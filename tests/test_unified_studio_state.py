"""Unified Flash Studio read-only transport/profile integration tests."""
from __future__ import annotations

import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from swirphoneos.diagnostics import DiagnosticError, summarize
from swirphoneos.fastboot import summarize_fastboot
from swirphoneos.profiles import DeviceProfile
from swirphoneos.studio_state import UnifiedDiagnosticSession


PROFILE = DeviceProfile(
    profile_id="oneplus/avicii",
    display_name="OnePlus Nord AC2003",
    codename="avicii",
    model_allowlist=("AC2003",),
    status="PLANNED_NOT_SUPPORTED",
    firmware_baseline=None,
    sources=("https://example.invalid/avicii",),
)


def wait_for(session: UnifiedDiagnosticSession):
    deadline = time.monotonic() + 2
    result = None
    while result is None and time.monotonic() < deadline:
        result = session.poll()
        if result is None:
            time.sleep(0.01)
    if result is None:
        raise AssertionError("diagnostic worker did not finish")
    return result


class UnifiedStudioStateTests(unittest.TestCase):
    def test_adb_report_gets_fail_closed_profile_hint(self):
        session = UnifiedDiagnosticSession(adb_inspector=lambda _: summarize({
            "ro.product.model": "AC2003",
            "ro.product.device": "avicii",
        }))
        with patch("swirphoneos.studio_state.discover_profiles", return_value=[PROFILE]):
            self.assertTrue(session.start(Path("/trusted/adb"), "adb"))
            result = wait_for(session)
        self.assertIsNone(result.error_key)
        report = json.loads(result.report_json)
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["transport"], "adb")
        self.assertEqual(report["profile_assessment"]["candidate_profile_id"], "oneplus/avicii")
        self.assertFalse(report["profile_assessment"]["identity_verified"])
        self.assertFalse(report["flash_allowed"])

    def test_fastboot_report_gets_profile_hint(self):
        session = UnifiedDiagnosticSession(fastboot_inspector=lambda _: summarize_fastboot({"product": "avicii"}))
        with patch("swirphoneos.studio_state.discover_profiles", return_value=[PROFILE]):
            self.assertTrue(session.start(Path("/trusted/fastboot"), "fastboot"))
            result = wait_for(session)
        report = json.loads(result.report_json)
        self.assertEqual(report["transport"], "fastboot")
        self.assertEqual(report["profile_assessment"]["result"], "PROFILE_HINT_ONLY")
        self.assertFalse(report["transport_report"]["flash_allowed"])

    def test_transport_failure_does_not_leak_raw_details(self):
        def failure(_: Path):
            raise DiagnosticError("serial-and-private-path")
        session = UnifiedDiagnosticSession(adb_inspector=failure)
        with patch("swirphoneos.studio_state.discover_profiles", return_value=[PROFILE]):
            self.assertTrue(session.start(Path("/private/adb"), "adb"))
            result = wait_for(session)
        self.assertEqual(result.error_key, "scan_failed")
        self.assertIsNone(result.report_json)
        self.assertIsNone(session.report)


if __name__ == "__main__":
    unittest.main()
