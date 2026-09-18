from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path("platform/aosp_product/apps/SwirPhone")
ANDROID = "{http://schemas.android.com/apk/res/android}"
LOCALES = ("values", "values-pl", "values-nb", "values-de", "values-es", "values-fr", "values-pt", "values-ar")


def string_keys(path: Path) -> set[str]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    return {node.get("name", "") for node in root.findall("string")}


class SwirPhoneInCallSourceTests(unittest.TestCase):
    def test_manifest_declares_owner_visible_dialer_role_contract(self):
        root = ET.fromstring((ROOT / "AndroidManifest.xml").read_text(encoding="utf-8"))
        self.assertEqual(root.findall("uses-permission"), [])
        application = root.find("application")
        self.assertIsNotNone(application)
        main = next(node for node in application.findall("activity") if node.get(ANDROID + "name") == ".MainActivity")
        filters = main.findall("intent-filter")
        dial_filters = [
            intent_filter
            for intent_filter in filters
            if any(action.get(ANDROID + "name") == "android.intent.action.DIAL" for action in intent_filter.findall("action"))
        ]
        self.assertEqual(len(dial_filters), 2)
        self.assertTrue(
            any(not intent_filter.findall("data") for intent_filter in dial_filters),
            "default-dialer role must expose a bare ACTION_DIAL surface",
        )
        self.assertTrue(
            any(
                any(data.get(ANDROID + "scheme") == "tel" for data in intent_filter.findall("data"))
                for intent_filter in dial_filters
            ),
            "default-dialer role must expose ACTION_DIAL for tel: URIs",
        )
        for intent_filter in dial_filters:
            categories = {node.get(ANDROID + "name") for node in intent_filter.findall("category")}
            self.assertEqual(categories, {"android.intent.category.DEFAULT"})

        incall = next(node for node in application.findall("activity") if node.get(ANDROID + "name") == ".InCallActivity")
        self.assertEqual(incall.get(ANDROID + "exported"), "false")
        service = next(node for node in application.findall("service") if node.get(ANDROID + "name") == ".SwirInCallService")
        self.assertEqual(service.get(ANDROID + "permission"), "android.permission.BIND_INCALL_SERVICE")
        service_actions = {action.get(ANDROID + "name") for f in service.findall("intent-filter") for action in f.findall("action")}
        self.assertEqual(service_actions, {"android.telecom.InCallService"})
        metadata = {node.get(ANDROID + "name"): node.get(ANDROID + "value") for node in service.findall("meta-data")}
        self.assertEqual(metadata.get("android.telecom.IN_CALL_SERVICE_UI"), "true")

    def test_default_role_request_is_explicit_and_outgoing_calls_stay_handoff_only(self):
        source = (ROOT / "src/org/swir/phoneos/phone/MainActivity.java").read_text(encoding="utf-8")
        for token in ("RoleManager.ROLE_DIALER", "createRequestRoleIntent", "startActivityForResult", "Intent.ACTION_DIAL"):
            self.assertIn(token, source)
        for forbidden in ("Intent.ACTION_CALL", "TelecomManager.placeCall", "CALL_PHONE"):
            self.assertNotIn(forbidden, source)

    def test_incall_service_only_mutates_the_owner_visible_active_call(self):
        source = (ROOT / "src/org/swir/phoneos/phone/SwirInCallService.java").read_text(encoding="utf-8")
        for token in ("extends InCallService", "call.answer", "call.reject", "call.disconnect", "Call.STATE_RINGING"):
            self.assertIn(token, source)
        for forbidden in ("TelecomManager.placeCall", "Intent.ACTION_CALL", "Runtime.getRuntime", "ProcessBuilder", "getContentResolver().insert", "getContentResolver().delete"):
            self.assertNotIn(forbidden, source)

    def test_private_or_restricted_caller_identity_is_not_exposed(self):
        source = (ROOT / "src/org/swir/phoneos/phone/SwirInCallService.java").read_text(encoding="utf-8")
        presentation = source.index("getHandlePresentation()")
        allowed = source.index("TelecomManager.PRESENTATION_ALLOWED")
        handle = source.index("details.getHandle()")
        self.assertLess(presentation, handle)
        self.assertLess(allowed, handle)
        self.assertIn('if (details.getHandlePresentation() != TelecomManager.PRESENTATION_ALLOWED) return "";', source)

    def test_incall_activity_is_resource_backed_and_owner_controlled(self):
        source = (ROOT / "src/org/swir/phoneos/phone/InCallActivity.java").read_text(encoding="utf-8")
        for token in ("R.string.answer_call", "R.string.reject_call", "R.string.end_call", "SwirInCallService.answerActiveCall", "SwirInCallService.rejectActiveCall", "SwirInCallService.disconnectActiveCall"):
            self.assertIn(token, source)
        self.assertNotIn('setText("', source)

    def test_exact_stage_fragment_contains_all_new_runtime_sources(self):
        data = json.loads(Path("platform/aosp_product/stage_manifest.d/phone.json").read_text(encoding="utf-8"))
        sources = {entry["source"] for entry in data["files"]}
        self.assertIn("apps/SwirPhone/src/org/swir/phoneos/phone/InCallActivity.java", sources)
        self.assertIn("apps/SwirPhone/src/org/swir/phoneos/phone/SwirInCallService.java", sources)

    def test_all_phone_locales_have_exact_role_and_incall_keys(self):
        expected = string_keys(ROOT / "res/values/strings.xml")
        required = {
            "role_active", "role_inactive", "request_default_phone", "role_unavailable", "open_active_call",
            "incall_title", "incall_number_format", "incall_state_format", "answer_call", "reject_call", "end_call",
            "call_state_ringing", "call_state_active", "call_state_disconnected",
        }
        self.assertTrue(required.issubset(expected))
        for folder in LOCALES:
            self.assertEqual(string_keys(ROOT / f"res/{folder}/strings.xml"), expected, folder)


if __name__ == "__main__":
    unittest.main()
