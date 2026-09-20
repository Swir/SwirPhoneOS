from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from swirphoneos.android_apps import validate_android_app_sources


ROOT = Path("platform/aosp_product/apps/SwirMessages")
ACTIVITY = ROOT / "src/org/swir/phoneos/messages/MainActivity.java"
POLICY = ROOT / "src/org/swir/phoneos/messages/MessagePolicy.java"
MANIFEST = ROOT / "AndroidManifest.xml"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class SwirMessagesMediaHandoffTests(unittest.TestCase):
    def test_media_selection_is_owner_visible_and_uri_scoped(self):
        source = ACTIVITY.read_text(encoding="utf-8")
        for token in (
            "Intent.ACTION_OPEN_DOCUMENT",
            "Intent.CATEGORY_OPENABLE",
            "Intent.EXTRA_MIME_TYPES",
            'new String[]{"image/*", "video/*", "audio/*"}',
            '"content".equals(uri.getScheme())',
            "OpenableColumns.DISPLAY_NAME",
            "OpenableColumns.SIZE",
            "MessagePolicy.attachmentReviewReady",
            "Intent.ACTION_SEND",
            "Intent.EXTRA_STREAM",
            "ClipData.newUri",
            "Intent.FLAG_GRANT_READ_URI_PERMISSION",
            "Intent.createChooser",
            "MessagePolicy.canMediaHandoff",
        ):
            self.assertIn(token, source)

    def test_media_draft_uses_persisted_read_grant_and_fails_closed_on_restore(self):
        source = ACTIVITY.read_text(encoding="utf-8")
        for token in (
            "Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION",
            "takePersistableUriPermission",
            "getPersistedUriPermissions",
            "permission.isReadPermission()",
            "releasePersistableUriPermission",
            'KEY_ATTACHMENT_URI = "attachment_uri"',
            'KEY_ATTACHMENT_MIME = "attachment_mime"',
            'KEY_ATTACHMENT_NAME = "attachment_name"',
            'KEY_ATTACHMENT_SIZE = "attachment_size"',
            "persistAttachmentDraft",
            "restoreAttachmentDraft",
            "revalidateCurrentAttachment",
            "storedMime.equals(fresh.mime)",
            "storedName.equals(freshName)",
            "storedSize != fresh.sizeBytes",
        ):
            self.assertIn(token, source)
        self.assertIn("putString(KEY_ATTACHMENT_URI, attachmentUri.toString())", source)
        self.assertIn("putLong(KEY_ATTACHMENT_SIZE, attachmentSize)", source)
        self.assertIn("remove(KEY_ATTACHMENT_URI)", source)
        self.assertNotIn("KEY_ATTACHMENT_BYTES", source)
        self.assertNotIn("openInputStream", source)

    def test_media_handoff_revalidates_provider_and_does_not_create_sms_history(self):
        source = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn("hasAttachment && !revalidateCurrentAttachment()", source)
        self.assertIn("!mediaReady && rememberHistory != null", source)
        self.assertNotIn("if (rememberHistory != null && rememberHistory.isChecked()", source)

    def test_media_policy_is_bounded_and_fail_closed(self):
        source = POLICY.read_text(encoding="utf-8")
        for token in (
            "MAX_ATTACHMENT_BYTES = 25L * 1024L * 1024L",
            "MAX_ATTACHMENT_NAME_LENGTH = 180",
            "isSupportedMediaMime",
            '"image".equals(family)',
            '"video".equals(family)',
            '"audio".equals(family)',
            'slash != mime.lastIndexOf',
            '"*".equals(subtype)',
            "safeAttachmentName",
            "attachmentReviewReady",
            "sizeBytes > 0L",
            "sizeBytes <= MAX_ATTACHMENT_BYTES",
        ):
            self.assertIn(token, source)

    def test_media_handoff_adds_no_sms_storage_or_network_permission(self):
        root = ET.parse(MANIFEST).getroot()
        permissions = {
            node.get(ANDROID_NS + "name")
            for node in root.findall("uses-permission")
            if node.get(ANDROID_NS + "name")
        }
        self.assertEqual(permissions, set())
        source = ACTIVITY.read_text(encoding="utf-8") + "\n" + POLICY.read_text(encoding="utf-8")
        for forbidden in (
            "SmsManager",
            "sendTextMessage",
            "sendMultipartTextMessage",
            "Manifest.permission.SEND_SMS",
            "Manifest.permission.READ_SMS",
            "Manifest.permission.RECEIVE_SMS",
            "Manifest.permission.READ_MEDIA_IMAGES",
            "Manifest.permission.READ_MEDIA_VIDEO",
            "Manifest.permission.READ_EXTERNAL_STORAGE",
            "Manifest.permission.WRITE_EXTERNAL_STORAGE",
            "Manifest.permission.INTERNET",
        ):
            self.assertNotIn(forbidden, source)

    def test_mms_capability_stays_open_until_runtime_review(self):
        summary = validate_android_app_sources()
        self.assertIn("messages:mms", summary.missing_app_capabilities)
        self.assertIn("messages:conversation_history", summary.missing_app_capabilities)


if __name__ == "__main__":
    unittest.main()
