from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.cuttlefish_evidence import (
    EXPECTED_ANDROID_RELEASE,
    EXPECTED_API_LEVEL,
    EXPECTED_BUILD_TYPE,
    EXPECTED_PRODUCT,
)
from swirphoneos.i18n import LOCALES
from swirphoneos.runtime_review_evidence import (
    RuntimeReviewEvidenceError,
    collect_runtime_review_evidence,
)
from swirphoneos.system_apps import load_registry


class RuntimeReviewEvidenceTests(unittest.TestCase):
    def setUp(self):
        registry = load_registry(Path("system_apps/manifest.json"))
        self.packages = sorted(app.package for app in registry.apps if app.source_ready)
        self.fingerprint = "Swir/test:17/TEST/1:userdebug/test-keys"
        self.digest = hashlib.sha256(self.fingerprint.encode("ascii")).hexdigest()
        self.runtime = {
            "schema_version": 3,
            "runtime_evidence_complete": True,
            "expected_product": EXPECTED_PRODUCT,
            "android_release": EXPECTED_ANDROID_RELEASE,
            "api_level": EXPECTED_API_LEVEL,
            "build_type": EXPECTED_BUILD_TYPE,
            "identity_matches": True,
            "boot_completed": True,
            "device_write_allowed": False,
            "status_promotion_performed": False,
            "build_fingerprint": self.fingerprint,
            "build_fingerprint_sha256": self.digest,
            "required_source_ready_packages": self.packages,
            "present_required_packages": self.packages,
            "present_launchable_packages": self.packages,
            "missing_required_packages": [],
            "missing_launchable_packages": [],
        }
        self.smoke = {
            "schema_version": 1,
            "app_smoke_complete": True,
            "expected_product": EXPECTED_PRODUCT,
            "build_fingerprint": self.fingerprint,
            "build_fingerprint_sha256": self.digest,
            "tested_packages": self.packages,
            "launch_results": [
                {
                    "package": package,
                    "component": f"{package}/.MainActivity",
                    "am_start_status": "ok",
                    "foreground_confirmed": True,
                }
                for package in self.packages
            ],
            "runtime_state_mutation_performed": True,
            "status_promotion_performed": False,
            "physical_device_support_claimed": False,
            "persistent_device_write_allowed": False,
        }
        locales = list(LOCALES)
        rtl = [code for code in locales if LOCALES[code].direction == "rtl"]
        self.i18n = {
            "schema_version": 1,
            "source": "local_cuttlefish_runtime_locale_matrix",
            "expected_product": EXPECTED_PRODUCT,
            "build_fingerprint": self.fingerprint,
            "build_fingerprint_sha256": self.digest,
            "android_user_id": 0,
            "tested_locales": locales,
            "rtl_locales_exercised": rtl,
            "tested_packages": self.packages,
            "locale_results": [
                {
                    "package": package,
                    "locale": locale,
                    "component": f"{package}/.MainActivity",
                    "foreground_confirmed": True,
                }
                for locale in locales
                for package in self.packages
            ],
            "locale_matrix_complete": True,
            "rtl_runtime_switch_exercised": bool(rtl),
            "rtl_visual_mirroring_verified": False,
            "original_app_locales_restored": True,
            "status_promotion_performed": False,
            "physical_device_support_claimed": False,
            "persistent_device_write_allowed": False,
            "runtime_state_mutation_performed": True,
        }

    def _write(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")

    def _collect(self, runtime=None, smoke=None, i18n=None):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime_path = root / "runtime.json"
            smoke_path = root / "smoke.json"
            i18n_path = root / "i18n.json"
            self._write(runtime_path, self.runtime if runtime is None else runtime)
            self._write(smoke_path, self.smoke if smoke is None else smoke)
            self._write(i18n_path, self.i18n if i18n is None else i18n)
            return collect_runtime_review_evidence(
                runtime_path=runtime_path,
                smoke_path=smoke_path,
                i18n_path=i18n_path,
                app_manifest_path=Path("system_apps/manifest.json"),
            )

    def test_collect_binds_exact_boot_launch_and_locale_matrix(self):
        report = self._collect()
        self.assertTrue(report["runtime_review_evidence_complete"])
        self.assertTrue(report["boot_identity_complete"])
        self.assertTrue(report["app_launch_matrix_complete"])
        self.assertTrue(report["locale_matrix_complete"])
        self.assertTrue(report["original_app_locales_restored"])
        self.assertEqual(report["source_ready_packages"], self.packages)
        self.assertEqual(report["tested_locales"], list(LOCALES))
        self.assertFalse(report["rtl_visual_mirroring_verified"])
        self.assertFalse(report["accessibility_review_complete"])
        self.assertFalse(report["visual_translation_review_complete"])
        self.assertFalse(report["physical_device_support_claimed"])
        self.assertFalse(report["device_write_allowed"])
        self.assertFalse(report["status_promotion_performed"])
        self.assertRegex(report["runtime_review_sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_cross_runtime_fingerprint(self):
        smoke = copy.deepcopy(self.smoke)
        smoke["build_fingerprint"] = "Swir/other:17/TEST/2:userdebug/test-keys"
        with self.assertRaises(RuntimeReviewEvidenceError):
            self._collect(smoke=smoke)

    def test_rejects_missing_package_locale_pair(self):
        i18n = copy.deepcopy(self.i18n)
        i18n["locale_results"].pop()
        with self.assertRaises(RuntimeReviewEvidenceError):
            self._collect(i18n=i18n)

    def test_rejects_claimed_visual_rtl_verification(self):
        i18n = copy.deepcopy(self.i18n)
        i18n["rtl_visual_mirroring_verified"] = True
        with self.assertRaises(RuntimeReviewEvidenceError):
            self._collect(i18n=i18n)

    def test_rejects_locale_restoration_failure(self):
        i18n = copy.deepcopy(self.i18n)
        i18n["original_app_locales_restored"] = False
        with self.assertRaises(RuntimeReviewEvidenceError):
            self._collect(i18n=i18n)

    def test_rejects_locale_catalog_drift(self):
        i18n = copy.deepcopy(self.i18n)
        i18n["tested_locales"] = i18n["tested_locales"][:-1]
        with self.assertRaises(RuntimeReviewEvidenceError):
            self._collect(i18n=i18n)

    def test_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime_path = root / "runtime.json"
            smoke_path = root / "smoke.json"
            i18n_path = root / "i18n.json"
            runtime_path.write_text('{"schema_version":3,"schema_version":3}', encoding="utf-8")
            self._write(smoke_path, self.smoke)
            self._write(i18n_path, self.i18n)
            with self.assertRaises(RuntimeReviewEvidenceError):
                collect_runtime_review_evidence(
                    runtime_path=runtime_path,
                    smoke_path=smoke_path,
                    i18n_path=i18n_path,
                    app_manifest_path=Path("system_apps/manifest.json"),
                )


if __name__ == "__main__":
    unittest.main()
