from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path("platform/aosp_product/apps/SwirUpdate")
LOCALES = ("values", "values-pl", "values-nb", "values-de", "values-es", "values-fr", "values-pt", "values-ar")


def string_keys(path: Path) -> set[str]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    return {node.get("name", "") for node in root.findall("string")}


class SwirUpdateOwnerReviewSourceTests(unittest.TestCase):
    def test_update_remains_permission_free_and_owner_selected(self):
        manifest = ET.fromstring((ROOT / "AndroidManifest.xml").read_text(encoding="utf-8"))
        self.assertEqual(manifest.findall("uses-permission"), [])
        activity = (ROOT / "src/org/swir/phoneos/update/MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("Intent.ACTION_OPEN_DOCUMENT", activity)
        self.assertIn("REQUEST_SIGNED_MANIFEST", activity)
        self.assertIn("REQUEST_DETACHED_SIGNATURE", activity)
        self.assertIn("reviewSession.selectManifest", activity)
        self.assertIn("reviewSession.selectSignature", activity)
        self.assertNotIn("takePersistableUriPermission", activity)
        for forbidden in (
            "RecoverySystem.installPackage",
            "UpdateEngine",
            "Runtime.getRuntime",
            "ProcessBuilder",
            "PowerManager.reboot",
            "fastboot",
            "flash ",
            "erase ",
        ):
            self.assertNotIn(forbidden, activity)

    def test_review_session_is_bounded_and_cannot_authorize_staging(self):
        source = (ROOT / "src/org/swir/phoneos/update/OtaReviewSession.java").read_text(encoding="utf-8")
        self.assertIn("MAX_SIGNATURE_BYTES = 1024", source)
        self.assertIn("UpdatePolicy.MAX_MANIFEST_BYTES", source)
        self.assertIn("Thread.currentThread().isInterrupted()", source)
        self.assertIn("public boolean stagingAllowed() { return false; }", source)
        self.assertIn("clearSignedArtifacts();", source)
        self.assertIn("signatureBytes = null;", source)
        for forbidden in (
            "RecoverySystem",
            "UpdateEngine",
            "Runtime.getRuntime",
            "ProcessBuilder",
            "FileOutputStream",
            "RandomAccessFile",
        ):
            self.assertNotIn(forbidden, source)

    def test_review_session_is_in_exact_aosp_staging_closure(self):
        data = json.loads(Path("platform/aosp_product/stage_manifest.d/update-trust-store.json").read_text(encoding="utf-8"))
        sources = {entry["source"] for entry in data["files"]}
        self.assertIn(
            "apps/SwirUpdate/src/org/swir/phoneos/update/OtaReviewSession.java",
            sources,
        )

    def test_all_locales_expose_the_exact_owner_review_surface(self):
        expected = string_keys(ROOT / "res/values/strings.xml")
        required = {
            "review_signed_manifest",
            "review_detached_signature",
            "signed_metadata",
            "metadata_inspecting",
            "metadata_need_manifest",
            "metadata_need_signature",
            "metadata_input_rejected",
            "metadata_trust_rejected",
            "metadata_policy_rejected",
            "metadata_authentic_not_staged",
            "manifest_target",
            "manifest_key_id",
            "manifest_channel",
            "manifest_sha256",
            "signature_sha256",
        }
        self.assertTrue(required.issubset(expected))
        for folder in LOCALES:
            self.assertEqual(string_keys(ROOT / f"res/{folder}/strings.xml"), expected, folder)


if __name__ == "__main__":
    unittest.main()
