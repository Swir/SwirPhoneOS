from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path("platform/aosp_product/apps/SwirPhone")
ANDROID = "{http://schemas.android.com/apk/res/android}"


class SwirPhoneSourceBoundaryTests(unittest.TestCase):
    def test_manifest_keeps_permission_free_launcher_and_explicit_dial_role_surface(self):
        manifest = ET.fromstring((ROOT / "AndroidManifest.xml").read_text(encoding="utf-8"))
        self.assertEqual(manifest.findall("uses-permission"), [])

        main = next(
            node
            for node in manifest.findall("./application/activity")
            if node.get(ANDROID + "name") == ".MainActivity"
        )
        filters = main.findall("intent-filter")
        actions = {
            node.get(ANDROID + "name")
            for intent_filter in filters
            for node in intent_filter.findall("action")
        }
        categories = {
            node.get(ANDROID + "name")
            for intent_filter in filters
            for node in intent_filter.findall("category")
        }
        schemes = {
            node.get(ANDROID + "scheme")
            for intent_filter in filters
            for node in intent_filter.findall("data")
        }

        self.assertEqual(actions, {"android.intent.action.MAIN", "android.intent.action.DIAL"})
        self.assertEqual(
            categories,
            {"android.intent.category.LAUNCHER", "android.intent.category.DEFAULT"},
        )
        self.assertEqual(schemes, {"tel"})
        self.assertNotIn("android.intent.action.CALL", actions)

    def test_activity_hands_off_to_an_external_dialer(self):
        source = (ROOT / "src/org/swir/phoneos/phone/MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("Intent.ACTION_DIAL", source)
        self.assertIn('Uri.fromParts("tel"', source)
        self.assertIn("resolveActivity(getPackageManager())", source)
        self.assertNotIn("Intent.ACTION_CALL", source)
        self.assertNotIn("TelecomManager.placeCall", source)


if __name__ == "__main__":
    unittest.main()
