from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.cuttlefish_evidence import EXPECTED_PRODUCT
from swirphoneos.i18n import LOCALES
from swirphoneos.runtime_accessibility_review import (
    RuntimeAccessibilityReviewError,
    create_accessibility_template,
    verify_completed_accessibility_review,
)
from swirphoneos.runtime_visual_review import _sha


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


class RuntimeAccessibilityReviewTests(unittest.TestCase):
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
            "rtl_runtime_switch_exercised": any(
                LOCALES[code].direction == "rtl" for code in locales
            ),
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
    def _complete(
        template: dict[str, object],
        *,
        fail_check: str | None = None,
    ) -> dict[str, object]:
        review = json.loads(json.dumps(template))
        review["reviewer"] = "SWIR accessibility reviewer"
        review["reviewed_at_utc"] = "2026-09-18T19:30:00Z"
        review["assistive_technology"] = "TalkBack"
        for item in review["items"]:
            for check in item["checks"]:
                item["checks"][check] = "PASS"
        if fail_check is not None:
            review["items"][0]["checks"][fail_check] = "FAIL"
            review["items"][0]["note"] = "Observed accessibility regression."
        return review

    def test_template_is_deterministic_pending_and_exactly_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, packages, locales = self._write_inputs(root)
            first = create_accessibility_template(trust_path, visual_path)
            second = create_accessibility_template(trust_path, visual_path)
            self.assertEqual(first, second)
            self.assertEqual(first["capture_count"], len(packages) * len(locales))
            self.assertEqual(first["reviewer"], "")
            self.assertEqual(first["reviewed_at_utc"], "")
            self.assertEqual(first["assistive_technology"], "")
            self.assertEqual(first["input_methods"], ["touch", "keyboard"])
            for item in first["items"]:
                self.assertEqual(
                    set(item["checks"]),
                    {
                        "spoken_labels",
                        "focus_order",
                        "touch_targets",
                        "keyboard_navigation",
                        "state_announcements",
                    },
                )
                self.assertEqual(set(item["checks"].values()), {"PENDING"})

    def test_all_pass_review_computes_accessibility_but_never_promotes_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            review = self._complete(
                create_accessibility_template(trust_path, visual_path)
            )
            review_path = root / "accessibility-review.json"
            review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
            evidence = verify_completed_accessibility_review(
                trust_path, visual_path, review_path
            )
            self.assertTrue(evidence["human_review_complete"])
            self.assertTrue(evidence["accessibility_review_complete"])
            self.assertTrue(evidence["accessibility_review_passed"])
            self.assertEqual(evidence["assistive_technology"], "TalkBack")
            self.assertTrue(evidence["spoken_labels_review_passed"])
            self.assertTrue(evidence["focus_order_review_passed"])
            self.assertTrue(evidence["touch_targets_review_passed"])
            self.assertTrue(evidence["keyboard_navigation_review_passed"])
            self.assertTrue(evidence["state_announcements_review_passed"])
            self.assertEqual(evidence["failed_check_count"], 0)
            self.assertFalse(evidence["visual_translation_review_complete"])
            self.assertFalse(evidence["rtl_visual_mirroring_verified"])
            self.assertFalse(evidence["status_promotion_performed"])
            self.assertFalse(evidence["release_artifact_authorized"])
            self.assertFalse(evidence["device_write_allowed"])

    def test_review_can_be_complete_but_failed_without_hiding_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            review = self._complete(
                create_accessibility_template(trust_path, visual_path),
                fail_check="focus_order",
            )
            review_path = root / "accessibility-review.json"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            evidence = verify_completed_accessibility_review(
                trust_path, visual_path, review_path
            )
            self.assertTrue(evidence["accessibility_review_complete"])
            self.assertFalse(evidence["accessibility_review_passed"])
            self.assertFalse(evidence["focus_order_review_passed"])
            self.assertEqual(evidence["failed_check_count"], 1)
            self.assertEqual(evidence["failed_checks"][0]["check"], "focus_order")
            self.assertIn("note", evidence["failed_checks"][0])

    def test_pending_unknown_fields_and_scope_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            template = create_accessibility_template(trust_path, visual_path)
            template["reviewer"] = "Reviewer"
            template["reviewed_at_utc"] = "2026-09-18T19:30:00Z"
            review_path = root / "accessibility-review.json"
            review_path.write_text(json.dumps(template), encoding="utf-8")
            with self.assertRaises(RuntimeAccessibilityReviewError):
                verify_completed_accessibility_review(
                    trust_path, visual_path, review_path
                )

            complete = self._complete(
                create_accessibility_template(trust_path, visual_path)
            )
            complete["items"][0]["checks"]["unexpected"] = "PASS"
            review_path.write_text(json.dumps(complete), encoding="utf-8")
            with self.assertRaises(RuntimeAccessibilityReviewError):
                verify_completed_accessibility_review(
                    trust_path, visual_path, review_path
                )

            complete = self._complete(
                create_accessibility_template(trust_path, visual_path)
            )
            complete["input_methods"] = ["touch"]
            review_path.write_text(json.dumps(complete), encoding="utf-8")
            with self.assertRaises(RuntimeAccessibilityReviewError):
                verify_completed_accessibility_review(
                    trust_path, visual_path, review_path
                )

            complete = self._complete(
                create_accessibility_template(trust_path, visual_path)
            )
            complete["assistive_technology"] = ""
            review_path.write_text(json.dumps(complete), encoding="utf-8")
            with self.assertRaises(RuntimeAccessibilityReviewError):
                verify_completed_accessibility_review(
                    trust_path, visual_path, review_path
                )

    def test_capture_identity_and_trust_overclaim_cannot_be_forged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            trust_path, visual_path, _packages, _locales = self._write_inputs(root)
            review = self._complete(
                create_accessibility_template(trust_path, visual_path)
            )
            review["items"][0]["sha256"] = "f" * 64
            review_path = root / "accessibility-review.json"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaises(RuntimeAccessibilityReviewError):
                verify_completed_accessibility_review(
                    trust_path, visual_path, review_path
                )

            trust = json.loads(trust_path.read_text(encoding="utf-8"))
            trust["release_artifact_authorized"] = True
            trust["runtime_visual_trust_bundle_sha256"] = _sha(
                {
                    key: value
                    for key, value in trust.items()
                    if key != "runtime_visual_trust_bundle_sha256"
                }
            )
            trust_path.write_text(json.dumps(trust), encoding="utf-8")
            with self.assertRaises(RuntimeAccessibilityReviewError):
                create_accessibility_template(trust_path, visual_path)


if __name__ == "__main__":
    unittest.main()
