from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path("platform/aosp_product/apps/SwirMessages")
ACTIVITY = ROOT / "src/org/swir/phoneos/messages/MainActivity.java"
HISTORY = ROOT / "src/org/swir/phoneos/messages/MessageHandoffHistory.java"
STAGE_FRAGMENT = Path("platform/aosp_product/stage_manifest.d/messages.json")


class SwirMessagesHandoffHistoryTests(unittest.TestCase):
    def test_history_is_owner_opt_in_and_default_off(self):
        source = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn('KEY_REMEMBER_HISTORY = "remember_handoff_history"', source)
        self.assertIn("getBoolean(KEY_REMEMBER_HISTORY, false)", source)
        self.assertIn("rememberHistory.isChecked()", source)
        self.assertIn("MessageHandoffHistory.prepend", source)
        self.assertIn("remove(KEY_HISTORY)", source)

    def test_history_is_text_handoff_evidence_not_delivery_or_media_storage(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        history = HISTORY.read_text(encoding="utf-8")
        self.assertIn("Intent.ACTION_SENDTO", activity)
        self.assertIn('Uri.fromParts("smsto"', activity)
        self.assertIn("resolveActivity(getPackageManager())", activity)
        self.assertIn("startActivity(intent)", activity)
        self.assertIn("text compose handoffs", history)
        self.assertIn("does not claim that an SMS or MMS was sent, delivered, or received", history)
        self.assertIn("never\n * stores attached media bytes", history)
        self.assertIn("!normalizedBody.trim().isEmpty()", activity)
        for forbidden in (
            "SmsManager",
            "sendTextMessage",
            "sendMultipartTextMessage",
            "Manifest.permission.SEND_SMS",
            "Manifest.permission.READ_SMS",
            "Manifest.permission.RECEIVE_SMS",
        ):
            self.assertNotIn(forbidden, activity)
            self.assertNotIn(forbidden, history)

    def test_history_storage_is_bounded_and_body_minimized(self):
        source = HISTORY.read_text(encoding="utf-8")
        self.assertIn("MAX_ENTRIES = 8", source)
        self.assertIn("MAX_SERIALIZED_LENGTH = 64 * 1024", source)
        self.assertIn("MAX_PREVIEW_CODEPOINTS = 96", source)
        self.assertIn("if (entries.size() >= MAX_ENTRIES) break", source)
        self.assertIn("if (out.length() > MAX_SERIALIZED_LENGTH)", source)
        self.assertIn("String storedBody = preview(body)", source)
        self.assertIn("String body = preview(entry.body)", source)
        self.assertIn("String body = preview(decodeText(fields[2]))", source)
        self.assertIn("Character.isWhitespace(codePoint) || Character.isISOControl(codePoint)", source)
        self.assertIn("appendCodePoint(codePoint)", source)
        self.assertIn("append('…')", source)
        self.assertNotIn("String normalizedBody = MessagePolicy.normalizeBody(body);", source)

    def test_history_source_is_staged_exactly_once(self):
        data = json.loads(STAGE_FRAGMENT.read_text(encoding="utf-8"))
        source = "apps/SwirMessages/src/org/swir/phoneos/messages/MessageHandoffHistory.java"
        destination = "vendor/swir/apps/SwirMessages/src/org/swir/phoneos/messages/MessageHandoffHistory.java"
        matches = [item for item in data["files"] if item["source"] == source]
        self.assertEqual(matches, [{"source": source, "destination": destination}])


if __name__ == "__main__":
    unittest.main()
