from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_admission_continuity import (
    AospAdmissionContinuityError,
    collect_admission_continuity,
    validate_admission_continuity,
)
from swirphoneos.aosp_admission_gate import validate_admission


class AospAdmissionContinuityTests(unittest.TestCase):
    SOURCE_COMMIT = "1" * 40
    REPOSITORY = "Swir/SwirPhoneOS"

    @staticmethod
    def _canonical_sha(value: object) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _run_report(self, *, runtime: bool) -> dict[str, object]:
        report: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "source_commit": self.SOURCE_COMMIT,
            "scope": "BUILD_AND_RUNTIME" if runtime else "BUILD_ONLY",
            "expected_product": "swirphoneos_cf_x86_64",
            "build_chain_complete": True,
            "runtime_chain_complete": runtime,
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
        }
        report["run_evidence_sha256"] = self._canonical_sha(report)
        report["run_evidence_complete"] = True
        return report

    def _write_chain(self, root: Path, *, runtime: bool) -> dict[str, Path]:
        preflight = {
            "schema_version": 1,
            "operation": "READ_ONLY_HOST_PREFLIGHT",
            "ready_for_full_build": True,
            "cuttlefish_kvm_available": runtime,
            "workspace": {"cleanup_performed": False},
            "checks": [{"id": "workspace", "passed": True}],
        }
        preflight_path = root / "builder-admission.json"
        preflight_path.write_text(json.dumps(preflight, sort_keys=True), encoding="utf-8")
        preflight_sha = hashlib.sha256(preflight_path.read_bytes()).hexdigest()

        attestation = {
            "schema_version": 1,
            "operation": "AOSP_BUILDER_ADMISSION_ATTESTATION",
            "admitted": True,
            "read_only": True,
            "source_commit": self.SOURCE_COMMIT,
            "repository": self.REPOSITORY,
            "workflow_run_id": 123,
            "requested_jobs": 16,
            "require_kvm": runtime,
            "preflight_sha256": preflight_sha,
            "preflight_operation": "READ_ONLY_HOST_PREFLIGHT",
            "ready_for_full_build": True,
            "cuttlefish_kvm_available": runtime,
            "workspace_cleanup_performed": False,
        }
        attestation_path = root / "builder-admission-envelope.json"
        attestation_path.write_text(json.dumps(attestation, sort_keys=True), encoding="utf-8")

        gate = validate_admission(
            preflight_path=preflight_path,
            attestation_path=attestation_path,
            source_commit=self.SOURCE_COMMIT,
            repository=self.REPOSITORY,
            admission_run_id=123,
            requested_jobs=16,
            require_kvm=runtime,
        )
        gate_path = root / "builder-admission-build-gate.json"
        gate_path.write_text(json.dumps(gate, sort_keys=True), encoding="utf-8")

        run_path = root / "aosp-run-evidence.json"
        run_path.write_text(json.dumps(self._run_report(runtime=runtime), sort_keys=True), encoding="utf-8")
        return {
            "run": run_path,
            "gate": gate_path,
            "preflight": preflight_path,
            "attestation": attestation_path,
        }

    def _collect(self, paths: dict[str, Path]) -> dict[str, object]:
        return collect_admission_continuity(
            run_evidence_path=paths["run"],
            gate_path=paths["gate"],
            preflight_path=paths["preflight"],
            attestation_path=paths["attestation"],
            repository=self.REPOSITORY,
            expected_source_commit=self.SOURCE_COMMIT,
        )

    def test_accepts_exact_build_only_admission_chain(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._collect(self._write_chain(Path(temporary), runtime=False))
            self.assertTrue(result["admission_chain_verified"])
            self.assertTrue(result["exact_run_bytes_bound"])
            self.assertEqual(result["aosp_run_scope"], "BUILD_ONLY")
            self.assertFalse(result["runtime_kvm_required"])
            self.assertEqual(result["admission_workflow_run_id"], 123)
            self.assertFalse(result["device_write_allowed"])
            self.assertEqual(len(validate_admission_continuity(result)), 64)

    def test_accepts_runtime_chain_only_with_kvm_qualified_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._collect(self._write_chain(Path(temporary), runtime=True))
            self.assertEqual(result["aosp_run_scope"], "BUILD_AND_RUNTIME")
            self.assertTrue(result["runtime_kvm_required"])
            self.assertTrue(result["admission_chain_verified"])

    def test_rejects_runtime_scope_with_build_only_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_chain(root, runtime=False)
            paths["run"].write_text(json.dumps(self._run_report(runtime=True), sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospAdmissionContinuityError):
                self._collect(paths)

    def test_rejects_tampered_attestation_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write_chain(Path(temporary), runtime=False)
            attestation = json.loads(paths["attestation"].read_text(encoding="utf-8"))
            attestation["requested_jobs"] = 8
            paths["attestation"].write_text(json.dumps(attestation, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospAdmissionContinuityError):
                self._collect(paths)

    def test_rejects_gate_from_different_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write_chain(Path(temporary), runtime=False)
            gate = json.loads(paths["gate"].read_text(encoding="utf-8"))
            gate["repository"] = "Other/Repo"
            paths["gate"].write_text(json.dumps(gate, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospAdmissionContinuityError):
                self._collect(paths)

    def test_rejects_tampered_run_evidence_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write_chain(Path(temporary), runtime=False)
            run = json.loads(paths["run"].read_text(encoding="utf-8"))
            run["source_commit"] = "2" * 40
            paths["run"].write_text(json.dumps(run, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospAdmissionContinuityError):
                self._collect(paths)

    def test_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write_chain(Path(temporary), runtime=False)
            paths["gate"].write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(AospAdmissionContinuityError):
                self._collect(paths)

    def test_report_validator_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._collect(self._write_chain(Path(temporary), runtime=False))
            result["requested_jobs"] = 32
            with self.assertRaises(AospAdmissionContinuityError):
                validate_admission_continuity(result)


if __name__ == "__main__":
    unittest.main()
