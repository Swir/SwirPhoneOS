from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path("platform/aosp_product/apps/SwirGallery")
ACTIVITY = ROOT / "src/org/swir/phoneos/gallery/MainActivity.java"
POLICY = ROOT / "src/org/swir/phoneos/gallery/MediaPolicy.java"
MANIFEST = ROOT / "AndroidManifest.xml"
LOCALES = ("values", "values-pl", "values-nb", "values-de", "values-es", "values-fr", "values-pt", "values-ar")
ALBUM_KEYS = {"album_section_title", "all_media", "album_item", "unknown_album"}


class GalleryAlbumSourceTests(unittest.TestCase):
    def test_album_grouping_is_scoped_read_only_mediastore_source(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        for token in (
            "MediaStore.Files.getContentUri",
            "MediaStore.Images.ImageColumns.BUCKET_ID",
            "MediaStore.Images.ImageColumns.BUCKET_DISPLAY_NAME",
            "MediaPolicy.safeAlbumName",
            "selectedAlbumId",
            "renderAlbums",
            "MediaStore.createDeleteRequest",
        ):
            self.assertIn(token, activity)
        for token in (
            "getContentResolver().insert",
            "getContentResolver().update",
            "getContentResolver().delete",
            "MANAGE_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
        ):
            self.assertNotIn(token, activity)

    def test_album_policy_stays_pure_java_and_bounded(self):
        policy = POLICY.read_text(encoding="utf-8")
        self.assertNotIn("import android.", policy)
        self.assertIn("MAX_ALBUM_NAME_LENGTH = 80", policy)
        self.assertIn("Character.isISOControl", policy)
        self.assertIn("album.contains(needle)", policy)

    def test_gallery_permissions_remain_exact(self):
        root = ET.fromstring(MANIFEST.read_text(encoding="utf-8"))
        ns = "{http://schemas.android.com/apk/res/android}"
        permissions = {(node.get(ns + "name") or "").strip() for node in root.findall("uses-permission")}
        self.assertEqual(permissions, {
            "android.permission.READ_MEDIA_IMAGES",
            "android.permission.READ_MEDIA_VIDEO",
        })

    def test_album_strings_exist_in_all_eight_locales(self):
        baseline: set[str] | None = None
        for directory in LOCALES:
            root = ET.fromstring((ROOT / "res" / directory / "strings.xml").read_text(encoding="utf-8"))
            keys = {(node.get("name") or "").strip() for node in root.findall("string")}
            self.assertTrue(ALBUM_KEYS.issubset(keys), directory)
            if baseline is None:
                baseline = keys
            else:
                self.assertEqual(keys, baseline, directory)


if __name__ == "__main__":
    unittest.main()
