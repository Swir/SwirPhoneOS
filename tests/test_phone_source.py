from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path("platform/aosp_product/apps/SwirPhone")
ANDROID = "{http://schemas.android.com/apk/res/android}"


class SwirPhoneSourceBoundaryTests(unittest.TestCase):
    def test_manifest_is_launcher_only_and_permission_free(self):
        manifest = ET.fromstring((ROOT / "AndroidManifest.xml").read_text(encoding="utf-8"))
        self.assertEqual(manifest.findall("uses-permission"), [])
        actions = {
            node.get(ANDROID + "name")
            for node in manifest.findall("./application/activity/intent-filter/action")
        }
        categories = {
            node.get(ANDROID + "name")
            for node in manifest.findall("./application/activity/intent-filter/category")
        }
        self.assertEqual(actions, {"android.intent.action.MAIN"})
        self.assertEqual(categories, {"android.intent.category.LAUNCHER"})
        self.assertNotIn("android.intent.action.DIAL", actions)
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
