from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.device_support_readiness import collect_device_support_readiness
from swirphoneos.diagnostics import summarize
from swirphoneos.fastboot import summarize_fastboot
from swirphoneos.hardware_evidence import create_hardware_evidence
from swirphoneos.identity import build_unified_report
from swirphoneos.profiles import validate_profile
from swirphoneos.studio_evidence import (
    StudioEvidenceError,
    load_device_support_readiness,
    load_public_device_support_readiness_summary,
    load_public_swirroot_readiness_summary,
    load_swirroot_readiness,
    public_device_support_readiness_summary,
    public_swirroot_readiness_summary,
)
from swirphoneos.swirroot import load_policy
from swirphoneos.swirroot_readiness import collect_swirroot_readiness

POLICY = Path("swirroot/policy.json")
FINGERPRINT = "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys"
TARGET = "Swir/swirphoneos_gsi_arm64/generic_arm64:17/CP2A.260605.016/test:userdebug/test-keys"
SERIAL_DIGEST = hashlib.sha256(b"ABC123").hexdigest()
PROFILE_DIGEST = hashlib.sha256(b"test-profile-snapshot").hexdigest()


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
        "install_artifacts": [{
            "name": "boot", "path": "target/boot.img", "kind": "install",
            "size": 1, "sha256": "1" * 64, "verified": True,
        }],
        "rollback_artifacts": [{
            "name": "stock_boot", "path": "rollback/boot.img", "kind": "rollback",
            "size": 1, "sha256": "2" * 64, "verified": True,
        }],
    }
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return {**core, "evidence_sha256": digest, "created_utc": "2026-09-17T12:00:00Z"}


def _report():
    return collect_swirroot_readiness(
        action="enable",
        exact_build=TARGET,
        policy=load_policy(POLICY),
        journal=_journal(),
        hardware=_hardware(),
    )


def _support_report():
    return collect_device_support_readiness(
        profile=_profile(),
        profile_sha256=PROFILE_DIGEST,
        journal=_journal(),
        hardware=_hardware(),
    )


class StudioEvidenceTests(unittest.TestCase):
    def test_summary_is_bounded_and_non_authorizing(self):
        summary = public_swirroot_readiness_summary(_report())
        self.assertEqual(summary["source"], "swirphoneos_studio_swirroot_readiness_summary")
        self.assertEqual(summary["profile_id"], "oneplus/avicii")
        self.assertIn("verified_device_profile", summary["missing_requirements"])
        self.assertFalse(summary["hardware_root_authorized"])
        self.assertFalse(summary["transition_ready"])
        self.assertFalse(summary["device_write_allowed"])
        self.assertNotIn("hardware_evidence_sha256", summary)
        self.assertNotIn("journal_evidence_sha256", summary)

    def test_absolute_json_roundtrip(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "readiness.json"
            path.write_text(json.dumps(_report()), encoding="utf-8")
            loaded = load_swirroot_readiness(path)
            self.assertEqual(loaded["evidence_sha256"], _report()["evidence_sha256"])
            summary = load_public_swirroot_readiness_summary(path)
            self.assertFalse(summary["device_write_allowed"])

    def test_relative_path_rejected(self):
        with self.assertRaises(StudioEvidenceError):
            load_swirroot_readiness(Path("readiness.json"))

    def test_non_json_extension_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "readiness.txt"
            path.write_text(json.dumps(_report()), encoding="utf-8")
            with self.assertRaises(StudioEvidenceError):
                load_swirroot_readiness(path)

    def test_duplicate_key_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "readiness.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(StudioEvidenceError):
                load_swirroot_readiness(path)

    def test_symlink_rejected(self):
        with TemporaryDirectory() as folder:
            target = Path(folder).resolve() / "target.json"
            target.write_text(json.dumps(_report()), encoding="utf-8")
            link = Path(folder).resolve() / "readiness.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Host does not permit creating symlinks.")
            with self.assertRaises(StudioEvidenceError):
                load_swirroot_readiness(link)

    def test_oversized_file_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "readiness.json"
            path.write_bytes(b" " * 262_145)
            with self.assertRaises(StudioEvidenceError):
                load_swirroot_readiness(path)

    def test_tampered_integrity_rejected(self):
        tampered = copy.deepcopy(_report())
        tampered["missing_requirements"] = []
        with self.assertRaises(StudioEvidenceError):
            public_swirroot_readiness_summary(tampered)

    def test_forged_write_authorization_rejected(self):
        tampered = copy.deepcopy(_report())
        tampered["device_write_allowed"] = True
        core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
        tampered["evidence_sha256"] = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        with self.assertRaises(StudioEvidenceError):
            public_swirroot_readiness_summary(tampered)


class StudioDeviceSupportEvidenceTests(unittest.TestCase):
    def test_support_summary_is_bounded_and_non_authorizing(self):
        summary = public_device_support_readiness_summary(_support_report())
        self.assertEqual(summary["source"], "swirphoneos_studio_device_support_readiness_summary")
        self.assertEqual(summary["profile_id"], "oneplus/avicii")
        self.assertEqual(summary["support_status"], "NOT_SUPPORTED")
        self.assertIn("verified_partition_map", summary["missing_requirements"])
        self.assertEqual(summary["capability_status"]["telephony"], "UNVERIFIED")
        self.assertFalse(summary["support_claim_allowed"])
        self.assertFalse(summary["profile_promotion_allowed"])
        self.assertFalse(summary["install_allowed"])
        self.assertFalse(summary["device_write_allowed"])
        self.assertFalse(summary["root_allowed"])
        self.assertNotIn("hardware_evidence_sha256", summary)
        self.assertNotIn("journal_evidence_sha256", summary)

    def test_support_absolute_json_roundtrip(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "support-readiness.json"
            path.write_text(json.dumps(_support_report()), encoding="utf-8")
            loaded = load_device_support_readiness(path)
            self.assertEqual(loaded["evidence_sha256"], _support_report()["evidence_sha256"])
            summary = load_public_device_support_readiness_summary(path)
            self.assertEqual(summary["support_status"], "NOT_SUPPORTED")
            self.assertFalse(summary["install_allowed"])

    def test_support_relative_path_rejected(self):
        with self.assertRaises(StudioEvidenceError):
            load_device_support_readiness(Path("support-readiness.json"))

    def test_support_duplicate_key_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "support-readiness.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(StudioEvidenceError):
                load_device_support_readiness(path)

    def test_support_symlink_rejected(self):
        with TemporaryDirectory() as folder:
            target = Path(folder).resolve() / "target.json"
            target.write_text(json.dumps(_support_report()), encoding="utf-8")
            link = Path(folder).resolve() / "support-readiness.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Host does not permit creating symlinks.")
            with self.assertRaises(StudioEvidenceError):
                load_device_support_readiness(link)

    def test_support_forged_install_authorization_rejected_after_rehash(self):
        tampered = copy.deepcopy(_support_report())
        tampered["install_allowed"] = True
        core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
        tampered["evidence_sha256"] = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        with self.assertRaises(StudioEvidenceError):
            public_device_support_readiness_summary(tampered)

    def test_support_forged_verified_capability_rejected_after_rehash(self):
        tampered = copy.deepcopy(_support_report())
        tampered["capability_status"]["camera"] = "VERIFIED"
        core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
        tampered["evidence_sha256"] = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        with self.assertRaises(StudioEvidenceError):
            public_device_support_readiness_summary(tampered)


if __name__ == "__main__":
    unittest.main()
