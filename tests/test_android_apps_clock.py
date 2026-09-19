from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


CLOCK_ROOT = Path("platform/aosp_product/apps/SwirClock")
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class SwirClockResilientSessionSourceTests(unittest.TestCase):
    def test_clock_keeps_permission_minimal_boundary(self):
        root = ET.parse(CLOCK_ROOT / "AndroidManifest.xml").getroot()
        permissions = [node.get(ANDROID_NS + "name") for node in root.findall("uses-permission")]
        self.assertEqual(permissions, [])

    def test_clock_core_rejects_stale_elapsed_realtime_snapshots(self):
        source = (CLOCK_ROOT / "src/org/swir/phoneos/clock/ClockCore.java").read_text(encoding="utf-8")
        for token in (
            "MAX_SESSION_DRIFT_MILLIS",
            "canRestoreElapsedSession",
            "restoredTimerRemaining",
            "nowElapsedMillis < startedElapsedMillis",
            "nowWallMillis < startedWallMillis",
            "difference <= MAX_SESSION_DRIFT_MILLIS",
        ):
            self.assertIn(token, source)

    def test_activity_restores_only_dual_clock_verified_sessions(self):
        source = (CLOCK_ROOT / "src/org/swir/phoneos/clock/MainActivity.java").read_text(encoding="utf-8")
        for token in (
            "STATE_STOPWATCH_STARTED_ELAPSED",
            "STATE_STOPWATCH_STARTED_WALL",
            "STATE_TIMER_STARTED_ELAPSED",
            "STATE_TIMER_STARTED_WALL",
            "onSaveInstanceState",
            "restoreSessionState",
            "ClockCore.canRestoreElapsedSession",
            "ClockCore.restoredTimerRemaining",
            "SystemClock.elapsedRealtime()",
            "System.currentTimeMillis()",
        ):
            self.assertIn(token, source)

    def test_host_contract_covers_reboot_and_clock_drift_boundaries(self):
        source = (CLOCK_ROOT / "hosttest/ClockCoreHostTest.java").read_text(encoding="utf-8")
        for token in (
            "matching monotonic and wall deltas restore",
            "excessive wall drift rejected",
            "elapsed clock reset rejects stale snapshot",
            "wall clock rollback rejects snapshot",
            "verified timer restore keeps remaining duration",
            "stale timer snapshot fails closed",
        ):
            self.assertIn(token, source)

    def test_essential_suite_executes_clock_host_contract(self):
        workflow = Path(".github/workflows/essential-source-suite.yml").read_text(encoding="utf-8")
        self.assertIn("SwirClock org/swir/phoneos/clock ClockCore ClockCoreHostTest", workflow)


if __name__ == "__main__":
    unittest.main()
