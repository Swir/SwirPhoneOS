from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_run_evidence import AospRunEvidenceError, collect_aosp_run_evidence
from swirphoneos.build_evidence import create_evidence_bundle
from swirphoneos.system_apps import load_registry


class AospRunEvidenceTests(unittest.TestCase):
    SOURCE_COMMIT = "1" * 40
    WORKSPACE = "/tmp/swir-aosp"
    FINGERPRINT = "Swir/swirphoneos_cf_x86_64/vsoc_x86_64_only:17/CP2A.260605.016/1:userdebug/test-keys"
    APP_MANIFEST = Path("system_apps/manifest.json")
    PACKAGES = sorted(app.package for app in load_registry(APP_MANIFEST).first_beta_apps)

    def _reports(self) -> dict[str, dict[str, object]]:
        manifest_sha = "a" * 64
        stage_sha = "c" * 64
        fingerprint_sha = hashlib.sha256(self.FINGERPRINT.encode("ascii")).hexdigest()
        preflight = {
            "schema_version": 1,
            "operation": "READ_ONLY_HOST_PREFLIGHT",
            "ready_for_source_sync": True,
            "ready_for_full_build": True,
            "cuttlefish_kvm_available": True,
        }
        plan = {
            "schema_version": 2,
            "workspace": self.WORKSPACE,
            "revision": "android-17.0.0_r1",
            "lunch_choice": "swirphoneos_cf_x86_64-aosp_current-userdebug",
            "device_write_allowed": False,
            "build_verified": False,
            "boot_verified": False,
        }
        manifest = {
            "schema_version": 1,
            "project_count": 2,
            "unique_path_count": 2,
            "sha256": manifest_sha,
            "all_projects_pinned": True,
            "build_verified": False,
            "boot_verified": False,
        }
        stage = {
            "schema_version": 5,
            "workspace": self.WORKSPACE,
            "executed": True,
            "copy_verified": True,
            "destination_tree_closed": True,
            "file_count": 1,
            "preexisting_destination_file_count": 0,
            "destination_file_count": 1,
            "device_write_allowed": False,
            "staged_content_sha256": stage_sha,
            "files": [{
                "destination_relative": "vendor/swir/products/SwirPhoneOS.mk",
                "copy_verified": True,
                "size": 4,
                "sha256": "b" * 64,
            }],
        }
        post_stage = {
            "schema_version": 1,
            "workspace": self.WORKSPACE,
            "stage_report_schema": 5,
            "staged_content_sha256": stage_sha,
            "file_count": 1,
            "destination_file_count": 1,
            "destination_tree_closed": True,
            "post_build_verified": True,
            "verification_sha256": "d" * 64,
            "device_write_allowed": False,
            "status_promotion_performed": False,
        }
        build = {
            "schema_version": 1,
            "source": "local_aosp_build_output",
            "expected_product": "swirphoneos_cf_x86_64",
            "baseline_revision": "android-17.0.0_r1",
            "baseline_identity": {
                "build_id": "CP2A.260605.016",
                "android_release": "17",
                "api_level": "37",
                "security_patch": "2026-06-05",
                "build_type": "userdebug",
            },
            "resolved_manifest": {
                "project_count": 2,
                "unique_path_count": 2,
                "sha256": manifest_sha,
                "all_projects_pinned": True,
            },
            "build": {
                "fingerprint": self.FINGERPRINT,
                "build_id": "CP2A.260605.016",
                "android_release": "17",
                "api_level": "37",
                "security_patch": "2026-06-05",
                "build_type": "userdebug",
            },
            "artifacts": [
                {"path": "boot.img", "size": 4, "sha256": "e" * 64},
                {"path": "system.img", "size": 6, "sha256": "f" * 64},
            ],
            "required_artifacts": ["boot.img", "system.img"],
            "build_evidence_complete": True,
            "device_write_allowed": False,
            "status_promotion_performed": False,
        }
        runtime = {
            "schema_version": 3,
            "expected_product": "swirphoneos_cf_x86_64",
            "build_fingerprint": self.FINGERPRINT,
            "build_fingerprint_sha256": fingerprint_sha,
            "android_release": "17",
            "api_level": "37",
            "build_type": "userdebug",
            "boot_completed": True,
            "identity_matches": True,
            "required_source_ready_packages": list(self.PACKAGES),
            "present_required_packages": list(self.PACKAGES),
            "missing_required_packages": [],
            "present_launchable_packages": list(self.PACKAGES),
            "missing_launchable_packages": [],
            "runtime_evidence_complete": True,
            "status_promotion_performed": False,
            "device_write_allowed": False,
        }
        smoke = {
            "schema_version": 1,
            "expected_product": "swirphoneos_cf_x86_64",
            "build_fingerprint": self.FINGERPRINT,
            "build_fingerprint_sha256": fingerprint_sha,
            "tested_packages": list(self.PACKAGES),
            "launch_results": [
                {
                    "package": package,
                    "component": package + "/.MainActivity",
                    "am_start_status": "ok",
                    "foreground_confirmed": True,
                }
                for package in self.PACKAGES
            ],
            "app_smoke_complete": True,
            "status_promotion_performed": False,
            "physical_device_support_claimed": False,
            "persistent_device_write_allowed": False,
            "runtime_state_mutation_performed": True,
        }
        bundle = create_evidence_bundle(build, runtime)
        return {
            "preflight": preflight,
            "plan": plan,
            "manifest": manifest,
            "stage": stage,
            "post_stage": post_stage,
            "build": build,
            "runtime": runtime,
            "smoke": smoke,
            "bundle": bundle,
        }

    def _write(self, root: Path, reports: dict[str, dict[str, object]]) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for name, report in reports.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
            paths[name] = path
        return paths

    def _collect(self, paths: dict[str, Path], runtime: bool) -> dict[str, object]:
        kwargs = {
            "source_commit": self.SOURCE_COMMIT,
            "preflight_path": paths["preflight"],
            "plan_path": paths["plan"],
            "manifest_path": paths["manifest"],
            "stage_path": paths["stage"],
            "post_stage_path": paths["post_stage"],
            "build_path": paths["build"],
            "app_manifest_path": self.APP_MANIFEST,
        }
        if runtime:
            kwargs.update({
                "runtime_path": paths["runtime"],
                "smoke_path": paths["smoke"],
                "bundle_path": paths["bundle"],
            })
        return collect_aosp_run_evidence(**kwargs)

    def test_accepts_build_only_chain(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write(Path(temporary), self._reports())
            result = self._collect(paths, runtime=False)
            self.assertTrue(result["run_evidence_complete"])
            self.assertTrue(result["build_chain_complete"])
            self.assertFalse(result["runtime_chain_complete"])
            self.assertEqual(result["scope"], "BUILD_ONLY")
            self.assertEqual(result["source_ready_packages"], self.PACKAGES)
            self.assertEqual(len(result["app_manifest_sha256"]), 64)
            self.assertFalse(result["device_write_allowed"])
            self.assertEqual(len(result["run_evidence_sha256"]), 64)

    def test_accepts_complete_build_and_runtime_chain(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write(Path(temporary), self._reports())
            result = self._collect(paths, runtime=True)
            self.assertTrue(result["run_evidence_complete"])
            self.assertTrue(result["runtime_chain_complete"])
            self.assertEqual(result["scope"], "BUILD_AND_RUNTIME")
            self.assertEqual(result["source_ready_packages"], self.PACKAGES)
            self.assertIn("bundle", result["report_file_sha256"])

    def test_rejects_cross_run_stage_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = self._reports()
            reports["post_stage"]["staged_content_sha256"] = "9" * 64
            paths = self._write(Path(temporary), reports)
            with self.assertRaises(AospRunEvidenceError):
                self._collect(paths, runtime=False)

    def test_rejects_stage_without_exact_tree_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = self._reports()
            reports["stage"]["destination_tree_closed"] = False
            paths = self._write(Path(temporary), reports)
            with self.assertRaises(AospRunEvidenceError):
                self._collect(paths, runtime=False)

    def test_rejects_post_build_tree_closure_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = self._reports()
            reports["post_stage"]["destination_file_count"] = 2
            paths = self._write(Path(temporary), reports)
            with self.assertRaises(AospRunEvidenceError):
                self._collect(paths, runtime=False)

    def test_rejects_runtime_smoke_package_set_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = self._reports()
            reports["smoke"]["tested_packages"] = self.PACKAGES[:-1]
            paths = self._write(Path(temporary), reports)
            with self.assertRaises(AospRunEvidenceError):
                self._collect(paths, runtime=True)

    def test_rejects_runtime_package_set_that_omits_first_beta_app(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = self._reports()
            subset = self.PACKAGES[:-1]
            reports["runtime"]["required_source_ready_packages"] = subset
            reports["runtime"]["present_required_packages"] = subset
            reports["runtime"]["present_launchable_packages"] = subset
            reports["smoke"]["tested_packages"] = subset
            reports["smoke"]["launch_results"] = reports["smoke"]["launch_results"][:-1]
            reports["bundle"] = create_evidence_bundle(reports["build"], reports["runtime"])
            paths = self._write(Path(temporary), reports)
            with self.assertRaises(AospRunEvidenceError):
                self._collect(paths, runtime=True)

    def test_rejects_bundle_that_embeds_different_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = self._reports()
            other_runtime = copy.deepcopy(reports["runtime"])
            other_runtime["reported_model"] = "Different run"
            reports["bundle"] = create_evidence_bundle(reports["build"], other_runtime)
            paths = self._write(Path(temporary), reports)
            with self.assertRaises(AospRunEvidenceError):
                self._collect(paths, runtime=True)

    def test_rejects_partial_runtime_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write(Path(temporary), self._reports())
            with self.assertRaises(AospRunEvidenceError):
                collect_aosp_run_evidence(
                    source_commit=self.SOURCE_COMMIT,
                    preflight_path=paths["preflight"],
                    plan_path=paths["plan"],
                    manifest_path=paths["manifest"],
                    stage_path=paths["stage"],
                    post_stage_path=paths["post_stage"],
                    build_path=paths["build"],
                    app_manifest_path=self.APP_MANIFEST,
                    runtime_path=paths["runtime"],
                )

    def test_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write(Path(temporary), self._reports())
            paths["preflight"].write_text(
                '{"schema_version":1,"schema_version":1,"operation":"READ_ONLY_HOST_PREFLIGHT"}',
                encoding="utf-8",
            )
            with self.assertRaises(AospRunEvidenceError):
                self._collect(paths, runtime=False)


if __name__ == "__main__":
    unittest.main()
