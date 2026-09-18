from __future__ import annotations

from pathlib import Path
import unittest


class SwirBackupRestoreSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path("platform/aosp_product/apps/SwirBackup")
        cls.activity = (root / "src/org/swir/phoneos/backup/MainActivity.java").read_text(encoding="utf-8")
        cls.policy = (root / "src/org/swir/phoneos/backup/BackupPolicy.java").read_text(encoding="utf-8")
        cls.manifest = (root / "AndroidManifest.xml").read_text(encoding="utf-8")

    def test_restore_is_owner_selected_saf_only(self):
        for token in (
            "Intent.ACTION_OPEN_DOCUMENT",
            "Intent.ACTION_OPEN_DOCUMENT_TREE",
            "DocumentsContract.createDocument",
            "DocumentsContract.renameDocument",
            "DocumentsContract.deleteDocument",
            "DocumentsContract.buildDocumentUriUsingTree",
            "verifyArchive(archive, false)",
            "getContentResolver().openOutputStream(temp, \"w\")",
        ):
            self.assertIn(token, self.activity)
        for forbidden in (
            "MANAGE_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
            "READ_EXTERNAL_STORAGE",
            "FileOutputStream",
            "getDataDirectory()",
            '"/data/"',
            "Runtime.getRuntime",
            "ProcessBuilder",
        ):
            self.assertNotIn(forbidden, self.activity + self.manifest)

    def test_backup_and_restore_bind_each_document_to_sha256(self):
        for token in (
            'MessageDigest.getInstance("SHA-256")',
            "requireIntegrity(document.record, written)",
            "requireIntegrity(record, result)",
            "BackupPolicy.encodeManifest(manifest)",
            "BackupPolicy.parseManifest(text)",
            "BackupPolicy.MAX_MANIFEST_BYTES",
            "copyLimited(input, zip, BackupPolicy.MAX_ENTRY_BYTES)",
            "copyLimited(input, output, BackupPolicy.MAX_ENTRY_BYTES)",
        ):
            self.assertIn(token, self.activity)
        for token in (
            "MANIFEST_SCHEMA = 2",
            'MANIFEST_ENTRY = "swir/manifest.txt"',
            "validSha256",
            "duplicate manifest key",
            "unexpected manifest keys",
            "non-canonical field",
        ):
            self.assertIn(token, self.policy)

    def test_source_is_rehashed_before_archive_write_and_restore_rechecks_archive(self):
        self.assertIn("openInputStream(uri)", self.activity)
        self.assertIn("openInputStream(document.uri)", self.activity)
        self.assertIn("source size changed", self.activity)
        self.assertIn("archive changed before restore", self.activity)
        self.assertGreaterEqual(self.activity.count("verifyManifestEntries"), 3)

    def test_legacy_schema_is_inspect_only(self):
        self.assertIn("BackupPolicy.isLegacyManifest(text)", self.activity)
        self.assertIn("if (!allowLegacy)", self.activity)
        self.assertIn("legacy archive is inspect-only", self.activity)
        self.assertIn('text.startsWith("schema=1\\n")', self.policy)

    def test_restore_cleanup_is_fail_closed_best_effort(self):
        self.assertIn("cleanupDocuments(created)", self.activity)
        self.assertIn("DocumentsContract.deleteDocument", self.activity)
        self.assertIn("unexpected archive entry", self.activity)
        self.assertIn("archive entry mismatch", self.activity)

    def test_backup_ui_uses_shared_swir_design_tokens(self):
        for token in (
            "R.color.swir_background",
            "R.color.swir_text_primary",
            "R.color.swir_text_secondary",
            "R.dimen.swir_touch_min",
        ):
            self.assertIn(token, self.activity)
        self.assertNotIn("android.graphics.Color", self.activity)
        self.assertNotIn("Color.", self.activity)


if __name__ == "__main__":
    unittest.main()
