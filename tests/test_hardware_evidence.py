from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.diagnostics import summarize
from swirphoneos.fastboot import summarize_fastboot
from swirphoneos.hardware_evidence import (
    HardwareEvidenceError,
    assess_transaction_hardware,
    create_hardware_evidence,
    load_hardware_evidence,
    validate_hardware_evidence,
)
from swirphoneos.identity import build_unified_report
from swirphoneos.profiles import validate_profile
from swirphoneos.transaction_evidence import validate_plan


FINGERPRINT = "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys"
SERIAL_DIGEST = hashlib.sha256(b"ABC123").hexdigest()
ADB_TOOL_DIGEST = "a" * 64
FASTBOOT_TOOL_DIGEST = "b" * 64


def profile():
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


def reports():
    current_profile = profile()
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
    }, transport_serial_sha256=SERIAL_DIGEST, tool_sha256=ADB_TOOL_DIGEST)
    fastboot = summarize_fastboot({
        "product": "avicii",
        "current-slot": "a",
        "slot-count": "2",
        "unlocked": "yes",
        "is-userspace": "no",
        "secure": "yes",
        "has-slot:boot": "yes",
        "partition-size:boot": "0x06000000",
        "has-slot:super": "no",
        "partition-size:super": "0x1c0000000",
    }, transport_serial_sha256=SERIAL_DIGEST, tool_sha256=FASTBOOT_TOOL_DIGEST)
    return (
        build_unified_report("adb", adb, [current_profile]),
        build_unified_report("fastboot", fastboot, [current_profile]),
        current_profile,
    )


def transaction_plan():
    digest = "0" * 64
    return validate_plan({
        "schema_version": 1,
        "transaction_id": "avicii-test-001",
        "profile_id": "oneplus/avicii",
        "device_codename": "avicii",
        "device_model": "AC2003",
        "expected_current_build": FINGERPRINT,
        "target_build": "SwirPhoneOS/test/target:userdebug",
        "write_enabled": False,
        "owner_confirmation_required": True,
        "rollback_required": True,
        "install_artifacts": [{"name": "boot", "path": "target/boot.img", "sha256": digest, "size": 1, "kind": "install"}],
        "rollback_artifacts": [{"name": "stock_boot", "path": "rollback/boot.img", "sha256": digest, "size": 1, "kind": "rollback"}],
        "notes": "read-only plan fixture",
    })


class HardwareEvidenceTests(unittest.TestCase):
    def test_correlates_matching_reports_without_authorizing_writes(self):
        adb, fastboot, current_profile = reports()
        evidence = create_hardware_evidence(adb, fastboot, [current_profile])
        self.assertEqual(evidence["schema_version"], 2)
        self.assertEqual(evidence["profile_id"], "oneplus/avicii")
        self.assertEqual(evidence["adb_build_fingerprint_reported"], FINGERPRINT)
        self.assertEqual(evidence["transport_serial_sha256"], SERIAL_DIGEST)
        self.assertEqual(evidence["adb_tool_sha256"], ADB_TOOL_DIGEST)
        self.assertEqual(evidence["fastboot_tool_sha256"], FASTBOOT_TOOL_DIGEST)
        self.assertIn("transport_serial_sha256_matches_across_transports", evidence["correlations"])
        self.assertEqual(evidence["state"], "CORRELATED_READ_ONLY_NOT_VERIFIED")
        self.assertFalse(evidence["hardware_verified"])
        self.assertFalse(evidence["write_allowed"])
        self.assertFalse(evidence["flash_allowed"])
        self.assertFalse(evidence["root_allowed"])
        self.assertEqual(evidence["partition_hints_reported"][0]["name"], "boot")
        self.assertEqual(evidence["partition_hints_reported"][0]["size_bytes_reported"], 0x06000000)
        validate_hardware_evidence(evidence)

    def test_rejects_cross_transport_serial_digest_mismatch(self):
        adb, fastboot, current_profile = reports()
        fastboot["transport_report"]["transport_serial_sha256"] = hashlib.sha256(b"OTHER").hexdigest()
        with self.assertRaises(HardwareEvidenceError):
            create_hardware_evidence(adb, fastboot, [current_profile])

    def test_rejects_missing_transport_provenance(self):
        adb, fastboot, current_profile = reports()
        adb["transport_report"]["transport_serial_sha256"] = None
        with self.assertRaises(HardwareEvidenceError):
            create_hardware_evidence(adb, fastboot, [current_profile])

    def test_rejects_invalid_tool_digest(self):
        adb, fastboot, current_profile = reports()
        fastboot["transport_report"]["tool_sha256"] = "bad"
        with self.assertRaises(HardwareEvidenceError):
            create_hardware_evidence(adb, fastboot, [current_profile])

    def test_rejects_cross_transport_slot_mismatch(self):
        adb, fastboot, current_profile = reports()
        fastboot["transport_report"]["current_slot_reported"] = "b"
        with self.assertRaises(HardwareEvidenceError):
            create_hardware_evidence(adb, fastboot, [current_profile])

    def test_rejects_missing_exact_firmware_fingerprint(self):
        adb, fastboot, current_profile = reports()
        adb["transport_report"]["build_fingerprint_reported"] = None
        with self.assertRaises(HardwareEvidenceError):
            create_hardware_evidence(adb, fastboot, [current_profile])

    def test_integrity_hash_detects_tampering(self):
        adb, fastboot, current_profile = reports()
        evidence = create_hardware_evidence(adb, fastboot, [current_profile])
        tampered = copy.deepcopy(evidence)
        tampered["adb_model_reported"] = "OTHER"
        with self.assertRaises(HardwareEvidenceError):
            validate_hardware_evidence(tampered)

    def test_integrity_hash_detects_tool_digest_tampering(self):
        adb, fastboot, current_profile = reports()
        evidence = create_hardware_evidence(adb, fastboot, [current_profile])
        tampered = copy.deepcopy(evidence)
        tampered["adb_tool_sha256"] = "c" * 64
        with self.assertRaises(HardwareEvidenceError):
            validate_hardware_evidence(tampered)

    def test_persisted_evidence_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "hardware.json"
            path.write_text('{"schema_version":2,"schema_version":2}', encoding="utf-8")
            with self.assertRaises(HardwareEvidenceError):
                load_hardware_evidence(path)

    def test_transaction_binding_matches_but_never_enables_write(self):
        adb, fastboot, current_profile = reports()
        evidence = create_hardware_evidence(adb, fastboot, [current_profile])
        result = assess_transaction_hardware(transaction_plan(), evidence)
        self.assertTrue(result["preconditions_match"])
        self.assertEqual(result["state"], "PREPARATION_MATCH_ONLY")
        self.assertFalse(result["hardware_verified"])
        self.assertFalse(result["write_allowed"])
        self.assertFalse(result["flash_allowed"])
        self.assertFalse(result["root_allowed"])

    def test_transaction_fingerprint_mismatch_is_fail_closed(self):
        adb, fastboot, current_profile = reports()
        evidence = create_hardware_evidence(adb, fastboot, [current_profile])
        plan = transaction_plan()
        object.__setattr__(plan, "expected_current_build", "different/build")
        result = assess_transaction_hardware(plan, evidence)
        self.assertFalse(result["preconditions_match"])
        self.assertEqual(result["state"], "PREPARATION_MISMATCH")
        self.assertFalse(result["write_allowed"])


if __name__ == "__main__":
    unittest.main()
