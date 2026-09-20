"""Fail-closed validation for AOSP builder admission artifacts.

The admission workflow is intentionally read-only. This module verifies that a
previous successful admission artifact belongs to the exact repository, source
commit, workflow run and requested build budget before the expensive AOSP build
workflow is allowed to touch its persistent workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


class AospAdmissionGateError(ValueError):
    """Raised when builder admission evidence cannot authorize a build run."""


_MAX_PREFLIGHT_BYTES = 256 * 1024
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
            raise AospAdmissionGateError("Admission JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_json(path: Path, *, maximum: int, label: str) -> tuple[dict[str, object], str]:
    if not path.is_file() or path.is_symlink():
        raise AospAdmissionGateError(f"{label} is missing or is not a regular file.")
    raw = path.read_bytes()
    if not raw or len(raw) > maximum:
        raise AospAdmissionGateError(f"{label} has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospAdmissionGateError(f"{label} must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise AospAdmissionGateError(f"{label} root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _positive_int(value: int | str, *, field: str, maximum: int | None = None) -> int:
    if isinstance(value, bool):
        raise AospAdmissionGateError(f"{field} must be a positive integer.")
    text = str(value)
    if not text.isdigit():
        raise AospAdmissionGateError(f"{field} must be a positive integer.")
    parsed = int(text)
    if parsed <= 0 or (maximum is not None and parsed > maximum):
        raise AospAdmissionGateError(f"{field} is outside the accepted range.")
    return parsed


def validate_admission(
    *,
    preflight_path: Path,
    attestation_path: Path,
    source_commit: str,
    repository: str,
    admission_run_id: int | str,
    requested_jobs: int | str,
    require_kvm: bool,
) -> dict[str, object]:
    """Validate one downloaded admission artifact against the build run contract."""

    if _HEX40.fullmatch(source_commit) is None:
        raise AospAdmissionGateError("Source commit must be an exact lowercase 40-character Git SHA-1.")
    if not repository or len(repository) > 200 or repository.count("/") != 1:
        raise AospAdmissionGateError("Repository identity is malformed.")
    expected_run_id = _positive_int(admission_run_id, field="admission_run_id")
    expected_jobs = _positive_int(requested_jobs, field="requested_jobs", maximum=256)

    preflight, preflight_sha256 = _load_json(
        preflight_path,
        maximum=_MAX_PREFLIGHT_BYTES,
        label="Builder admission preflight",
    )
    attestation, attestation_sha256 = _load_json(
        attestation_path,
        maximum=_MAX_ATTESTATION_BYTES,
        label="Builder admission attestation",
    )

    if preflight.get("operation") != "READ_ONLY_HOST_PREFLIGHT":
        raise AospAdmissionGateError("Admission preflight is not the read-only host contract.")
    if preflight.get("ready_for_full_build") is not True:
        raise AospAdmissionGateError("Admission preflight did not prove a build-ready host.")
    workspace = preflight.get("workspace")
    if not isinstance(workspace, dict) or workspace.get("cleanup_performed") is not False:
        raise AospAdmissionGateError("Admission preflight mutated or omitted workspace state.")
    checks = preflight.get("checks")
    if not isinstance(checks, list) or not checks:
        raise AospAdmissionGateError("Admission preflight has no checks.")
    if any(not isinstance(item, dict) or item.get("passed") is not True for item in checks):
        raise AospAdmissionGateError("Admission preflight contains a failed or malformed check.")

    if set(attestation) != _EXPECTED_ATTESTATION_KEYS:
        raise AospAdmissionGateError("Admission attestation field set is not exact.")
    if attestation.get("schema_version") != 1 or attestation.get("operation") != "AOSP_BUILDER_ADMISSION_ATTESTATION":
        raise AospAdmissionGateError("Admission attestation schema is unsupported.")
    if attestation.get("admitted") is not True or attestation.get("read_only") is not True:
        raise AospAdmissionGateError("Admission attestation is not an admitted read-only contract.")
    if attestation.get("preflight_operation") != "READ_ONLY_HOST_PREFLIGHT":
        raise AospAdmissionGateError("Admission attestation references the wrong preflight operation.")
    if attestation.get("ready_for_full_build") is not True or attestation.get("workspace_cleanup_performed") is not False:
        raise AospAdmissionGateError("Admission attestation does not preserve the accepted preflight contract.")

    if attestation.get("source_commit") != source_commit:
        raise AospAdmissionGateError("Admission artifact belongs to a different source commit.")
    if attestation.get("repository") != repository:
        raise AospAdmissionGateError("Admission artifact belongs to a different repository.")
    if attestation.get("workflow_run_id") != expected_run_id:
        raise AospAdmissionGateError("Admission artifact workflow run id does not match the requested run.")
    if attestation.get("requested_jobs") != expected_jobs:
        raise AospAdmissionGateError("Admission artifact job budget does not match the build request.")

    digest = attestation.get("preflight_sha256")
    if _HEX64.fullmatch(str(digest or "")) is None or digest != preflight_sha256:
        raise AospAdmissionGateError("Admission attestation is not bound to the exact preflight bytes.")

    preflight_kvm = preflight.get("cuttlefish_kvm_available") is True
    attested_kvm = attestation.get("cuttlefish_kvm_available") is True
    if attested_kvm != preflight_kvm:
        raise AospAdmissionGateError("Admission attestation KVM state does not match the preflight.")
    admission_required_kvm = attestation.get("require_kvm")
    if not isinstance(admission_required_kvm, bool):
        raise AospAdmissionGateError("Admission KVM requirement is malformed.")
    if admission_required_kvm and not attested_kvm:
        raise AospAdmissionGateError("Admission claimed a KVM requirement without admitted KVM.")
    if require_kvm and (not admission_required_kvm or not attested_kvm):
        raise AospAdmissionGateError("Runtime collection requires an admission run that required and admitted KVM.")

    return {
        "schema_version": 1,
        "operation": "AOSP_BUILD_ADMISSION_GATE",
        "admitted": True,
        "build_allowed": True,
        "source_commit": source_commit,
        "repository": repository,
        "admission_workflow_run_id": expected_run_id,
        "requested_jobs": expected_jobs,
        "runtime_kvm_required": require_kvm,
        "admission_required_kvm": admission_required_kvm,
        "cuttlefish_kvm_available": attested_kvm,
        "preflight_sha256": preflight_sha256,
        "attestation_sha256": attestation_sha256,
        "read_only_admission": True,
        "workspace_cleanup_performed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate exact AOSP builder admission before build work.")
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--attestation", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--admission-run-id", required=True)
    parser.add_argument("--jobs", required=True)
    parser.add_argument("--require-kvm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = validate_admission(
            preflight_path=args.preflight,
            attestation_path=args.attestation,
            source_commit=args.source_commit,
            repository=args.repository,
            admission_run_id=args.admission_run_id,
            requested_jobs=args.jobs,
            require_kvm=args.require_kvm,
        )
    except (AospAdmissionGateError, OSError) as exc:
        raise SystemExit(f"AOSP build admission gate rejected: {exc}") from exc
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
