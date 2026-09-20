from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform" / "aosp_product" / "apps" / "SwirApps"
ACTIVITY = APP / "src" / "org" / "swir" / "phoneos" / "apps" / "MainActivity.java"
POLICY = APP / "src" / "org" / "swir" / "phoneos" / "apps" / "AppCatalogPolicy.java"
MANIFEST = APP / "AndroidManifest.xml"
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
UPDATE_STRING_KEYS = {
    "update_source_format",
    "update_source_system",
    "update_source_external",
    "update_source_local",
    "update_status_format",
    "update_status_system_baseline",
    "update_status_system_updated",
    "update_status_external",
    "update_status_local",
    "last_updated_format",
    "last_updated_unknown",
}


class SwirAppsUpdateStatusSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.activity = ACTIVITY.read_text(encoding="utf-8")
        cls.policy = POLICY.read_text(encoding="utf-8")
        cls.manifest = MANIFEST.read_text(encoding="utf-8")

    def test_update_status_uses_only_local_package_metadata(self) -> None:
        required = (
            "PackageManager.GET_SIGNING_CERTIFICATES",
            "ApplicationInfo.FLAG_SYSTEM",
            "ApplicationInfo.FLAG_UPDATED_SYSTEM_APP",
            "getInstallSourceInfo(packageName)",
            "getInstallingPackageName()",
            "AppCatalogPolicy.validPackageName(sourcePackage)",
            "AppCatalogPolicy.updateSource",
            "AppCatalogPolicy.updateState",
            "R.string.update_status_format",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.activity)

    def test_install_source_lookup_fails_closed_without_crashing_catalog(self) -> None:
        self.assertIn(
            "catch (PackageManager.NameNotFoundException | SecurityException ignored)",
            self.activity,
        )
        self.assertIn("LOCAL_UNKNOWN", self.policy)
        self.assertIn("validPackageName(installerPackage)", self.policy)

    def test_software_center_remains_permission_free_and_non_installing(self) -> None:
        manifest = ET.fromstring(self.manifest)
        self.assertEqual([], manifest.findall("uses-permission"))
        bundle = self.activity + "\n" + self.policy + "\n" + self.manifest
        forbidden = (
            "PackageInstaller",
            "DownloadManager",
            "REQUEST_INSTALL_PACKAGES",
            "ACTION_INSTALL_PACKAGE",
            "android.permission.INTERNET",
            "Runtime.getRuntime",
            "ProcessBuilder",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, bundle)

    def test_update_status_strings_exist_in_all_supported_locales(self) -> None:
        for directory in LOCALE_DIRS:
            path = APP / "res" / directory / "strings.xml"
            root = ET.fromstring(path.read_text(encoding="utf-8"))
            keys = {node.get("name") for node in root.findall("string")}
            with self.subTest(locale=directory):
                self.assertTrue(UPDATE_STRING_KEYS.issubset(keys))


if __name__ == "__main__":
    unittest.main()
