from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.device_support_readiness import (
    CAPABILITY_NAMES,
    DeviceSupportReadinessError,
    collect_device_support_readiness,
    collect_device_support_readiness_from_files,
    validate_device_support_readiness,
)
from swirphoneos.diagnostics import summarize
from swirphoneos.fastboot import summarize_fastboot
from swirphoneos.hardware_evidence import create_hardware_evidence
from swirphoneos.identity import build_unified_report
from swirphoneos.profiles import validate_profile

FINGERPRINT = "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys"
TARGET = "Swir/swirphoneos_gsi_arm64/generic_arm64:17/CP2A.260605.016/test:userdebug/test-keys"
SERIAL_DIGEST = hashlib.sha256(b"ABC123").hexdigest()


def _profile_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "oneplus/avicii",
        "display_name": "OnePlus Nord AC2003",
        "codename": "avicii",
        "model_allowlist": ["AC2003"],
        "status": "PLANNED_NOT_SUPPORTED",
        "flash_enabled": False,
        "firmware_baseline": None,
        "verified_partition_map": None,
        "validated_builds": [],
        "flash_operations": [],
        "recovery_evidence": [],
        "notes": "test metadata",
        "sources": ["https://example.invalid/avicii"],
    }


def _profile():
    return validate_profile(_profile_data())


def _hardware():
    profile = _profile()
    adb = summarize({
        "ro.product.manufacturer": "OnePlus",
        "ro.product.model": "AC2003",
        "ro.product.device": "avicii",
        "ro.build.fingerprint": FINGERPRINT,
        "ro.boot.slot": "a",
        "ro.boot.slot_suffix": "_a",
        "ro.boot.flash.locked": "0",
        "ro.boot.verifiedbootstate": "orange",
        "ro.boot.vbmeta.device_state": "unlocked",
    }, transport_serial_sha256=SERIAL_DIGEST, tool_sha256="a" * 64)
    fastboot = summarize_fastboot({
        "product": "avicii",
        "current-slot": "a",
        "slot-count": "2",
        "unlocked": "yes",
        "is-userspace": "no",
        "secure": "yes",
    }, transport_serial_sha256=SERIAL_DIGEST, tool_sha256="b" * 64)
    return create_hardware_evidence(
        build_unified_report("adb", adb, [profile]),
        build_unified_report("fastboot", fastboot, [profile]),
        [profile],
    )


def _journal():
    item_install = {
        "name": "boot",
        "path": "target/boot.img",
        "kind": "install",
        "size": 1,
        "sha256": "1" * 64,
        "verified": True,
    }
    item_rollback = {
        "name": "stock_boot",
        "path": "rollback/boot.img",
        "kind": "rollback",
        "size": 1,
        "sha256": "2" * 64,
        "verified": True,
    }
    core = {
        "schema_version": 1,
        "transaction_id": "avicii-support-readiness-001",
        "profile_id": "oneplus/avicii",
        "device_codename": "avicii",
        "device_model": "AC2003",
        "expected_current_build": FINGERPRINT,
        "target_build": TARGET,
        "plan_sha256": "3" * 64,
        "state": "ARTIFACTS_VERIFIED_READ_ONLY",
        "rollback_ready": True,
        "owner_confirmation_recorded": False,
        "write_allowed": False,
        "install_artifacts": [item_install],
        "rollback_artifacts": [item_rollback],
    }
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return {**core, "evidence_sha256": digest, "created_utc": "2026-09-17T16:00:00Z"}


def _rehash_journal(journal: dict[str, object]) -> dict[str, object]:
    core = {key: value for key, value in journal.items() if key not in {"evidence_sha256", "created_utc"}}
    journal["evidence_sha256"] = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return journal


def _rehash_readiness(report: dict[str, object]) -> dict[str, object]:
    core = {key: value for key, value in report.items() if key != "evidence_sha256"}
    report["evidence_sha256"] = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return report


class DeviceSupportReadinessTests(unittest.TestCase):
    def test_projection_binds_preparation_evidence_but_denies_support(self):
        result = collect_device_support_readiness(
            profile=_profile(),
            profile_sha256="c" * 64,
            journal=_journal(),
            hardware=_hardware(),
        )
        self.assertEqual(result["profile_id"], "oneplus/avicii")
        self.assertEqual(result["support_status"], "NOT_SUPPORTED")
        self.assertTrue(result["readiness_gates"]["metadata_profile_valid"])
        self.assertTrue(result["readiness_gates"]["cross_transport_identity_correlated"])
        self.assertTrue(result["readiness_gates"]["rollback_artifacts_preverified"])
        self.assertFalse(result["readiness_gates"]["physical_hardware_verified"])
        self.assertIn("verified_partition_map", result["missing_requirements"])
        self.assertIn("stock_restore_verified", result["missing_requirements"])
        self.assertIn("swirphoneos_boot_verified", result["missing_requirements"])
        self.assertIn("install_cycle_verified", result["missing_requirements"])
        self.assertIn("rollback_cycle_verified", result["missing_requirements"])
        self.assertIn("core_phone_experience_verified", result["missing_requirements"])
        self.assertFalse(result["support_claim_allowed"])
        self.assertFalse(result["profile_promotion_allowed"])
        self.assertFalse(result["install_allowed"])
        self.assertFalse(result["device_write_allowed"])
        self.assertFalse(result["root_allowed"])
        self.assertEqual(result["capability_status"], {name: "UNVERIFIED" for name in CAPABILITY_NAMES})
        validate_device_support_readiness(result)

    def test_rejects_profile_identity_mismatch(self):
        data = _profile_data()
        data["id"] = "oneplus/other"
        with self.assertRaises(DeviceSupportReadinessError):
            collect_device_support_readiness(
                profile=validate_profile(data),
                profile_sha256="c" * 64,
                journal=_journal(),
                hardware=_hardware(),
            )

    def test_rejects_journal_model_mismatch_even_with_valid_integrity(self):
        journal = _journal()
        journal["device_model"] = "AC2001"
        _rehash_journal(journal)
        with self.assertRaises(DeviceSupportReadinessError):
            collect_device_support_readiness(
                profile=_profile(),
                profile_sha256="c" * 64,
                journal=journal,
                hardware=_hardware(),
            )

    def test_rejects_current_build_mismatch_even_with_valid_integrity(self):
        journal = _journal()
        journal["expected_current_build"] = "OnePlus/different/build"
        _rehash_journal(journal)
        with self.assertRaises(DeviceSupportReadinessError):
            collect_device_support_readiness(
                profile=_profile(),
                profile_sha256="c" * 64,
                journal=journal,
                hardware=_hardware(),
            )

    def test_support_claim_cannot_be_forged_with_recomputed_hash(self):
        result = collect_device_support_readiness(
            profile=_profile(), profile_sha256="c" * 64, journal=_journal(), hardware=_hardware()
        )
        tampered = copy.deepcopy(result)
        tampered["support_claim_allowed"] = True
        _rehash_readiness(tampered)
        with self.assertRaises(DeviceSupportReadinessError):
            validate_device_support_readiness(tampered)

    def test_verified_gate_cannot_be_forged_with_recomputed_hash(self):
        result = collect_device_support_readiness(
            profile=_profile(), profile_sha256="c" * 64, journal=_journal(), hardware=_hardware()
        )
        tampered = copy.deepcopy(result)
        tampered["readiness_gates"]["physical_hardware_verified"] = True
        tampered["missing_requirements"].remove("physical_hardware_verified")
        _rehash_readiness(tampered)
        with self.assertRaises(DeviceSupportReadinessError):
            validate_device_support_readiness(tampered)

    def test_capability_cannot_be_forged_with_recomputed_hash(self):
        result = collect_device_support_readiness(
            profile=_profile(), profile_sha256="c" * 64, journal=_journal(), hardware=_hardware()
        )
        tampered = copy.deepcopy(result)
        tampered["capability_status"]["telephony"] = "VERIFIED"
        _rehash_readiness(tampered)
        with self.assertRaises(DeviceSupportReadinessError):
            validate_device_support_readiness(tampered)

    def test_file_collector_binds_exact_profile_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile_path = root / "profile.json"
            hardware_path = root / "hardware.json"
            journal_path = root / "journal.json"
            profile_raw = (json.dumps(_profile_data(), sort_keys=True) + "\n").encode()
            profile_path.write_bytes(profile_raw)
            hardware_path.write_text(json.dumps(_hardware()), encoding="utf-8")
            journal_path.write_text(json.dumps(_journal()), encoding="utf-8")

            result = collect_device_support_readiness_from_files(
                profile_path=profile_path,
                journal_path=journal_path,
                hardware_path=hardware_path,
            )
            self.assertEqual(result["profile_sha256"], hashlib.sha256(profile_raw).hexdigest())
            self.assertEqual(result["hardware_evidence_sha256"], _hardware()["evidence_sha256"])
            self.assertEqual(result["journal_evidence_sha256"], _journal()["evidence_sha256"])


if __name__ == "__main__":
    unittest.main()
