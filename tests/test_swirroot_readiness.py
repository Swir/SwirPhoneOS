from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from swirphoneos.diagnostics import summarize
from swirphoneos.fastboot import summarize_fastboot
from swirphoneos.hardware_evidence import create_hardware_evidence
from swirphoneos.identity import build_unified_report
from swirphoneos.profiles import validate_profile
from swirphoneos.swirroot import load_policy
from swirphoneos.swirroot_readiness import (
    SwirRootReadinessError,
    collect_swirroot_readiness,
    validate_swirroot_readiness,
)

POLICY = Path("swirroot/policy.json")
FINGERPRINT = "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys"
TARGET = "Swir/swirphoneos_gsi_arm64/generic_arm64:17/CP2A.260605.016/test:userdebug/test-keys"
SERIAL_DIGEST = hashlib.sha256(b"ABC123").hexdigest()


def _profile():
    return validate_profile({
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
    })


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
        "transaction_id": "avicii-root-readiness-001",
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
    return {**core, "evidence_sha256": digest, "created_utc": "2026-09-17T12:00:00Z"}


class SwirRootReadinessTests(unittest.TestCase):
    def test_enable_projection_binds_evidence_but_stays_blocked(self):
        result = collect_swirroot_readiness(
            action="enable",
            exact_build=TARGET,
            policy=load_policy(POLICY),
            journal=_journal(),
            hardware=_hardware(),
        )
        self.assertEqual(result["profile_id"], "oneplus/avicii")
        self.assertTrue(result["policy_gates"]["exact_build_match"])
        self.assertTrue(result["policy_gates"]["rollback_material_verified"])
        self.assertTrue(result["policy_gates"]["journal_available"])
        self.assertIn("verified_device_profile", result["missing_requirements"])
        self.assertIn("owner_confirmation", result["missing_requirements"])
        self.assertIn("update_state_safe", result["missing_requirements"])
        self.assertFalse(result["policy_backend_available"])
        self.assertFalse(result["hardware_root_authorized"])
        self.assertFalse(result["transition_ready"])
        self.assertFalse(result["device_write_allowed"])
        self.assertFalse(result["root_operation_executed"])
        validate_swirroot_readiness(result)

    def test_unroot_projection_requires_expected_nonroot_state(self):
        result = collect_swirroot_readiness(
            action="unroot",
            exact_build=TARGET,
            policy=load_policy(POLICY),
            journal=_journal(),
            hardware=_hardware(),
        )
        self.assertIn("owner_confirmation", result["missing_requirements"])
        self.assertIn("expected_nonroot_state_known", result["missing_requirements"])
        self.assertNotIn("update_state_safe", result["missing_requirements"])
        self.assertFalse(result["transition_ready"])

    def test_rejects_hardware_and_journal_build_mismatch(self):
        journal = _journal()
        journal["expected_current_build"] = "different/build"
        core = {key: value for key, value in journal.items() if key not in {"evidence_sha256", "created_utc"}}
        journal["evidence_sha256"] = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        with self.assertRaises(SwirRootReadinessError):
            collect_swirroot_readiness(
                action="enable",
                exact_build=TARGET,
                policy=load_policy(POLICY),
                journal=journal,
                hardware=_hardware(),
            )

    def test_rejects_wrong_target_build(self):
        with self.assertRaises(SwirRootReadinessError):
            collect_swirroot_readiness(
                action="enable",
                exact_build="Swir/other/build",
                policy=load_policy(POLICY),
                journal=_journal(),
                hardware=_hardware(),
            )

    def test_integrity_hash_detects_tampering(self):
        result = collect_swirroot_readiness(
            action="enable",
            exact_build=TARGET,
            policy=load_policy(POLICY),
            journal=_journal(),
            hardware=_hardware(),
        )
        tampered = copy.deepcopy(result)
        tampered["policy_gates"]["owner_confirmation"] = True
        with self.assertRaises(SwirRootReadinessError):
            validate_swirroot_readiness(tampered)

    def test_transition_ready_cannot_be_forged(self):
        result = collect_swirroot_readiness(
            action="enable",
            exact_build=TARGET,
            policy=load_policy(POLICY),
            journal=_journal(),
            hardware=_hardware(),
        )
        tampered = copy.deepcopy(result)
        tampered["transition_ready"] = True
        core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
        tampered["evidence_sha256"] = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        with self.assertRaises(SwirRootReadinessError):
            validate_swirroot_readiness(tampered)


if __name__ == "__main__":
    unittest.main()
