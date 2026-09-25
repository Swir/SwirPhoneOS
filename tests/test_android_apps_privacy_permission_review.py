from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform" / "aosp_product" / "apps" / "SwirPrivacy"
ANDROID = "{http://schemas.android.com/apk/res/android}"

EXPECTED_QUERY_PACKAGES = {
    "org.swir.phoneos.launcher",
    "org.swir.phoneos.settings",
    "org.swir.phoneos.files",
    "org.swir.phoneos.update",
    "org.swir.phoneos.device_care",
    "org.swir.phoneos.swirroot",
}
EXPECTED_BETA_SURFACES = EXPECTED_QUERY_PACKAGES | {"org.swir.phoneos.privacy"}


class SwirPrivacyPermissionReviewTests(unittest.TestCase):
    def test_manifest_visibility_is_exact_and_permission_free(self) -> None:
        root = ET.parse(APP / "AndroidManifest.xml").getroot()
        permissions = {
            item.attrib.get(ANDROID + "name")
            for item in root.findall("uses-permission")
        }
        self.assertNotIn("android.permission.QUERY_ALL_PACKAGES", permissions)
        self.assertEqual(permissions, set())

        queries = root.find("queries")
        self.assertIsNotNone(queries)
        packages = {
            item.attrib.get(ANDROID + "name")
            for item in queries.findall("package")
        }
        self.assertEqual(packages, EXPECTED_QUERY_PACKAGES)

    def test_policy_is_frozen_to_first_beta_surfaces(self) -> None:
        text = (APP / "src" / "org" / "swir" / "phoneos" / "privacy"
                / "PermissionReviewPolicy.java").read_text(encoding="utf-8")
        packages = set(re.findall(r'"(org\.swir\.phoneos\.[a-z_]+)"', text))
        self.assertEqual(packages, EXPECTED_BETA_SURFACES)
        self.assertIn("MAX_PACKAGES = 7", text)
        self.assertIn("MAX_PERMISSIONS_PER_PACKAGE = 32", text)

    def test_runtime_review_is_read_only(self) -> None:
        text = (APP / "src" / "org" / "swir" / "phoneos" / "privacy"
                / "MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("PackageManager.GET_PERMISSIONS", text)
        self.assertIn("packageManager.checkPermission", text)
        for forbidden in (
            "requestPermissions(",
            "grantRuntimePermission",
            "revokeRuntimePermission",
            "QUERY_ALL_PACKAGES",
            "PackageInstaller",
            "Runtime.getRuntime",
            "ProcessBuilder",
        ):
            self.assertNotIn(forbidden, text)

    def test_new_policy_is_staged_into_aosp_product(self) -> None:
        fragment = ROOT / "platform" / "aosp_product" / "stage_manifest.d" / "privacy-permission-review.json"
        self.assertTrue(fragment.is_file())
        text = fragment.read_text(encoding="utf-8")
        self.assertIn("PermissionReviewPolicy.java", text)


if __name__ == "__main__":
    unittest.main()
