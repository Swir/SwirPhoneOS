from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path("platform/aosp_product/apps/SwirPhone")
MAIN = ROOT / "src/org/swir/phoneos/phone/MainActivity.java"
POLICY = ROOT / "src/org/swir/phoneos/phone/CallHistoryPolicy.java"


class SwirPhoneRecentCallsSourceTests(unittest.TestCase):
    def test_recent_calls_require_default_role_and_explicit_runtime_permission(self):
        source = MAIN.read_text(encoding="utf-8")
        role = source.index("if (!isDefaultDialer())")
        permission = source.index("checkSelfPermission(Manifest.permission.READ_CALL_LOG)")
        request = source.index("requestPermissions(new String[]{Manifest.permission.READ_CALL_LOG}")
        query = source.index("CallLog.Calls.CONTENT_URI")
        self.assertLess(role, permission)
        self.assertLess(permission, request)
        self.assertLess(request, query)

    def test_call_log_is_read_only_and_bounded(self):
        source = MAIN.read_text(encoding="utf-8")
        for token in (
            "CallLog.Calls.NUMBER_PRESENTATION",
            "TelecomManager.PRESENTATION_ALLOWED",
            "CallHistoryPolicy.MAX_RECENT_CALLS",
            "getContentResolver().query",
            "CallLog.Calls.DATE + \" DESC\"",
        ):
            self.assertIn(token, source)
        for forbidden in (
            "getContentResolver().insert",
            "getContentResolver().update",
            "getContentResolver().delete",
            "WRITE_CALL_LOG",
            "Intent.ACTION_CALL",
            "TelecomManager.placeCall",
        ):
            self.assertNotIn(forbidden, source)

    def test_privacy_policy_is_pure_java_and_bounds_sensitive_labels(self):
        source = POLICY.read_text(encoding="utf-8")
        self.assertNotIn("import android.", source)
        for token in (
            "MAX_RECENT_CALLS = 20",
            "MAX_LABEL_LENGTH = 80",
            "presentationAllowed",
            "Character.isISOControl",
            "safeDurationSeconds",
        ):
            self.assertIn(token, source)

    def test_staging_contains_recent_call_policy(self):
        stage = json.loads(Path("platform/aosp_product/stage_manifest.d/phone.json").read_text(encoding="utf-8"))
        sources = {entry["source"] for entry in stage["files"]}
        self.assertIn("apps/SwirPhone/src/org/swir/phoneos/phone/CallHistoryPolicy.java", sources)


if __name__ == "__main__":
    unittest.main()
