from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform" / "aosp_product" / "apps" / "SwirCalendar"
ACTIVITY = APP / "src" / "org" / "swir" / "phoneos" / "calendar" / "MainActivity.java"
POLICY = APP / "src" / "org" / "swir" / "phoneos" / "calendar" / "EventPolicy.java"
MANIFEST = APP / "AndroidManifest.xml"
WORKFLOW = ROOT / ".github" / "workflows" / "essential-source-suite.yml"
LOCALES = ("values", "values-pl", "values-nb", "values-de", "values-es", "values-fr", "values-pt", "values-ar")


class CalendarProviderBridgeTests(unittest.TestCase):
    def test_manifest_keeps_zero_calendar_permissions(self):
        root = ET.parse(MANIFEST).getroot()
        ns = "{http://schemas.android.com/apk/res/android}"
        permissions = [node.get(ns + "name") for node in root.findall("uses-permission")]
        self.assertEqual(permissions, [])

    def test_provider_bridge_is_owner_visible_insert_handoff_only(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        for token in (
            "Intent.ACTION_INSERT",
            "CalendarContract.Events.CONTENT_URI",
            "CalendarContract.Events.TITLE",
            "CalendarContract.Events.EVENT_LOCATION",
            "CalendarContract.EXTRA_EVENT_BEGIN_TIME",
            "CalendarContract.EXTRA_EVENT_END_TIME",
            "resolveActivity(getPackageManager())",
            "startActivity(intent)",
        ):
            self.assertIn(token, activity)
        for forbidden in (
            "Manifest.permission.READ_CALENDAR",
            "Manifest.permission.WRITE_CALENDAR",
            "getContentResolver().insert(CalendarContract.Events.CONTENT_URI",
            "getContentResolver().update(CalendarContract.Events.CONTENT_URI",
            "getContentResolver().delete(CalendarContract.Events.CONTENT_URI",
        ):
            self.assertNotIn(forbidden, activity)

    def test_ics_import_is_owner_selected_bounded_and_strict_utf8(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        policy = POLICY.read_text(encoding="utf-8")
        for token in (
            "Intent.ACTION_OPEN_DOCUMENT",
            "Intent.CATEGORY_OPENABLE",
            'setType("text/calendar")',
            "openInputStream(uri)",
            "EventPolicy.MAX_ICS_BYTES",
            "CodingErrorAction.REPORT",
            "EventPolicy.parseSingleEvent",
        ):
            self.assertIn(token, activity)
        for token in (
            "MAX_ICS_BYTES = 64 * 1024",
            "parseSingleEvent",
            "DEFAULT_ALL_DAY_DURATION_MS",
            "setLenient(false)",
            "TimeZone.getTimeZone(\"UTC\")",
        ):
            self.assertIn(token, policy)
        self.assertNotIn("java.net.", policy)

    def test_calendar_uses_shared_design_tokens_and_touch_target(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        self.assertNotIn("android.graphics.Color", activity)
        for token in (
            "R.color.swir_background",
            "R.color.swir_surface",
            "R.color.swir_text_primary",
            "R.color.swir_text_secondary",
            "R.dimen.swir_space_md",
            "R.dimen.swir_touch_min",
        ):
            self.assertIn(token, activity)

    def test_all_locales_expose_import_and_handoff_strings(self):
        expected = None
        required = {
            "import_event",
            "imported_event",
            "import_failed",
            "add_to_device_calendar",
            "device_calendar_unavailable",
        }
        for folder in LOCALES:
            root = ET.parse(APP / "res" / folder / "strings.xml").getroot()
            keys = {item.get("name") for item in root.findall("string")}
            self.assertTrue(required.issubset(keys), folder)
            if expected is None:
                expected = keys
            else:
                self.assertEqual(expected, keys, folder)

    def test_calendar_host_policy_runs_in_essential_suite(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("SwirCalendar org/swir/phoneos/calendar EventPolicy EventPolicyHostTest", workflow)


if __name__ == "__main__":
    unittest.main()
