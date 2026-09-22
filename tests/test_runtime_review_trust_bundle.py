from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.cuttlefish_evidence import EXPECTED_PRODUCT
from swirphoneos.i18n import LOCALES
from swirphoneos.runtime_review_trust_bundle import (
    RuntimeReviewTrustBundleError,
    create_runtime_review_trust_bundle,
)
from swirphoneos.system_apps import load_registry


class RuntimeReviewTrustBundleTests(unittest.TestCase):
    FINGERPRINT = "Swir/swirphoneos_cf_x86_64/vsoc_x86_64_only:17/CP2A.260605.016/1:userdebug/test-keys"

    def setUp(self) -> None:
        self.packages = sorted(
            app.package for app in load_registry(Path("system_apps/manifest.json")).apps if app.source_ready
        )
        self.fingerprint_sha = hashlib.sha256(self.FINGERPRINT.encode("ascii")).hexdigest()
        self.manifest_sha = "c" * 64

    @staticmethod
    def _canonical(value: dict[str, object], excluded: set[str] | None = None) -> str:
        excluded = excluded or set()
        payload = {key: item for key, item in value.items() if key not in excluded}
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()

    def _reports(self) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        run: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "source_commit": "1" * 40,
            "scope": "BUILD_AND_RUNTIME",
            "expected_product": EXPECTED_PRODUCT,
            "workspace_sha256": "a" * 64,
            "staged_content_sha256": "b" * 64,
            "build_fingerprint": self.FINGERPRINT,
            "build_fingerprint_sha256": self.fingerprint_sha,
            "app_manifest_sha256": self.manifest_sha,
            "source_ready_packages": list(self.packages),
            "report_file_sha256": {"runtime": "d" * 64},
            "build_chain_complete": True,
            "runtime_chain_complete": True,
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
            "warnings": ["synthetic test fixture"],
        }
        run["run_evidence_sha256"] = self._canonical(run)
        run["run_evidence_complete"] = True

        trust: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_runtime_trust_bundle",
            "scope": "CUTTLEFISH_BUILD_RUNTIME_AND_EXACT_ADB",
            "run_evidence_sha256": run["run_evidence_sha256"],
            "build_fingerprint_sha256": self.fingerprint_sha,
            "adb_sha256": "e" * 64,
            "adb_path_identity_sha256": "f" * 64,
            "adb_size": 123456,
            "report_file_sha256": {"aosp_run_evidence": "1" * 64},
            "runtime_tool_unchanged_across_evidence_window": True,
            "runtime_trust_chain_complete": True,
            "tool_capture_executed_adb": False,
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
            "warnings": ["synthetic test fixture"],
        }
        trust["runtime_trust_bundle_sha256"] = self._canonical(trust)

        locales = list(LOCALES)
        review: dict[str, object] = {
            "schema_version": 1,
            "source": "local_cuttlefish_runtime_review_bundle",
            "expected_product": EXPECTED_PRODUCT,
            "build_fingerprint": self.FINGERPRINT,
            "build_fingerprint_sha256": self.fingerprint_sha,
            "app_manifest_sha256": self.manifest_sha,
            "source_ready_packages": list(self.packages),
            "tested_locales": locales,
            "report_file_sha256": {"runtime": "2" * 64, "smoke": "3" * 64, "i18n": "4" * 64},
            "boot_identity_complete": True,
            "home_surface_complete": True,
            "app_launch_matrix_complete": True,
            "locale_matrix_complete": True,
            "original_app_locales_restored": True,
            "rtl_runtime_switch_exercised": bool([code for code in locales if LOCALES[code].direction == "rtl"]),
            "rtl_visual_mirroring_verified": False,
            "accessibility_review_complete": False,
            "visual_translation_review_complete": False,
            "physical_device_support_claimed": False,
            "device_write_allowed": False,
            "status_promotion_performed": False,
            "warnings": ["synthetic test fixture"],
        }
        review["runtime_review_sha256"] = self._canonical(review)
        review["runtime_review_evidence_complete"] = True
        return run, trust, review

    @staticmethod
    def _write(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def _collect(self, run=None, trust=None, review=None) -> dict[str, object]:
        base_run, base_trust, base_review = self._reports()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_path = root / "aosp-run-evidence.json"
            trust_path = root / "runtime-trust-bundle.json"
            review_path = root / "runtime-review-evidence.json"
            self._write(run_path, base_run if run is None else run)
            self._write(trust_path, base_trust if trust is None else trust)
            self._write(review_path, base_review if review is None else review)
            return create_runtime_review_trust_bundle(run_path, trust_path, review_path)

    def test_binds_exact_run_home_review_and_adb_trust(self) -> None:
        report = self._collect()
        self.assertEqual(report["scope"], "CUTTLEFISH_BUILD_RUNTIME_I18N_AND_EXACT_ADB")
        self.assertTrue(report["build_runtime_chain_complete"])
        self.assertTrue(report["home_surface_complete"])
        self.assertTrue(report["locale_review_chain_complete"])
        self.assertTrue(report["runtime_tool_unchanged_across_evidence_window"])
        self.assertEqual(report["source_ready_packages"], self.packages)
        self.assertEqual(report["tested_locales"], list(LOCALES))
        self.assertFalse(report["rtl_visual_mirroring_verified"])
        self.assertFalse(report["accessibility_review_complete"])
        self.assertFalse(report["physical_device_support_claimed"])
        self.assertFalse(report["device_write_allowed"])
        self.assertFalse(report["status_promotion_performed"])
        self.assertRegex(report["runtime_review_trust_bundle_sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_run_canonical_digest_tampering(self) -> None:
        run, trust, review = self._reports()
        run["workspace_sha256"] = "9" * 64
        with self.assertRaises(RuntimeReviewTrustBundleError):
            self._collect(run=run, trust=trust, review=review)

    def test_rejects_runtime_trust_adb_tampering_even_with_recomputed_digest(self) -> None:
        run, trust, review = self._reports()
        trust["adb_sha256"] = "9" * 64
        trust["runtime_trust_bundle_sha256"] = self._canonical(
            trust, {"runtime_trust_bundle_sha256"}
        )
        report = self._collect(run=run, trust=trust, review=review)
        self.assertEqual(report["adb_sha256"], "9" * 64)
        self.assertNotEqual(report["adb_sha256"], "e" * 64)

    def test_rejects_runtime_trust_run_mismatch(self) -> None:
        run, trust, review = self._reports()
        trust["run_evidence_sha256"] = "9" * 64
        trust["runtime_trust_bundle_sha256"] = self._canonical(
            trust, {"runtime_trust_bundle_sha256"}
        )
        with self.assertRaises(RuntimeReviewTrustBundleError):
            self._collect(run=run, trust=trust, review=review)

    def test_rejects_review_manifest_mismatch_even_with_recomputed_digest(self) -> None:
        run, trust, review = self._reports()
        review["app_manifest_sha256"] = "9" * 64
        review["runtime_review_sha256"] = self._canonical(
            review, {"runtime_review_sha256", "runtime_review_evidence_complete"}
        )
        with self.assertRaises(RuntimeReviewTrustBundleError):
            self._collect(run=run, trust=trust, review=review)

    def test_rejects_missing_home_surface_even_with_recomputed_digest(self) -> None:
        run, trust, review = self._reports()
        review["home_surface_complete"] = False
        review["runtime_review_sha256"] = self._canonical(
            review, {"runtime_review_sha256", "runtime_review_evidence_complete"}
        )
        with self.assertRaises(RuntimeReviewTrustBundleError):
            self._collect(run=run, trust=trust, review=review)

    def test_rejects_review_locale_catalog_drift(self) -> None:
        run, trust, review = self._reports()
        review["tested_locales"] = review["tested_locales"][:-1]
        review["runtime_review_sha256"] = self._canonical(
            review, {"runtime_review_sha256", "runtime_review_evidence_complete"}
        )
        with self.assertRaises(RuntimeReviewTrustBundleError):
            self._collect(run=run, trust=trust, review=review)

    def test_rejects_visual_rtl_overclaim(self) -> None:
        run, trust, review = self._reports()
        review["rtl_visual_mirroring_verified"] = True
        review["runtime_review_sha256"] = self._canonical(
            review, {"runtime_review_sha256", "runtime_review_evidence_complete"}
        )
        with self.assertRaises(RuntimeReviewTrustBundleError):
            self._collect(run=run, trust=trust, review=review)

    def test_rejects_duplicate_json_keys(self) -> None:
        run, trust, review = self._reports()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_path = root / "aosp-run-evidence.json"
            trust_path = root / "runtime-trust-bundle.json"
            review_path = root / "runtime-review-evidence.json"
            run_path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            self._write(trust_path, trust)
            self._write(review_path, review)
            with self.assertRaises(RuntimeReviewTrustBundleError):
                create_runtime_review_trust_bundle(run_path, trust_path, review_path)


if __name__ == "__main__":
    unittest.main()
