from __future__ import annotations

import unittest

from swirphoneos.identity import (
    IdentityAssessmentError,
    assess_profile_hint,
    build_unified_report,
    validate_unified_report,
)
from swirphoneos.profiles import DeviceProfile


def profile(profile_id: str = "oneplus/avicii", codename: str = "avicii", model: str = "AC2003") -> DeviceProfile:
    return DeviceProfile(
        profile_id=profile_id,
        display_name="Synthetic Profile",
        codename=codename,
        model_allowlist=(model,),
        status="PLANNED_NOT_SUPPORTED",
        firmware_baseline=None,
        sources=("https://example.com/device",),
    )


class IdentityAssessmentTests(unittest.TestCase):
    def test_adb_codename_yields_hint_not_identity(self):
        report = {"codename": "avicii", "model": "something", "flash_allowed": False,
                  "swirphoneos_support": "NOT_VALIDATED"}
        result = assess_profile_hint("adb", report, [profile()])
        self.assertEqual(result["result"], "PROFILE_HINT_ONLY")
        self.assertEqual(result["candidate_profile_id"], "oneplus/avicii")
        self.assertFalse(result["identity_verified"])
        self.assertFalse(result["flash_allowed"])

    def test_adb_model_allowlist_can_hint(self):
        report = {"codename": "unknown", "model": "ac2003", "flash_allowed": False,
                  "swirphoneos_support": "NOT_VALIDATED"}
        result = assess_profile_hint("adb", report, [profile()])
        self.assertIn("adb_model_matches_profile_allowlist", result["evidence"])

    def test_fastboot_product_can_hint(self):
        report = {"product_reported": "avicii", "flash_allowed": False,
                  "swirphoneos_support": "NOT_VALIDATED"}
        result = assess_profile_hint("fastboot", report, [profile()])
        self.assertEqual(result["candidate_profile_id"], "oneplus/avicii")

    def test_ambiguous_hint_exposes_no_candidate(self):
        report = {"codename": "same", "model": None, "flash_allowed": False,
                  "swirphoneos_support": "NOT_VALIDATED"}
        result = assess_profile_hint("adb", report, [
            profile("vendor/one", "same", "ONE"), profile("vendor/two", "same", "TWO")
        ])
        self.assertEqual(result["result"], "AMBIGUOUS_PROFILE_HINT")
        self.assertIsNone(result["candidate_profile_id"])
        self.assertEqual(result["evidence"], [])

    def test_unified_report_is_fail_closed(self):
        transport_report = {"codename": "avicii", "model": "AC2003", "flash_allowed": False,
                            "swirphoneos_support": "NOT_VALIDATED"}
        report = build_unified_report("adb", transport_report, [profile()])
        validate_unified_report(report)
        self.assertFalse(report["flash_allowed"])
        self.assertFalse(report["profile_assessment"]["identity_verified"])

    def test_tampered_nested_support_is_rejected(self):
        transport_report = {"codename": "avicii", "model": "AC2003", "flash_allowed": False,
                            "swirphoneos_support": "NOT_VALIDATED"}
        report = build_unified_report("adb", transport_report, [profile()])
        report["transport_report"]["swirphoneos_support"] = "VERIFIED"
        with self.assertRaises(IdentityAssessmentError):
            validate_unified_report(report)


if __name__ == "__main__":
    unittest.main()
