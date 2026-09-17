from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.device_physical_validation import (
    CAPABILITY_STATES,
    DevicePhysicalValidationError,
    PHYSICAL_TEST_IDS,
    collect_physical_validation_from_files,
    validate_physical_validation_report,
)
from swirphoneos.device_support_readiness import (
    CAPABILITY_NAMES,
    SOURCE as READINESS_SOURCE,
    SUPPORT_GATE_NAMES,
    WARNINGS as READINESS_WARNINGS,
    validate_device_support_readiness,
)

FINGERPRINT = "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys"
TARGET = "Swir/swirphoneos_gsi_arm64/generic_arm64:17/CP2A.260605.016/test:userdebug/test-keys"


def _canonical_sha256(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _readiness() -> dict[str, object]:
    gates = {
        "metadata_profile_valid": True,
        "cross_transport_identity_correlated": True,
        "rollback_artifacts_preverified": True,
        "physical_hardware_verified": False,
        "verified_partition_map": False,
        "stock_restore_verified": False,
        "swirphoneos_boot_verified": False,
        "install_cycle_verified": False,
        "rollback_cycle_verified": False,
        "core_phone_experience_verified": False,
    }
    core: dict[str, object] = {
        "schema_version": 1,
        "source": READINESS_SOURCE,
        "profile_id": "oneplus/avicii",
        "profile_status": "PLANNED_NOT_SUPPORTED",
        "profile_sha256": "c" * 64,
        "device_model": "AC2003",
        "device_codename": "avicii",
        "observed_current_build": FINGERPRINT,
        "target_build": TARGET,
        "hardware_evidence_sha256": "a" * 64,
        "journal_evidence_sha256": "b" * 64,
        "evidence_bindings": {
            "profile_matches_hardware": True,
            "profile_matches_journal": True,
            "codename_matches": True,
            "model_matches_allowlist": True,
            "hardware_matches_journal_current_build": True,
            "target_build_recorded": True,
        },
        "readiness_gates": gates,
        "missing_requirements": sorted(SUPPORT_GATE_NAMES),
        "capability_status": {name: "UNVERIFIED" for name in CAPABILITY_NAMES},
        "support_status": "NOT_SUPPORTED",
        "support_claim_allowed": False,
        "profile_promotion_allowed": False,
        "install_allowed": False,
        "device_write_allowed": False,
        "root_allowed": False,
        "status_promotion_performed": False,
        "warnings": list(READINESS_WARNINGS),
    }
    result = dict(core)
    result["evidence_sha256"] = _canonical_sha256(core)
    validate_device_support_readiness(result)
    return result


def _evidence_entry(root: Path, relative: str, content: str) -> tuple[str, int, str]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = content.encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), len(raw), relative


def _record(root: Path, *, capability_overrides: dict[str, str] | None = None, test_overrides: dict[str, str] | None = None) -> dict[str, object]:
    capability_overrides = capability_overrides or {}
    test_overrides = test_overrides or {}
    readiness = _readiness()
    tests: list[dict[str, object]] = []
    for test_id in PHYSICAL_TEST_IDS:
        digest, size, relative = _evidence_entry(root, f"tests/{test_id}.json", json.dumps({"test": test_id, "ok": True}))
        tests.append({
            "id": test_id,
            "outcome": test_overrides.get(test_id, "PASS"),
            "evidence_path": relative,
            "evidence_sha256": digest,
            "evidence_size": size,
            "evidence_kind": "HYBRID",
            "observed_utc": "2026-09-17T17:00:00Z",
            "notes": f"Reviewed physical gate {test_id}.",
        })
    capabilities: list[dict[str, object]] = []
    for name in CAPABILITY_NAMES:
        status = capability_overrides.get(name, "PASS")
        if status == "NOT_TESTED":
            capabilities.append({
                "name": name,
                "status": status,
                "evidence_path": None,
                "evidence_sha256": None,
                "evidence_size": None,
                "evidence_kind": None,
                "observed_utc": "2026-09-17T17:00:00Z",
                "notes": f"{name} has not yet been tested.",
            })
            continue
        digest, size, relative = _evidence_entry(root, f"capabilities/{name}.json", json.dumps({"capability": name, "status": status}))
        capabilities.append({
            "name": name,
            "status": status,
            "evidence_path": relative,
            "evidence_sha256": digest,
            "evidence_size": size,
            "evidence_kind": "MANUAL_OBSERVATION",
            "observed_utc": "2026-09-17T17:00:00Z",
            "notes": f"Reviewed capability {name}.",
        })
    return {
        "schema_version": 1,
        "source": "owner_physical_validation_record",
        "validation_session_id": "avicii-physical-001",
        "profile_id": "oneplus/avicii",
        "device_model": "AC2003",
        "device_codename": "avicii",
        "observed_current_build": FINGERPRINT,
        "target_build": TARGET,
        "readiness_evidence_sha256": readiness["evidence_sha256"],
        "owner_present": True,
        "external_operator_write_activity_recorded": True,
        "tool_write_authorized": False,
        "tests": tests,
        "capabilities": capabilities,
        "notes": "Owner-observed exact-device validation session; tooling remains non-authorizing.",
    }


def _write_inputs(root: Path, record: dict[str, object]) -> tuple[Path, Path]:
    readiness_path = root / "readiness.json"
    record_path = root / "record.json"
    readiness_path.write_text(json.dumps(_readiness(), indent=2), encoding="utf-8")
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return readiness_path, record_path


def _rehash_report(report: dict[str, object]) -> None:
    core = {key: value for key, value in report.items() if key != "evidence_sha256"}
    report["evidence_sha256"] = _canonical_sha256(core)


class DevicePhysicalValidationTests(unittest.TestCase):
    def test_complete_bundle_becomes_review_candidate_but_never_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root)
            readiness_path, record_path = _write_inputs(root, record)
            report = collect_physical_validation_from_files(
                readiness_path=readiness_path,
                record_path=record_path,
                evidence_root=evidence_root.resolve(),
            )
            self.assertTrue(report["physical_validation_evidence_complete"])
            self.assertTrue(report["support_candidate_review_ready"])
            self.assertEqual(report["missing_requirements"], [])
            self.assertEqual(report["known_capability_failures"], [])
            self.assertEqual(report["support_status"], "NOT_SUPPORTED")
            self.assertFalse(report["support_claim_allowed"])
            self.assertFalse(report["profile_promotion_allowed"])
            self.assertFalse(report["install_allowed"])
            self.assertFalse(report["device_write_allowed"])
            self.assertFalse(report["root_allowed"])
            validate_physical_validation_report(report)

    def test_known_camera_failure_is_truthful_and_does_not_hide_candidate_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root, capability_overrides={"camera": "FAIL"})
            readiness_path, record_path = _write_inputs(root, record)
            report = collect_physical_validation_from_files(
                readiness_path=readiness_path,
                record_path=record_path,
                evidence_root=evidence_root.resolve(),
            )
            self.assertTrue(report["support_candidate_review_ready"])
            self.assertEqual(report["known_capability_failures"], ["camera"])
            self.assertEqual(report["capability_status"]["camera"], "FAIL")
            self.assertFalse(report["support_claim_allowed"])

    def test_untested_capability_blocks_candidate_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root, capability_overrides={"camera": "NOT_TESTED"})
            readiness_path, record_path = _write_inputs(root, record)
            report = collect_physical_validation_from_files(
                readiness_path=readiness_path,
                record_path=record_path,
                evidence_root=evidence_root.resolve(),
            )
            self.assertFalse(report["support_candidate_review_ready"])
            self.assertIn("capability_review:camera", report["missing_requirements"])

    def test_failed_rollback_cycle_blocks_candidate_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root, test_overrides={"rollback_cycle_verified": "FAIL"})
            readiness_path, record_path = _write_inputs(root, record)
            report = collect_physical_validation_from_files(
                readiness_path=readiness_path,
                record_path=record_path,
                evidence_root=evidence_root.resolve(),
            )
            self.assertFalse(report["support_candidate_review_ready"])
            self.assertIn("rollback_cycle_verified", report["missing_requirements"])

    def test_core_audio_failure_blocks_candidate_even_when_reviewed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root, capability_overrides={"audio": "FAIL"})
            readiness_path, record_path = _write_inputs(root, record)
            report = collect_physical_validation_from_files(
                readiness_path=readiness_path,
                record_path=record_path,
                evidence_root=evidence_root.resolve(),
            )
            self.assertFalse(report["support_candidate_review_ready"])
            self.assertIn("core_capability:audio", report["missing_requirements"])
            self.assertIn("audio", report["known_capability_failures"])

    def test_evidence_digest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root)
            record["tests"][0]["evidence_sha256"] = "0" * 64
            readiness_path, record_path = _write_inputs(root, record)
            with self.assertRaises(DevicePhysicalValidationError):
                collect_physical_validation_from_files(
                    readiness_path=readiness_path,
                    record_path=record_path,
                    evidence_root=evidence_root.resolve(),
                )

    def test_target_build_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root)
            record["target_build"] = "Swir/different/build"
            readiness_path, record_path = _write_inputs(root, record)
            with self.assertRaises(DevicePhysicalValidationError):
                collect_physical_validation_from_files(
                    readiness_path=readiness_path,
                    record_path=record_path,
                    evidence_root=evidence_root.resolve(),
                )

    def test_recomputed_hash_cannot_forge_support_or_write_flags(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root)
            readiness_path, record_path = _write_inputs(root, record)
            report = collect_physical_validation_from_files(
                readiness_path=readiness_path,
                record_path=record_path,
                evidence_root=evidence_root.resolve(),
            )
            for key in ("support_claim_allowed", "profile_promotion_allowed", "device_write_allowed", "root_allowed"):
                tampered = copy.deepcopy(report)
                tampered[key] = True
                _rehash_report(tampered)
                with self.assertRaises(DevicePhysicalValidationError, msg=key):
                    validate_physical_validation_report(tampered)

    def test_recomputed_hash_cannot_forge_candidate_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            record = _record(evidence_root, test_overrides={"stock_restore_verified": "FAIL"})
            readiness_path, record_path = _write_inputs(root, record)
            report = collect_physical_validation_from_files(
                readiness_path=readiness_path,
                record_path=record_path,
                evidence_root=evidence_root.resolve(),
            )
            tampered = copy.deepcopy(report)
            tampered["support_candidate_review_ready"] = True
            _rehash_report(tampered)
            with self.assertRaises(DevicePhysicalValidationError):
                validate_physical_validation_report(tampered)

    def test_capability_state_vocabulary_is_bounded(self):
        self.assertEqual(CAPABILITY_STATES, {"PASS", "FAIL", "NOT_APPLICABLE", "NOT_TESTED"})


if __name__ == "__main__":
    unittest.main()
