"""Fail-closed validation for admission-backed AOSP build dispatch requests.

This module does not build Android and does not contact GitHub. It validates a
completed builder-admission workflow snapshot plus the exact admission
envelope, then emits a deterministic workflow-dispatch payload for the matching
``aosp-build-evidence.yml`` run. The source commit, repository, workflow run,
job budget and optional runtime/KVM requirement must all remain exact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


class AospBuildRequestError(ValueError):
    """Raised when admission evidence cannot authorize a build dispatch."""


_MAX_RUN_BYTES = 512 * 1024
_MAX_ATTESTATION_BYTES = 8 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_EXPECTED_ATTESTATION_KEYS = {
    "schema_version",
    "operation",
    "admitted",
    "read_only",
    "source_commit",
    "repository",
    "workflow_run_id",
    "requested_jobs",
    "require_kvm",
    "preflight_sha256",
    "preflight_operation",
    "ready_for_full_build",
    "cuttlefish_kvm_available",
    "workspace_cleanup_performed",
}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospBuildRequestError("Build-request JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_json(path: Path, *, maximum: int, label: str) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise AospBuildRequestError(f"{label} is missing or is not a regular file.")
    raw = path.read_bytes()
    if not raw or len(raw) > maximum:
        raise AospBuildRequestError(f"{label} has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospBuildRequestError(f"{label} must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise AospBuildRequestError(f"{label} root must be an object.")
    return value


def _positive_int(value: object, *, field: str, maximum: int | None = None) -> int:
    if isinstance(value, bool):
        raise AospBuildRequestError(f"{field} must be a positive integer.")
    text = str(value)
    if not text.isdigit():
        raise AospBuildRequestError(f"{field} must be a positive integer.")
    parsed = int(text)
    if parsed <= 0 or (maximum is not None and parsed > maximum):
        raise AospBuildRequestError(f"{field} is outside the accepted range.")
    return parsed


def validate_build_request(
    *,
    admission_run_path: Path,
    attestation_path: Path,
    source_commit: str,
    repository: str,
    admission_run_id: int | str,
    collect_runtime: bool,
) -> dict[str, object]:
    """Return an exact build-workflow dispatch payload or fail closed."""

    if _HEX40.fullmatch(source_commit) is None:
        raise AospBuildRequestError(
            "Source commit must be an exact lowercase 40-character Git SHA-1."
        )
    if not repository or len(repository) > 200 or repository.count("/") != 1:
        raise AospBuildRequestError("Repository identity is malformed.")
    if not isinstance(collect_runtime, bool):
        raise AospBuildRequestError("collect_runtime must be boolean.")
    expected_run_id = _positive_int(admission_run_id, field="admission_run_id")

    run = _load_json(
        admission_run_path,
        maximum=_MAX_RUN_BYTES,
        label="Admission workflow run metadata",
    )
    if run.get("id") != expected_run_id:
        raise AospBuildRequestError("Admission workflow run id is not exact.")
    if run.get("path") != ".github/workflows/aosp-builder-admission.yml":
        raise AospBuildRequestError("Admission metadata references the wrong workflow.")
    if run.get("event") != "workflow_dispatch":
        raise AospBuildRequestError("Admission workflow was not explicitly dispatched.")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise AospBuildRequestError("Admission workflow is not completed successfully.")
    if run.get("head_branch") != "main" or run.get("head_sha") != source_commit:
        raise AospBuildRequestError("Admission workflow does not belong to the exact main commit.")
    run_repository = run.get("repository")
    if not isinstance(run_repository, dict) or run_repository.get("full_name") != repository:
        raise AospBuildRequestError("Admission workflow belongs to a different repository.")

    attestation = _load_json(
        attestation_path,
        maximum=_MAX_ATTESTATION_BYTES,
        label="Admission attestation",
    )
    if set(attestation) != _EXPECTED_ATTESTATION_KEYS:
        raise AospBuildRequestError("Admission attestation field set is not exact.")
    if (
        attestation.get("schema_version") != 1
        or attestation.get("operation") != "AOSP_BUILDER_ADMISSION_ATTESTATION"
    ):
        raise AospBuildRequestError("Admission attestation schema is unsupported.")
    if attestation.get("admitted") is not True or attestation.get("read_only") is not True:
        raise AospBuildRequestError("Admission attestation is not an admitted read-only contract.")
    if attestation.get("source_commit") != source_commit:
        raise AospBuildRequestError("Admission attestation belongs to a different source commit.")
    if attestation.get("repository") != repository:
        raise AospBuildRequestError("Admission attestation belongs to a different repository.")
    if attestation.get("workflow_run_id") != expected_run_id:
        raise AospBuildRequestError("Admission attestation workflow run id does not match.")
    if attestation.get("preflight_operation") != "READ_ONLY_HOST_PREFLIGHT":
        raise AospBuildRequestError("Admission attestation references the wrong preflight operation.")
    if attestation.get("ready_for_full_build") is not True:
        raise AospBuildRequestError("Admission did not prove a build-ready host.")
    if attestation.get("workspace_cleanup_performed") is not False:
        raise AospBuildRequestError("Admission mutated or ambiguously reported workspace state.")

    jobs = _positive_int(attestation.get("requested_jobs"), field="requested_jobs", maximum=256)
    require_kvm = attestation.get("require_kvm")
    kvm_available = attestation.get("cuttlefish_kvm_available")
    if not isinstance(require_kvm, bool) or not isinstance(kvm_available, bool):
        raise AospBuildRequestError("Admission KVM state is malformed.")
    if require_kvm and not kvm_available:
        raise AospBuildRequestError("Admission required KVM without proving KVM availability.")
    if collect_runtime and (not require_kvm or not kvm_available):
        raise AospBuildRequestError(
            "Runtime collection requires an admission that required and admitted KVM."
        )
    digest = str(attestation.get("preflight_sha256") or "")
    if _HEX64.fullmatch(digest) is None:
        raise AospBuildRequestError("Admission preflight digest is malformed.")

    return {
        "ref": "main",
        "inputs": {
            "admission_run_id": str(expected_run_id),
            "jobs": str(jobs),
            "collect_runtime": collect_runtime,
        },
    }


def public_request_report(payload: dict[str, object], *, source_commit: str, repository: str) -> dict[str, object]:
    inputs = payload["inputs"]
    assert isinstance(inputs, dict)
    return {
        "schema_version": 1,
        "operation": "AOSP_BUILD_REQUEST_VALIDATION",
        "request_valid": True,
        "target_ref": payload["ref"],
        "source_commit": source_commit,
        "repository": repository,
        "admission_run_id": int(str(inputs["admission_run_id"])),
        "requested_jobs": int(str(inputs["jobs"])),
        "collect_runtime": bool(inputs["collect_runtime"]),
        "device_write_allowed": False,
        "build_verified": False,
        "boot_verified": False,
        "status_promotion_performed": False,
    }


def _parse_bool(text: str) -> bool:
    value = text.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("boolean value must be true or false")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate an exact successful AOSP admission before build dispatch."
    )
    parser.add_argument("--admission-run", required=True, type=Path)
    parser.add_argument("--attestation", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--admission-run-id", required=True)
    parser.add_argument("--collect-runtime", required=True, type=_parse_bool)
    parser.add_argument("--dispatch-output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = validate_build_request(
            admission_run_path=args.admission_run,
            attestation_path=args.attestation,
            source_commit=args.source_commit,
            repository=args.repository,
            admission_run_id=args.admission_run_id,
            collect_runtime=args.collect_runtime,
        )
        output = args.dispatch_output
        if output.exists() and output.is_symlink():
            raise AospBuildRequestError("Dispatch output must not be a symlink.")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    except (AospBuildRequestError, OSError, ValueError) as exc:
        raise SystemExit(f"AOSP build request rejected: {exc}") from exc
    print(
        json.dumps(
            public_request_report(payload, source_commit=args.source_commit, repository=args.repository),
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
