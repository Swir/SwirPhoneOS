from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.gsi_contract import GsiContractError, public_gsi_contract_summary, validate_gsi_contract
from swirphoneos.gsi_evidence import GsiEvidenceError, collect_gsi_build_evidence
from swirphoneos.gsi_workspace import GsiWorkspaceError, make_gsi_workspace_plan, public_gsi_workspace_plan
from swirphoneos.platform import load_baseline


MODULES = (
    "SwirPhone", "SwirMessages", "SwirCamera", "SwirCalculator", "SwirSettings",
    "SwirFiles", "SwirBrowser", "SwirDeviceCare", "SwirUpdate", "SwirPrivacy",
    "SwirClock", "SwirNotes", "SwirCalendar", "SwirWeather", "SwirGallery",
    "SwirRecorder", "SwirContacts", "SwirBackup", "SwirApps", "SwirRoot",
)


class GsiFoundationTests(unittest.TestCase):
    def test_checked_in_gsi_contract_is_source_only_and_complete(self):
        contract = validate_gsi_contract(Path("platform/aosp_product"))
        summary = public_gsi_contract_summary(contract)
        self.assertEqual(contract.product_name, "swirphoneos_gsi_arm64")
        self.assertEqual(contract.device, "generic_arm64")
        self.assertEqual(contract.architecture, "arm64")
        self.assertEqual(len(contract.package_modules), 20)
        self.assertEqual(summary["source_ready_package_count"], 20)
        self.assertEqual(summary["expected_artifact"], "out/target/product/generic_arm64/system.img")
        self.assertFalse(summary["build_verified"])
        self.assertFalse(summary["treble_vts_verified"])
        self.assertFalse(summary["physical_device_compatibility_verified"])
        self.assertFalse(summary["install_verified"])
        self.assertFalse(summary["device_write_allowed"])
        self.assertFalse(summary["release_artifact"])

    def test_gsi_plan_is_pinned_build_only_and_targets_systemimage(self):
        baseline = load_baseline(Path("platform/aosp_baseline.json"))
        contract = validate_gsi_contract(Path("platform/aosp_product"))
        with tempfile.TemporaryDirectory() as temp:
            plan = make_gsi_workspace_plan(baseline, contract, Path(temp) / "aosp", jobs=12)
            summary = public_gsi_workspace_plan(plan)
        self.assertEqual(plan.revision, "android-17.0.0_r1")
        self.assertEqual(plan.lunch_choice, "swirphoneos_gsi_arm64-aosp_current-userdebug")
        self.assertIn("systemimage", plan.commands[-1][-1])
        self.assertTrue(str(plan.expected_system_image).endswith("out/target/product/generic_arm64/system.img"))
        self.assertFalse(summary["build_verified"])
        self.assertFalse(summary["treble_vts_verified"])
        self.assertFalse(summary["physical_device_compatibility_verified"])
        self.assertFalse(summary["install_verified"])
        self.assertFalse(summary["device_write_allowed"])

    def test_gsi_plan_rejects_root_workspace_and_bad_jobs(self):
        baseline = load_baseline(Path("platform/aosp_baseline.json"))
        contract = validate_gsi_contract(Path("platform/aosp_product"))
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(GsiWorkspaceError):
                make_gsi_workspace_plan(baseline, contract, Path(Path(temp).anchor))
            with self.assertRaises(GsiWorkspaceError):
                make_gsi_workspace_plan(baseline, contract, Path(temp) / "aosp", jobs=0)

    def _contract_fixture(self, root: Path, *, security_weakening: str = "", omit_module: str | None = None, stage: bool = True) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "AndroidProducts.mk").write_text(
            "PRODUCT_MAKEFILES := \\\n    $(LOCAL_DIR)/swirphoneos_gsi_arm64.mk\n\n"
            "COMMON_LUNCH_CHOICES := \\\n    swirphoneos_gsi_arm64-aosp_current-userdebug\n",
            encoding="utf-8",
        )
        modules = [module for module in MODULES if module != omit_module]
        package_lines = " \\\n".join(f"    {module}" for module in modules)
        (root / "swirphoneos_gsi_arm64.mk").write_text(
            "$(call inherit-product, $(SRC_TARGET_DIR)/product/aosp_arm64.mk)\n"
            "$(call inherit-product, $(SRC_TARGET_DIR)/product/gsi_release.mk)\n"
            "PRODUCT_NAME := swirphoneos_gsi_arm64\n"
            "PRODUCT_DEVICE := generic_arm64\n"
            "PRODUCT_BRAND := Swir\n"
            "PRODUCT_MANUFACTURER := Swir\n"
            "PRODUCT_MODEL := SwirPhoneOS ARM64 GSI Developer\n"
            "PRODUCT_PACKAGES += \\\n" + package_lines + "\n" + security_weakening,
            encoding="utf-8",
        )
        if stage:
            (root / "stage_manifest.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "files": [{
                        "source": "swirphoneos_gsi_arm64.mk",
                        "destination": "vendor/swir/products/swirphoneos_gsi_arm64.mk",
                    }],
                }),
                encoding="utf-8",
            )

    def test_gsi_contract_rejects_security_weakening_missing_package_and_missing_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "security"
            self._contract_fixture(root, security_weakening="ro.secure=0\n")
            with self.assertRaises(GsiContractError):
                validate_gsi_contract(root)

            root = Path(temp) / "missing-package"
            self._contract_fixture(root, omit_module="SwirRoot")
            with self.assertRaises(GsiContractError):
                validate_gsi_contract(root)

            root = Path(temp) / "missing-stage"
            self._contract_fixture(root, stage=False)
            with self.assertRaises(GsiContractError):
                validate_gsi_contract(root)

    def _fake_build(self, root: Path, *, build_id: str = "CP2A.260605.016", fingerprint_product: str = "swirphoneos_gsi_arm64", image: bytes = b"gsi-system-image") -> tuple[Path, Path]:
        workspace = root / "aosp"
        (workspace / ".repo").mkdir(parents=True)
        (workspace / "build").mkdir()
        (workspace / "build/envsetup.sh").write_text("# synthetic test checkout\n", encoding="utf-8")
        product_out = workspace / "out/target/product/generic_arm64"
        (product_out / "system").mkdir(parents=True)
        (product_out / "system.img").write_bytes(image)
        (product_out / "system/build.prop").write_text(
            f"ro.build.fingerprint=Swir/{fingerprint_product}/generic_arm64:17/{build_id}/synthetic:userdebug/test-keys\n"
            f"ro.build.id={build_id}\n"
            "ro.build.version.release=17\n"
            "ro.build.version.sdk=37\n"
            "ro.build.version.security_patch=2026-06-05\n"
            "ro.build.type=userdebug\n",
            encoding="utf-8",
        )
        manifest = root / "resolved.xml"
        manifest.write_text(
            '<manifest><project name="platform/build" path="build" revision="'
            + "1" * 40
            + '" /><project name="platform/frameworks/base" path="frameworks/base" revision="'
            + "2" * 40
            + '" /></manifest>',
            encoding="utf-8",
        )
        return workspace, manifest

    def test_gsi_build_evidence_hashes_exact_system_image_but_never_claims_compatibility(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, manifest = self._fake_build(root)
            report = collect_gsi_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))
        self.assertEqual(report["expected_product"], "swirphoneos_gsi_arm64")
        self.assertEqual(report["expected_device"], "generic_arm64")
        self.assertEqual(report["architecture"], "arm64")
        self.assertEqual(report["system_image"]["sha256"], hashlib.sha256(b"gsi-system-image").hexdigest())
        self.assertTrue(report["gsi_build_evidence_complete"])
        self.assertFalse(report["treble_vts_verified"])
        self.assertFalse(report["physical_device_compatibility_verified"])
        self.assertFalse(report["install_verified"])
        self.assertFalse(report["rollback_verified"])
        self.assertFalse(report["device_write_allowed"])
        self.assertFalse(report["status_promotion_performed"])
        self.assertFalse(report["release_artifact"])

    def test_gsi_build_evidence_rejects_identity_drift_empty_image_and_floating_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, manifest = self._fake_build(root / "build-id", build_id="WRONG")
            with self.assertRaises(GsiEvidenceError):
                collect_gsi_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))

            workspace, manifest = self._fake_build(root / "fingerprint", fingerprint_product="aosp_arm64")
            with self.assertRaises(GsiEvidenceError):
                collect_gsi_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))

            workspace, manifest = self._fake_build(root / "empty", image=b"")
            with self.assertRaises(GsiEvidenceError):
                collect_gsi_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))

            workspace, manifest = self._fake_build(root / "floating")
            manifest.write_text("<manifest><project name='x' path='x' revision='main'/></manifest>", encoding="utf-8")
            with self.assertRaises(GsiEvidenceError):
                collect_gsi_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))


if __name__ == "__main__":
    unittest.main()
