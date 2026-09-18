from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.cuttlefish_evidence import EXPECTED_PRODUCT
from swirphoneos.i18n import LOCALES
from swirphoneos.runtime_visual_review import (
    RuntimeVisualReviewError,
    _sha,
    create_review_template,
    verify_completed_review,
)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


class RuntimeVisualReviewTests(unittest.TestCase):
    def _write_inputs(self, root: Path):
        packages = ["org.swirphoneos.alpha", "org.swirphoneos.beta"]
        locales = list(LOCALES)
        captures = []
        index = 0
        for locale in locales:
            for package in packages:
                index += 1
                captures.append(
                    {
                        "relative_path": f"{index:03d}_{package}__{locale}.png",
                        "size": 1234 + index,
                        "sha256": f"{index:064x}",
                        "width": 1080,
                        "height": 2400,
                        "package": package,
                        "locale": locale,
                        "direction": LOCALES[locale].direction,
                        "component": f"{package}/.MainActivity",
                        "foreground_confirmed": True,
                    }
                )

        visual = {
            "schema_version": 1,
            "source": "local_cuttlefish_visual_capture_matrix",
            "expected_product": EXPECTED_PRODUCT,
            "build_fingerprint": "Swir/test:17/TEST/1:userdebug/test-keys",
            "build_fingerprint_sha256": HEX_B,
            "android_user_id": 0,
            "tested_packages": packages,
            "tested_locales": locales,
            "capture_count": len(captures),
            "captures": captures,
            "capture_set_sha256": _sha(captures),
            "capture_matrix_complete": True,
            "visual_bytes_captured": True,
            "original_app_locales_restored": True,
            "rtl_runtime_switch_exercised": any(LOCALES[code].direction == "rtl" for code in locales),
            "rtl_visual_mirroring_verified": False,
            "accessibility_review_complete": False,
            "visual_translation_review_complete": False,
            "status_promotion_performed": False,
            "physical_device_support_claimed": False,
            "runtime_state_mutation_performed": True,
            "host_evidence_write_performed": True,
            "persistent_device_write_allowed": False,
        }
        visual["visual_capture_sha256"] = _sha(visual)

        trust = {
            "schema_version": 1,
            "source": "local_cuttlefish_visual_trust_bundle",
            "scope": "CUTTLEFISH_BUILD_RUNTIME_I18N_VISUAL_CAPTURE_AND_EXACT_ADB",
            "expected_product": EXPECTED_PRODUCT,
            "runtime_review_trust_bundle_sha256": HEX_A,
            "visual_capture_sha256": visual["visual_capture_sha256"],
            "build_fingerprint_sha256": HEX_B,
            "app_manifest_sha256": HEX_C,
            "source_ready_packages": packages,
            "tested_locales": locales,
            "adb_sha256": HEX_A,
            "adb_path_identity_sha256": HEX_C,
            "adb_size": 1024,
            "report_file_sha256": {
                "runtime_review_trust_bundle": HEX_A,
                "visual_capture_evidence": HEX_B,
            },
            "capture_count": len(captures),
            "capture_directory_sha256": HEX_C,
            "capture_total_bytes": sum(item["size"] for item in captures),
            "visual_capture_matrix_complete": True,
            "visual_bytes_reverified": True,
            "rtl_visual_mirroring_verified": False,
            "accessibility_review_complete": False,
            "visual_translation_review_complete": False,
            "physical_device_support_claimed": False,
            "device_write_allowed": False,
            "status_promotion_performed": False,
            "release_artifact_authorized": False,
            "warnings": ["fixture"],
        }
        trust["runtime_visual_trust_bundle_sha256"] = _sha(trust)

        visual_path = root / "runtime-visual-evidence.json"
        trust_path = root / "runtime-visual-trust-bundle.json"
        visual_path.write_text(json.dumps(visual, indent=2), encoding="utf-8")
        trust_path.write_text(json.dumps(trust, indent=2), encoding="utf-8")
        return trust_path, visual_path, packages, locales

    @staticmethod
    def _complete(template: dict[str, object], *, pass_all: bool = True) -> dict[str, object]:
        review = json.loads(json.dumps(template))
        review["reviewer"] = "SWIR visual reviewer"
        review["reviewed_at_utc"] = "2026-09-18T18:30:00Z"
        for item in review["items"]:
            item["checks"]["translation"] = "PASS"
            item["checks"]["text_clipping"] = "PASS"
            if item["direction"] == "rtl":
                item["checks"]["rtl_mirroring"] = "PASS"
        if not pass_all:
            review["items"][0]["checks"]["translation"] = "FAIL"
            review["items"][0]["note"] = "Translation mismatch observed."
        return review

    def test_template_is_deterministic_pending_and_bound_to_exact_matrix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, packages, locales = self._write_inputs(root)
            first = create_review_template(trust_path, visual_path)
            second = create_review_template(trust_path, visual_path)
            self.assertEqual(first, second)
            self.assertEqual(first["capture_count"], len(packages) * len(locales))
            self.assertEqual(first["reviewer"], "")
            self.assertEqual(first["reviewed_at_utc"], "")
            self.assertEqual(len(first["items"]), len(packages) * len(locales))
            for item in first["items"]:
                self.assertEqual(item["checks"]["translation"], "PENDING")
                self.assertEqual(item["checks"]["text_clipping"], "PENDING")
                expected = "PENDING" if item["direction"] == "rtl" else "NOT_APPLICABLE"
                self.assertEqual(item["checks"]["rtl_mirroring"], expected)

    def test_verified_all_pass_review_computes_review_flags_but_not_accessibility_or_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            review = self._complete(create_review_template(trust_path, visual_path))
            review_path = root / "review.json"
            review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
            evidence = verify_completed_review(trust_path, visual_path, review_path)
            self.assertTrue(evidence["human_review_complete"])
            self.assertTrue(evidence["visual_translation_review_complete"])
            self.assertTrue(evidence["visual_translation_review_passed"])
            self.assertTrue(evidence["text_clipping_review_complete"])
            self.assertTrue(evidence["text_clipping_review_passed"])
            self.assertTrue(evidence["rtl_visual_review_complete"])
            self.assertTrue(evidence["rtl_visual_mirroring_verified"])
            self.assertEqual(evidence["failed_check_count"], 0)
            self.assertFalse(evidence["accessibility_review_complete"])
            self.assertFalse(evidence["status_promotion_performed"])
            self.assertFalse(evidence["release_artifact_authorized"])

    def test_review_can_be_complete_but_failed_without_overclaiming_quality(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            review = self._complete(create_review_template(trust_path, visual_path), pass_all=False)
            review_path = root / "review.json"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            evidence = verify_completed_review(trust_path, visual_path, review_path)
            self.assertTrue(evidence["human_review_complete"])
            self.assertTrue(evidence["visual_translation_review_complete"])
            self.assertFalse(evidence["visual_translation_review_passed"])
            self.assertEqual(evidence["failed_check_count"], 1)
            self.assertEqual(evidence["failed_checks"][0]["check"], "translation")
            self.assertFalse(evidence["accessibility_review_complete"])

    def test_pending_or_malformed_rtl_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            template = create_review_template(trust_path, visual_path)
            template["reviewer"] = "Reviewer"
            template["reviewed_at_utc"] = "2026-09-18T18:30:00Z"
            review_path = root / "review.json"
            review_path.write_text(json.dumps(template), encoding="utf-8")
            with self.assertRaises(RuntimeVisualReviewError):
                verify_completed_review(trust_path, visual_path, review_path)

            complete = self._complete(create_review_template(trust_path, visual_path))
            ltr = next(item for item in complete["items"] if item["direction"] == "ltr")
            ltr["checks"]["rtl_mirroring"] = "PASS"
            review_path.write_text(json.dumps(complete), encoding="utf-8")
            with self.assertRaises(RuntimeVisualReviewError):
                verify_completed_review(trust_path, visual_path, review_path)

    def test_cross_evidence_tamper_and_trust_overclaim_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            trust = json.loads(trust_path.read_text(encoding="utf-8"))
            trust["release_artifact_authorized"] = True
            trust["runtime_visual_trust_bundle_sha256"] = _sha(
                {key: value for key, value in trust.items() if key != "runtime_visual_trust_bundle_sha256"}
            )
            trust_path.write_text(json.dumps(trust), encoding="utf-8")
            with self.assertRaises(RuntimeVisualReviewError):
                create_review_template(trust_path, visual_path)

    def test_review_capture_identity_cannot_be_swapped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            review = self._complete(create_review_template(trust_path, visual_path))
            review["items"][0]["sha256"] = "f" * 64
            review_path = root / "review.json"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaises(RuntimeVisualReviewError):
                verify_completed_review(trust_path, visual_path, review_path)


if __name__ == "__main__":
    unittest.main()
