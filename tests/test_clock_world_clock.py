from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path("platform/aosp_product/apps/SwirClock")
LOCALE_DIRS = (
    "values",
    "values-pl",
    "values-nb",
    "values-de",
    "values-es",
    "values-fr",
    "values-pt",
    "values-ar",
)


class SwirClockWorldClockTests(unittest.TestCase):
    def test_reviewed_world_zone_inventory_is_bounded_and_host_tested(self):
        core = (ROOT / "src/org/swir/phoneos/clock/ClockCore.java").read_text(encoding="utf-8")
        host = (ROOT / "hosttest/ClockCoreHostTest.java").read_text(encoding="utf-8")
        for zone in ("UTC", "Europe/Oslo", "Europe/Warsaw", "America/New_York", "Asia/Tokyo"):
            self.assertEqual(core.count(f'"{zone}"'), 1)
            self.assertIn(f'"{zone}"', host)
        for token in ("worldZoneCount", "worldZoneId", "nextWorldZoneIndex", "worldTime", "worldZoneLabel", "ZoneId.of"):
            self.assertIn(token, core)
        self.assertIn("world zone index out of range", core)
        self.assertIn("nextWorldZoneIndex(4) == 0", host)
        self.assertIn('worldTime("Not/AZone"', host)

    def test_activity_exposes_owner_visible_zone_switch_without_new_permissions(self):
        activity = (ROOT / "src/org/swir/phoneos/clock/MainActivity.java").read_text(encoding="utf-8")
        manifest = (ROOT / "AndroidManifest.xml").read_text(encoding="utf-8")
        for token in (
            "R.string.world_clock",
            "R.string.next_zone_description",
            "ClockCore.nextWorldZoneIndex",
            "ClockCore.worldZoneId",
            "ClockCore.worldZoneLabel",
            "ClockCore.worldTime",
        ):
            self.assertIn(token, activity)
        self.assertNotIn("android.permission.INTERNET", manifest)
        self.assertNotIn("ACCESS_FINE_LOCATION", manifest)
        self.assertNotIn("ACCESS_COARSE_LOCATION", manifest)

    def test_world_clock_strings_are_present_in_every_supported_catalog(self):
        expected = None
        for directory in LOCALE_DIRS:
            path = ROOT / "res" / directory / "strings.xml"
            root = ET.parse(path).getroot()
            keys = {node.attrib["name"] for node in root.findall("string")}
            self.assertIn("world_clock", keys)
            self.assertIn("next_zone_description", keys)
            if expected is None:
                expected = keys
            else:
                self.assertEqual(keys, expected, f"locale key drift in {directory}")


if __name__ == "__main__":
    unittest.main()
