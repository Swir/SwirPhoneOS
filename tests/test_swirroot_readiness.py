from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.diagnostics import summarize
from swirphoneos.fastboot import summarize_fastboot
from swirphoneos.hardware_evidence import create_hardware_evidence
from swirphoneos.identity import build_unified_report
from swirphoneos.profiles import validate_profile
from swirphoneos.rollback_material_evidence import (
    RollbackMaterialEvidenceError,
    collect_rollback_material_evidence,
)
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
ROLLBACK_BYTES = b"known-stock-boot-image"


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
        "size": len(ROLLBACK_BYTES),
        "sha256": hashlib.sha256(ROLLBACK_BYTES).hexdigest(),
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


def _rollback_evidence(journal: dict[str, object], root: Path):
    rollback = root / "rollback"
    rollback.mkdir(parents=True)
    (rollback / "boot.img").write_bytes(ROLLBACK_BYTES)
    return collect_rollback_material_evidence(journal, root)


class SwirRootReadinessTests(unittest.TestCase):
    def _ready(self, action: str = "enable") -> dict[str, object]:
        journal = _journal()
        with tempfile.TemporaryDirectory() as temporary:
            rollback = _rollback_evidence(journal, Path(temporary))
            return collect_swirroot_readiness(
                action=action,
                exact_build=TARGET,
                policy=load_policy(POLICY),
                journal=journal,
                hardware=_hardware(),
                rollback_material=rollback,
            )

    def test_enable_projection_binds_fresh_rollback_but_stays_blocked(self):
        result = self._ready("enable")
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["profile_id"], "oneplus/avicii")
        self.assertTrue(result["policy_gates"]["exact_build_match"])
        self.assertTrue(result["policy_gates"]["rollback_material_verified"])
        self.assertTrue(result["evidence_bindings"]["rollback_material_rechecked"])
        self.assertTrue(result["policy_gates"]["journal_available"])
        self.assertIn("verified_device_profile", result["missing_requirements"])
        self.assertIn("owner_confirmation", result["missing_requirements"])
        self.assertIn("update_state_safe", result["missing_requirements"])
        self.assertIn("expected_nonroot_state_known", result["missing_requirements"])
        self.assertFalse(result["policy_backend_available"])
        self.assertFalse(result["hardware_root_authorized"])
        self.assertFalse(result["transition_ready"])
        self.assertFalse(result["device_write_allowed"])
        self.assertFalse(result["root_operation_executed"])
        validate_swirroot_readiness(result)

    def test_missing_fresh_rollback_recheck_fails_the_policy_gate(self):
        result = collect_swirroot_readiness(
            action="enable",
            exact_build=TARGET,
            policy=load_policy(POLICY),
            journal=_journal(),
            hardware=_hardware(),
        )
        self.assertFalse(result["policy_gates"]["rollback_material_verified"])
        self.assertFalse(result["evidence_bindings"]["rollback_material_rechecked"])
        self.assertIn("rollback_material_verified", result["missing_requirements"])
        self.assertFalse(result["transition_ready"])

    def test_stale_or_modified_rollback_file_is_rejected(self):
        journal = _journal()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rollback = root / "rollback"
            rollback.mkdir(parents=True)
            path = rollback / "boot.img"
            path.write_bytes(ROLLBACK_BYTES)
            collect_rollback_material_evidence(journal, root)
            path.write_bytes(b"changed-after-journal")
            with self.assertRaises(RollbackMaterialEvidenceError):
                collect_rollback_material_evidence(journal, root)

    def test_unroot_projection_uses_same_recovery_safe_gate_set(self):
        result = self._ready("unroot")
        self.assertIn("verified_device_profile", result["missing_requirements"])
        self.assertIn("owner_confirmation", result["missing_requirements"])
        self.assertIn("update_state_safe", result["missing_requirements"])
        self.assertIn("expected_nonroot_state_known", result["missing_requirements"])
        self.assertNotIn("rollback_material_verified", result["missing_requirements"])
        self.assertFalse(result["transition_ready"])

    def test_enable_and_unroot_project_identical_missing_gate_names(self):
        enable = self._ready("enable")
        unroot = self._ready("unroot")
        self.assertEqual(enable["missing_requirements"], unroot["missing_requirements"])

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
        result = self._ready("enable")
        tampered = copy.deepcopy(result)
        tampered["policy_gates"]["owner_confirmation"] = True
        with self.assertRaises(SwirRootReadinessError):
            validate_swirroot_readiness(tampered)

    def test_forged_rollback_binding_is_rejected_even_after_rehash(self):
        result = self._ready("enable")
        tampered = copy.deepcopy(result)
        tampered["evidence_bindings"]["rollback_material_rechecked"] = False
        core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
        tampered["evidence_sha256"] = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        with self.assertRaises(SwirRootReadinessError):
            validate_swirroot_readiness(tampered)

    def test_transition_ready_cannot_be_forged(self):
        result = self._ready("enable")
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
