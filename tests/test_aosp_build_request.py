from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_build_request import AospBuildRequestError, validate_build_request


SHA = "a" * 40
REPOSITORY = "Swir/SwirPhoneOS"
RUN_ID = 123456


def _run_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": RUN_ID,
        "path": ".github/workflows/aosp-builder-admission.yml",
        "event": "workflow_dispatch",
        "status": "completed",
        "conclusion": "success",
        "head_branch": "main",
        "head_sha": SHA,
        "repository": {"full_name": REPOSITORY},
    }
    payload.update(changes)
    return payload


def _attestation(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "operation": "AOSP_BUILDER_ADMISSION_ATTESTATION",
        "admitted": True,
        "read_only": True,
        "source_commit": SHA,
        "repository": REPOSITORY,
        "workflow_run_id": RUN_ID,
        "requested_jobs": 16,
        "require_kvm": True,
        "preflight_sha256": "b" * 64,
        "preflight_operation": "READ_ONLY_HOST_PREFLIGHT",
        "ready_for_full_build": True,
        "cuttlefish_kvm_available": True,
        "workspace_cleanup_performed": False,
    }
    payload.update(changes)
    return payload


class AospBuildRequestTests(unittest.TestCase):
    def _validate(
        self,
        *,
        run: dict[str, object] | None = None,
        attestation: dict[str, object] | None = None,
        collect_runtime: bool = False,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_path = root / "run.json"
            attestation_path = root / "attestation.json"
            run_path.write_text(json.dumps(run or _run_payload()), encoding="utf-8")
            attestation_path.write_text(
                json.dumps(attestation or _attestation()), encoding="utf-8"
            )
            return validate_build_request(
                admission_run_path=run_path,
                attestation_path=attestation_path,
                source_commit=SHA,
                repository=REPOSITORY,
                admission_run_id=RUN_ID,
                collect_runtime=collect_runtime,
            )

    def test_exact_successful_admission_emits_bounded_build_inputs(self) -> None:
        payload = self._validate()
        self.assertEqual(payload["ref"], "main")
        self.assertEqual(
            payload["inputs"],
            {
                "admission_run_id": str(RUN_ID),
                "jobs": "16",
                "collect_runtime": False,
            },
        )

    def test_runtime_request_requires_admitted_kvm(self) -> None:
        payload = self._validate(collect_runtime=True)
        self.assertIs(payload["inputs"]["collect_runtime"], True)
        with self.assertRaisesRegex(AospBuildRequestError, "required and admitted KVM"):
            self._validate(
                attestation=_attestation(require_kvm=False, cuttlefish_kvm_available=True),
                collect_runtime=True,
            )

    def test_rejects_queued_failed_or_wrong_workflow_admission(self) -> None:
        cases = (
            _run_payload(status="queued", conclusion=None),
            _run_payload(conclusion="failure"),
            _run_payload(path=".github/workflows/ci.yml"),
        )
        for run in cases:
            with self.subTest(run=run):
                with self.assertRaises(AospBuildRequestError):
                    self._validate(run=run)

    def test_rejects_stale_commit_or_repository_identity(self) -> None:
        with self.assertRaisesRegex(AospBuildRequestError, "exact main commit"):
            self._validate(run=_run_payload(head_sha="c" * 40))
        with self.assertRaisesRegex(AospBuildRequestError, "different repository"):
            self._validate(run=_run_payload(repository={"full_name": "Other/Repo"}))
        with self.assertRaisesRegex(AospBuildRequestError, "different source commit"):
            self._validate(attestation=_attestation(source_commit="c" * 40))

    def test_rejects_attestation_that_is_not_exact_read_only_and_build_ready(self) -> None:
        cases = (
            _attestation(admitted=False),
            _attestation(read_only=False),
            _attestation(ready_for_full_build=False),
            _attestation(workspace_cleanup_performed=True),
            _attestation(preflight_operation="WRITE_PREFLIGHT"),
        )
        for attestation in cases:
            with self.subTest(attestation=attestation):
                with self.assertRaises(AospBuildRequestError):
                    self._validate(attestation=attestation)

    def test_rejects_job_budget_kvm_and_digest_tampering(self) -> None:
        cases = (
            _attestation(requested_jobs=0),
            _attestation(requested_jobs=257),
            _attestation(require_kvm=True, cuttlefish_kvm_available=False),
            _attestation(preflight_sha256="not-a-digest"),
        )
        for attestation in cases:
            with self.subTest(attestation=attestation):
                with self.assertRaises(AospBuildRequestError):
                    self._validate(attestation=attestation)

    def test_rejects_extra_attestation_fields(self) -> None:
        attestation = _attestation()
        attestation["build_verified"] = True
        with self.assertRaisesRegex(AospBuildRequestError, "field set is not exact"):
            self._validate(attestation=attestation)


if __name__ == "__main__":
    unittest.main()
