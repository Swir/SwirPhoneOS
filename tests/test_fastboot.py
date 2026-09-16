from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from swirphoneos.fastboot import (
    FastbootDiagnosticError,
    FastbootDevice,
    ReadOnlyFastboot,
    parse_fastboot_devices,
    parse_getvar,
    select_fastboot_device,
    summarize_fastboot,
)


class ParseFastbootDevicesTests(unittest.TestCase):
    def test_single_device(self) -> None:
        devices = parse_fastboot_devices("ABC123\tfastboot\n")
        self.assertEqual(devices, [FastbootDevice(serial="ABC123")])

    def test_blank_output_is_no_devices(self) -> None:
        self.assertEqual(parse_fastboot_devices("\n"), [])

    def test_rejects_malformed_state(self) -> None:
        with self.assertRaises(FastbootDiagnosticError):
            parse_fastboot_devices("ABC123\tdevice\n")

    def test_rejects_extra_columns(self) -> None:
        with self.assertRaises(FastbootDiagnosticError):
            parse_fastboot_devices("ABC123 fastboot extra\n")

    def test_rejects_duplicate(self) -> None:
        with self.assertRaises(FastbootDiagnosticError):
            parse_fastboot_devices("ABC123 fastboot\nABC123 fastboot\n")


class SelectionTests(unittest.TestCase):
    def test_requires_exactly_one(self) -> None:
        with self.assertRaises(FastbootDiagnosticError):
            select_fastboot_device([])
        with self.assertRaises(FastbootDiagnosticError):
            select_fastboot_device([
                FastbootDevice("A"),
                FastbootDevice("B"),
            ])

    def test_rejects_network_transport(self) -> None:
        # Parser rejects ':' before selection; direct construction protects the
        # selector contract as well.
        with self.assertRaises(FastbootDiagnosticError):
            select_fastboot_device([FastbootDevice("192.0.2.1:5554")])


class GetvarTests(unittest.TestCase):
    def test_parses_stderr_style(self) -> None:
        self.assertEqual(
            parse_getvar("product", "", "product: avicii\nFinished. Total time: 0.001s\n"),
            "avicii",
        )

    def test_parses_bootloader_prefix(self) -> None:
        self.assertEqual(
            parse_getvar("current-slot", "", "(bootloader) current-slot: a\n"),
            "a",
        )

    def test_missing_variable_is_unknown(self) -> None:
        self.assertIsNone(parse_getvar("secure", "", "Finished. Total time: 0.001s\n"))

    def test_rejects_unlisted_variable(self) -> None:
        with self.assertRaises(FastbootDiagnosticError):
            parse_getvar("serialno", "", "serialno: PRIVATE\n")

    def test_rejects_conflicting_values(self) -> None:
        with self.assertRaises(FastbootDiagnosticError):
            parse_getvar("product", "product: one\n", "product: two\n")


class SummaryTests(unittest.TestCase):
    def test_fastbootd_and_unlocked_mapping(self) -> None:
        result = summarize_fastboot({
            "product": "avicii",
            "current-slot": "a",
            "slot-count": "2",
            "unlocked": "yes",
            "is-userspace": "yes",
            "secure": "yes",
        })
        self.assertEqual(result["transport_mode_reported"], "fastbootd")
        self.assertEqual(result["bootloader_reported"], "unlocked")
        self.assertEqual(result["slot_count_reported"], 2)
        self.assertFalse(result["flash_allowed"])
        self.assertEqual(result["swirphoneos_support"], "NOT_VALIDATED")

    def test_invalid_slot_count_stays_unknown(self) -> None:
        result = summarize_fastboot({"slot-count": "many"})
        self.assertIsNone(result["slot_count_reported"])


class ReadOnlyFastbootTests(unittest.TestCase):
    def _tool(self) -> tuple[tempfile.TemporaryDirectory[str], ReadOnlyFastboot]:
        temporary = tempfile.TemporaryDirectory()
        name = "fastboot.exe" if os.name == "nt" else "fastboot"
        path = Path(temporary.name) / name
        path.write_bytes(b"")
        return temporary, ReadOnlyFastboot(path)

    def test_rejects_mutating_command(self) -> None:
        temporary, tool = self._tool()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(FastbootDiagnosticError):
            tool._run(("flash", "boot", "boot.img"))

    def test_inspect_uses_only_allowlisted_getvars_and_rechecks_device(self) -> None:
        temporary, tool = self._tool()
        self.addCleanup(temporary.cleanup)

        calls: list[list[str]] = []

        def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            args = command[1:]
            if args == ["devices"]:
                return subprocess.CompletedProcess(command, 0, "ABC123\tfastboot\n", "")
            if len(args) == 4 and args[0:3] == ["-s", "ABC123", "getvar"]:
                name = args[3]
                values = {
                    "product": "avicii",
                    "current-slot": "a",
                    "slot-count": "2",
                    "unlocked": "yes",
                    "is-userspace": "no",
                    "secure": "yes",
                }
                return subprocess.CompletedProcess(command, 0, "", f"{name}: {values[name]}\n")
            raise AssertionError(f"unexpected command: {args!r}")

        with patch("swirphoneos.fastboot.subprocess.run", side_effect=fake_run):
            report = tool.inspect()

        self.assertEqual(report["product_reported"], "avicii")
        self.assertEqual(report["transport_mode_reported"], "bootloader-fastboot")
        self.assertFalse(report["flash_allowed"])
        self.assertEqual(sum(1 for call in calls if call[1:] == ["devices"]), 2)
        self.assertTrue(all("flash" not in call for call in calls))

    def test_unsupported_getvar_becomes_unknown(self) -> None:
        temporary, tool = self._tool()
        self.addCleanup(temporary.cleanup)

        def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            args = command[1:]
            if args == ["devices"]:
                return subprocess.CompletedProcess(command, 0, "ABC123 fastboot\n", "")
            return subprocess.CompletedProcess(command, 1, "", "FAILED (remote: unknown variable)\n")

        with patch("swirphoneos.fastboot.subprocess.run", side_effect=fake_run):
            report = tool.inspect()
        self.assertIsNone(report["product_reported"])
        self.assertEqual(report["transport_mode_reported"], "unknown")
        self.assertFalse(report["flash_allowed"])


if __name__ == "__main__":
    unittest.main()
