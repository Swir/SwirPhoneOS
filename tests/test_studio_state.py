"""Synthetic desktop tests; never physical-device evidence."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
import json
import os
import time
import unittest

from swirphoneos.diagnostics import DiagnosticError, summarize
from swirphoneos.studio_state import DiagnosticSession, report_json, save_report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.report = summarize({"ro.product.model": "Synthetic fixture"})

    def test_roundtrip(self):
        self.assertEqual(json.loads(report_json(self.report)), self.report)

    def test_no_serial_field(self):
        self.report["serial"] = "private"
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_no_adb_path_field(self):
        self.report["adb_path"] = "/private/user/adb"
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_missing_field(self):
        self.report.pop("model")
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_cannot_enable_flash(self):
        self.report["flash_allowed"] = True
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_cannot_use_zero_instead_of_false(self):
        self.report["flash_allowed"] = 0
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_cannot_claim_support(self):
        self.report["swirphoneos_support"] = "SUPPORTED"
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_cannot_remove_warnings(self):
        self.report["warnings"] = []
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_cannot_change_provenance(self):
        self.report["source"] = "physical_validation"
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_boolean_types(self):
        for value in (1, "true", [], {}):
            with self.subTest(value=value):
                self.report["treble_reported"] = value
                with self.assertRaises(ValueError):
                    report_json(self.report)

    def test_bootloader_enum(self):
        self.report["bootloader_reported"] = "safe"
        with self.assertRaises(ValueError):
            report_json(self.report)

    def test_invalid_text(self):
        for value in ("line\nbreak", "\x1b[31m", "é", "x" * 257, [], "", 1):
            with self.subTest(value=value):
                self.report["model"] = value
                with self.assertRaises(ValueError):
                    report_json(self.report)

    def test_unknowns_remain_unknown(self):
        value = json.loads(report_json(summarize({})))
        self.assertIsNone(value["model"])
        self.assertIsNone(value["treble_reported"])
        self.assertFalse(value["flash_allowed"])

    def test_private_new_file(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            save_report(path, report_json(self.report))
            self.assertEqual(json.loads(path.read_text()), self.report)
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_no_overwrite(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            path.write_text("keep me")
            with self.assertRaises(FileExistsError):
                save_report(path, report_json(self.report))
            self.assertEqual(path.read_text(), "keep me")

    def test_no_symlink_target(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "target.json"
            target.write_text("keep me")
            link = Path(folder) / "link.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Host does not permit creating symlinks.")
            with self.assertRaises(FileExistsError):
                save_report(link, report_json(self.report))
            self.assertEqual(target.read_text(), "keep me")

    def test_relative_destination_rejected(self):
        with self.assertRaises(ValueError):
            save_report(Path("relative.json"), report_json(self.report))

    def test_extension_rejected(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_report(Path(folder) / "report.exe", report_json(self.report))

    def test_oversized_rejected_before_create(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            with self.assertRaises(ValueError):
                save_report(path, " " * 16385)
            self.assertFalse(path.exists())

    def test_invalid_json_does_not_create_file(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            with self.assertRaises(ValueError):
                save_report(path, "not json")
            self.assertFalse(path.exists())


class SessionTests(unittest.TestCase):
    def result(self, session):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            result = session.poll()
            if result is not None:
                return result
            time.sleep(0.005)
        self.fail("Synthetic worker did not finish in time.")

    def test_success_is_immutable_json(self):
        session = DiagnosticSession(lambda _: summarize({}))
        self.assertTrue(session.start(Path("/unused/adb")))
        result = self.result(session)
        self.assertIsInstance(result.report_json, str)
        self.assertEqual(session.report, result.report_json)
        self.assertFalse(session.busy)
        self.assertIsNone(session.poll())

    def test_busy_rejects_duplicate(self):
        release = Event()
        def inspect(_):
            release.wait(1)
            return summarize({})
        session = DiagnosticSession(inspect)
        try:
            session.start(Path("/unused/adb"))
            self.assertFalse(session.start(Path("/second/adb")))
        finally:
            release.set()
        self.result(session)

    def test_diagnostic_error_is_private(self):
        def inspect(_):
            raise DiagnosticError("PRIVATE-SERIAL /home/private/path")
        session = DiagnosticSession(inspect)
        session.start(Path("/unused/adb"))
        result = self.result(session)
        self.assertEqual(result.error_key, "scan_failed")
        self.assertNotIn("PRIVATE", repr(result))
        self.assertIsNone(session.report)

    def test_unexpected_error_is_private(self):
        def inspect(_):
            raise RuntimeError("private-token")
        session = DiagnosticSession(inspect)
        session.start(Path("/unused/adb"))
        result = self.result(session)
        self.assertEqual(result.error_key, "unexpected")
        self.assertNotIn("private-token", repr(result))

    def test_bad_core_report_is_not_exported(self):
        session = DiagnosticSession(lambda _: {"serial": "private"})
        session.start(Path("/unused/adb"))
        result = self.result(session)
        self.assertIsNone(result.report_json)
        self.assertEqual(result.error_key, "unexpected")

    def test_new_failure_clears_old_report(self):
        def inspect(_):
            raise DiagnosticError("failure")
        session = DiagnosticSession(inspect)
        session.report = report_json(summarize({}))
        session.start(Path("/unused/adb"))
        self.assertIsNone(session.report)
        self.result(session)
        self.assertIsNone(session.report)

    def test_thread_start_failure_remains_busy_until_consumed(self):
        session = DiagnosticSession(lambda _: summarize({}))
        with patch("swirphoneos.studio_state.Thread.start", side_effect=RuntimeError("private")):
            session.start(Path("/unused/adb"))
            self.assertTrue(session.busy)
            self.assertFalse(session.start(Path("/second/adb")))
        self.assertEqual(self.result(session).error_key, "unexpected")
        self.assertFalse(session.busy)
