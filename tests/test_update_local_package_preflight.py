from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "platform" / "aosp_product" / "apps" / "SwirUpdate"
POLICY = APP / "src" / "org" / "swir" / "phoneos" / "update" / "UpdatePolicy.java"
ACTIVITY = APP / "src" / "org" / "swir" / "phoneos" / "update" / "MainActivity.java"
MANIFEST = APP / "AndroidManifest.xml"
LOCALES = ("values", "values-pl", "values-nb", "values-de", "values-es", "values-fr", "values-pt", "values-ar")


class UpdateLocalPackagePreflightTests(unittest.TestCase):
    def test_owner_selects_package_through_read_only_saf(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        for token in (
            "Intent.ACTION_OPEN_DOCUMENT",
            "Intent.CATEGORY_OPENABLE",
            'setType("application/zip")',
            "OpenableColumns.DISPLAY_NAME",
            "OpenableColumns.SIZE",
            "openInputStream(uri)",
            "UpdatePolicy.inspectPackage",
        ):
            self.assertIn(token, activity)
        for forbidden in (
            "ACTION_CREATE_DOCUMENT",
            "DownloadManager",
            "RecoverySystem.installPackage",
            "FileOutputStream",
            "getExternalStorageDirectory",
            "MANAGE_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
        ):
            self.assertNotIn(forbidden, activity)

    def test_policy_is_bounded_and_identity_only(self):
        policy = POLICY.read_text(encoding="utf-8")
        for token in (
            "MAX_PACKAGE_BYTES",
            "16L * 1024L * 1024L * 1024L",
            "REVIEW_READY_UNTRUSTED",
            "safePackageName",
            "looksLikeZipHeader",
            'MessageDigest.getInstance("SHA-256")',
            "declaredSize != total",
        ):
            self.assertIn(token, policy)
        for forbidden in (
            "RecoverySystem",
            "DownloadManager",
            "Runtime.getRuntime",
            "ProcessBuilder",
            "android.os.SystemProperties",
            "/dev/block/",
        ):
            self.assertNotIn(forbidden, policy)

    def test_manifest_gains_no_permission_for_local_review(self):
        root = ET.parse(MANIFEST).getroot()
        namespace = "{http://schemas.android.com/apk/res/android}"
        permissions = [node.get(namespace + "name") for node in root.findall("uses-permission")]
        self.assertEqual(permissions, [])

    def test_every_locale_has_identical_preflight_keys(self):
        expected = None
        required = {
            "review_local_package",
            "local_package",
            "package_none_selected",
            "package_inspecting",
            "package_review_ready_untrusted",
            "package_rejected_name",
            "package_rejected_size",
            "package_rejected_format",
            "package_read_failed",
            "package_name",
            "package_size",
            "package_sha256",
        }
        for folder in LOCALES:
            root = ET.parse(APP / "res" / folder / "strings.xml").getroot()
            keys = {item.get("name") for item in root.findall("string")}
            self.assertTrue(required.issubset(keys), folder)
            if expected is None:
                expected = keys
            else:
                self.assertEqual(expected, keys, folder)

    def test_ui_does_not_overclaim_staging_or_trust(self):
        english = ET.parse(APP / "res" / "values" / "strings.xml").getroot()
        values = {item.get("name"): "".join(item.itertext()) for item in english.findall("string")}
        ready = values["package_review_ready_untrusted"].lower()
        install = values["no_package_staged"].lower()
        self.assertIn("untrusted", ready)
        self.assertIn("disabled", ready)
        self.assertIn("no update package is staged", install)
        self.assertIn("recovery handoff remains disabled", install)


if __name__ == "__main__":
    unittest.main()
