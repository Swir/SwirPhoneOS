from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from swirphoneos.aosp_admission_gate import (
    AospAdmissionGateError,
    main,
    validate_admission,
)
from swirphoneos.aosp_host_freshness import AospHostFreshnessError


SOURCE_COMMIT = "a" * 40
REPOSITORY = "Swir/SwirPhoneOS"
RUN_ID = 123456789
JOBS = 16


class AospAdmissionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.preflight_path = self.root / "builder-admission.json"
        self.attestation_path = self.root / "builder-admission-envelope.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_fixture(self, *, require_kvm: bool = True, kvm_available: bool = True) -> None:
        preflight = {
            "schema_version": 1,
            "operation": "READ_ONLY_HOST_PREFLIGHT",
            "ready_for_full_build": True,
            "cuttlefish_kvm_available": kvm_available,
            "workspace": {"cleanup_performed": False},
            "checks": [
                {"id": "workspace", "passed": True},
                {"id": "toolchain", "passed": True},
            ],
        }
        raw = (json.dumps(preflight, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        self.preflight_path.write_bytes(raw)
        attestation = {
            "schema_version": 1,
            "operation": "AOSP_BUILDER_ADMISSION_ATTESTATION",
            "admitted": True,
            "read_only": True,
            "source_commit": SOURCE_COMMIT,
            "repository": REPOSITORY,
            "workflow_run_id": RUN_ID,
            "requested_jobs": JOBS,
            "require_kvm": require_kvm,
            "preflight_sha256": hashlib.sha256(raw).hexdigest(),
            "preflight_operation": "READ_ONLY_HOST_PREFLIGHT",
            "ready_for_full_build": True,
            "cuttlefish_kvm_available": kvm_available,
            "workspace_cleanup_performed": False,
        }
        self.attestation_path.write_text(
            json.dumps(attestation, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def _validate(self, *, require_kvm: bool = False, **overrides: object) -> dict[str, object]:
        values = {
            "preflight_path": self.preflight_path,
            "attestation_path": self.attestation_path,
            "source_commit": SOURCE_COMMIT,
            "repository": REPOSITORY,
            "admission_run_id": RUN_ID,
            "requested_jobs": JOBS,
            "require_kvm": require_kvm,
        }
        values.update(overrides)
        return validate_admission(**values)  # type: ignore[arg-type]

    def _cli_args(self, *, require_kvm: bool = False) -> list[str]:
        args = [
            "--preflight", str(self.preflight_path),
            "--attestation", str(self.attestation_path),
            "--source-commit", SOURCE_COMMIT,
            "--repository", REPOSITORY,
            "--admission-run-id", str(RUN_ID),
            "--jobs", str(JOBS),
        ]
        if require_kvm:
            args.append("--require-kvm")
        return args

    def test_accepts_exact_build_contract_and_emits_fail_closed_gate(self) -> None:
        self._write_fixture(require_kvm=True, kvm_available=True)
        report = self._validate(require_kvm=True)
        self.assertTrue(report["admitted"])
        self.assertTrue(report["build_allowed"])
        self.assertTrue(report["read_only_admission"])
        self.assertFalse(report["device_write_allowed"])
        self.assertFalse(report["status_promotion_performed"])
        self.assertEqual(report["admission_workflow_run_id"], RUN_ID)
        self.assertEqual(report["requested_jobs"], JOBS)

    def test_build_only_run_accepts_admission_without_kvm_requirement(self) -> None:
        self._write_fixture(require_kvm=False, kvm_available=False)
        report = self._validate(require_kvm=False)
        self.assertFalse(report["runtime_kvm_required"])
        self.assertFalse(report["admission_required_kvm"])
        self.assertFalse(report["cuttlefish_kvm_available"])

    def test_runtime_run_requires_admission_that_required_and_admitted_kvm(self) -> None:
        self._write_fixture(require_kvm=False, kvm_available=True)
        with self.assertRaisesRegex(AospAdmissionGateError, "required and admitted KVM"):
            self._validate(require_kvm=True)

    def test_rejects_cross_commit_artifact(self) -> None:
        self._write_fixture()
        with self.assertRaisesRegex(AospAdmissionGateError, "different source commit"):
            self._validate(source_commit="b" * 40)

    def test_rejects_cross_run_artifact(self) -> None:
        self._write_fixture()
        with self.assertRaisesRegex(AospAdmissionGateError, "workflow run id"):
            self._validate(admission_run_id=RUN_ID + 1)

    def test_rejects_job_budget_drift(self) -> None:
        self._write_fixture()
        with self.assertRaisesRegex(AospAdmissionGateError, "job budget"):
            self._validate(requested_jobs=JOBS + 1)

    def test_rejects_attestation_if_preflight_bytes_change(self) -> None:
        self._write_fixture()
        value = json.loads(self.preflight_path.read_text(encoding="utf-8"))
        value["new_field"] = "tampered"
        self.preflight_path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(AospAdmissionGateError, "exact preflight bytes"):
            self._validate()

    def test_rejects_duplicate_json_keys(self) -> None:
        self._write_fixture()
        self.attestation_path.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
        with self.assertRaisesRegex(AospAdmissionGateError, "duplicate key"):
            self._validate()

    def test_cli_rechecks_exact_host_snapshot_before_emitting_unchanged_gate_contract(self) -> None:
        self._write_fixture(require_kvm=True, kvm_available=True)
        workspace = self.root / "aosp"
        workspace.mkdir()
        output = io.StringIO()

        with mock.patch.dict(
                 os.environ,
                 {"SWIR_AOSP_WORKSPACE": str(workspace), "SWIR_ADMISSION_RUN_ID": str(RUN_ID)},
                 clear=False,
             ), \
             mock.patch(
                 "swirphoneos.aosp_admission_gate.validate_admitted_host_freshness",
                 return_value={"fresh": True},
             ) as freshness_gate, \
             redirect_stdout(output):
            self.assertEqual(main(self._cli_args(require_kvm=True)), 0)

        freshness_gate.assert_called_once()
        call = freshness_gate.call_args
        self.assertEqual(call.args, ())
        self.assertEqual(
            set(call.kwargs),
            {"host_admission_path", "workspace", "require_kvm"},
        )
        self.assertEqual(
            call.kwargs["host_admission_path"],
            self.preflight_path.resolve().parent / "aosp-host-admission.json",
        )
        self.assertTrue(os.path.samefile(call.kwargs["workspace"], workspace))
        self.assertIs(call.kwargs["require_kvm"], True)
        emitted = json.loads(output.getvalue())
        self.assertEqual(emitted, self._validate(require_kvm=True))
        self.assertNotIn("host_freshness", emitted)

    def test_cli_requires_workspace_for_host_freshness_verification(self) -> None:
        self._write_fixture(require_kvm=True, kvm_available=True)
        with mock.patch.dict(os.environ, {"SWIR_ADMISSION_RUN_ID": str(RUN_ID)}, clear=True):
            with self.assertRaisesRegex(SystemExit, "SWIR_AOSP_WORKSPACE is required"):
                main(self._cli_args(require_kvm=True))

    def test_cli_rejects_workflow_run_environment_mismatch(self) -> None:
        self._write_fixture(require_kvm=True, kvm_available=True)
        with mock.patch.dict(os.environ, {"SWIR_ADMISSION_RUN_ID": str(RUN_ID + 1)}, clear=True):
            with self.assertRaisesRegex(SystemExit, "does not match the requested admission run id"):
                main(self._cli_args(require_kvm=True))

    def test_cli_fails_closed_when_current_host_no_longer_matches_admission(self) -> None:
        self._write_fixture(require_kvm=True, kvm_available=True)
        workspace = self.root / "aosp"
        workspace.mkdir()

        with mock.patch.dict(
                 os.environ,
                 {"SWIR_AOSP_WORKSPACE": str(workspace), "SWIR_ADMISSION_RUN_ID": str(RUN_ID)},
                 clear=False,
             ), \
             mock.patch(
                 "swirphoneos.aosp_admission_gate.validate_admitted_host_freshness",
                 side_effect=AospHostFreshnessError("identity drift: toolchain_sha256"),
             ):
            with self.assertRaisesRegex(SystemExit, "identity drift: toolchain_sha256"):
                main(self._cli_args(require_kvm=True))

    def test_cli_standalone_validation_does_not_require_workflow_environment(self) -> None:
        self._write_fixture(require_kvm=True, kvm_available=True)
        output = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            self.assertEqual(main(self._cli_args(require_kvm=True)), 0)
        self.assertEqual(json.loads(output.getvalue()), self._validate(require_kvm=True))

    def test_workflow_requires_exact_downloaded_admission_before_source_sync(self) -> None:
        workflow = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")
        self.assertIn("admission_run_id:", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093", workflow)
        self.assertIn("run-id: ${{ inputs.admission_run_id }}", workflow)
        self.assertIn("python -m swirphoneos.aosp_admission_gate", workflow)
        self.assertIn("builder-admission-build-gate.json", workflow)
        gate_position = workflow.index("python -m swirphoneos.aosp_admission_gate")
        sync_position = workflow.index("repo init -u https://android.googlesource.com/platform/manifest")
        self.assertLess(gate_position, sync_position)
        self.assertIn("builder-admission-envelope.json", workflow)
        self.assertIn("builder-admission.json", workflow)


if __name__ == "__main__":
    unittest.main()
