"""Fail-closed continuity proof from one completed AOSP run to its exact builder admission.

The build workflow already rejects an invalid admission before touching the persistent
AOSP workspace. This module preserves that authorization in post-run evidence by
re-validating the downloaded admission preflight and attestation, requiring the exact
gate output used by the build, and binding all of it to the completed run-evidence
bytes. It is read-only and never promotes milestones, beta gates, device support or
release state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .aosp_admission_gate import AospAdmissionGateError, validate_admission

PRODUCT = "swirphoneos_cf_x86_64"
MAX_JSON = 16 * 1024 * 1024
H40 = re.compile(r"[0-9a-f]{40}\Z")
H64 = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED_GATE_KEYS = {
    "schema_version",
    "operation",
    "admitted",
    "build_allowed",
    "source_commit",
    "repository",
    "admission_workflow_run_id",
    "requested_jobs",
    "runtime_kvm_required",
    "admission_required_kvm",
    "cuttlefish_kvm_available",
    "preflight_sha256",
    "attestation_sha256",
    "read_only_admission",
    "workspace_cleanup_performed",
    "device_write_allowed",
    "status_promotion_performed",
}


class AospAdmissionContinuityError(ValueError):
    """Raised when a completed AOSP run is not bound to one exact admission chain."""


def _canonical_sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospAdmissionContinuityError("duplicate JSON key")
        result[key] = value
    return result


def _load(path: Path, *, maximum: int = MAX_JSON) -> tuple[dict[str, object], str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise AospAdmissionContinuityError("unsafe or missing evidence path")
    raw = path.read_bytes()
    if not raw or len(raw) > maximum:
        raise AospAdmissionContinuityError("invalid evidence size")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospAdmissionContinuityError("invalid evidence JSON") from exc
    if not isinstance(value, dict):
        raise AospAdmissionContinuityError("invalid evidence root")
    return value, hashlib.sha256(raw).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or H64.fullmatch(value) is None:
        raise AospAdmissionContinuityError(f"invalid {field}")
    return value


def _positive_int(value: object, field: str, *, maximum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise AospAdmissionContinuityError(f"invalid {field}")
    if maximum is not None and value > maximum:
        raise AospAdmissionContinuityError(f"invalid {field}")
    return value


def _validate_run(report: dict[str, object]) -> tuple[str, str, str, bool]:
    scope = report.get("scope")
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_run_evidence_chain"
        or report.get("expected_product") != PRODUCT
        or scope not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}
        or report.get("build_chain_complete") is not True
        or report.get("run_evidence_complete") is not True
        or (scope == "BUILD_AND_RUNTIME") != (report.get("runtime_chain_complete") is True)
    ):
        raise AospAdmissionContinuityError("invalid AOSP run evidence")
    if any(
        report.get(key) is not False
        for key in ("device_write_allowed", "physical_device_support_claimed", "status_promotion_performed")
    ):
        raise AospAdmissionContinuityError("AOSP run evidence exceeds read-only boundary")
    commit = report.get("source_commit")
    if not isinstance(commit, str) or H40.fullmatch(commit) is None:
        raise AospAdmissionContinuityError("invalid source commit")
    run_sha = _hex64(report.get("run_evidence_sha256"), "run evidence digest")
    canonical = {
        key: value
        for key, value in report.items()
        if key not in {"run_evidence_sha256", "run_evidence_complete"}
    }
    if _canonical_sha(canonical) != run_sha:
        raise AospAdmissionContinuityError("run evidence canonical digest mismatch")
    return commit, str(scope), run_sha, scope == "BUILD_AND_RUNTIME"


def _validate_gate(report: dict[str, object], *, source_commit: str, repository: str, runtime_required: bool) -> tuple[int, int]:
    if set(report) != EXPECTED_GATE_KEYS:
        raise AospAdmissionContinuityError("admission gate field set is not exact")
    if (
        report.get("schema_version") != 1
        or report.get("operation") != "AOSP_BUILD_ADMISSION_GATE"
        or report.get("admitted") is not True
        or report.get("build_allowed") is not True
        or report.get("read_only_admission") is not True
        or report.get("workspace_cleanup_performed") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise AospAdmissionContinuityError("invalid AOSP admission gate")
    if report.get("source_commit") != source_commit or report.get("repository") != repository:
        raise AospAdmissionContinuityError("admission gate identity mismatch")
    if report.get("runtime_kvm_required") is not runtime_required:
        raise AospAdmissionContinuityError("admission runtime/KVM contract does not match completed run scope")
    if not isinstance(report.get("admission_required_kvm"), bool) or not isinstance(report.get("cuttlefish_kvm_available"), bool):
        raise AospAdmissionContinuityError("invalid admission KVM state")
    if runtime_required and (report.get("admission_required_kvm") is not True or report.get("cuttlefish_kvm_available") is not True):
        raise AospAdmissionContinuityError("runtime run lacks KVM-qualified admission")
    _hex64(report.get("preflight_sha256"), "admission preflight digest")
    _hex64(report.get("attestation_sha256"), "admission attestation digest")
    return (
        _positive_int(report.get("admission_workflow_run_id"), "admission workflow run id"),
        _positive_int(report.get("requested_jobs"), "requested job budget", maximum=256),
    )


def collect_admission_continuity(
    *,
    run_evidence_path: Path,
    gate_path: Path,
    preflight_path: Path,
    attestation_path: Path,
    repository: str,
    expected_source_commit: str | None = None,
) -> dict[str, object]:
    """Re-validate and bind one completed run to the exact admission that authorized it."""
    if not repository or len(repository) > 200 or repository.count("/") != 1:
        raise AospAdmissionContinuityError("invalid repository identity")

    run, run_file_sha = _load(run_evidence_path)
    gate, gate_file_sha = _load(gate_path)
    _preflight, preflight_file_sha = _load(preflight_path, maximum=256 * 1024)
    _attestation, attestation_file_sha = _load(attestation_path, maximum=8 * 1024)

    source_commit, scope, run_sha, runtime_required = _validate_run(run)
    if expected_source_commit is not None:
        if H40.fullmatch(expected_source_commit) is None or expected_source_commit != source_commit:
            raise AospAdmissionContinuityError("triggering source commit mismatch")

    admission_run_id, requested_jobs = _validate_gate(
        gate,
        source_commit=source_commit,
        repository=repository,
        runtime_required=runtime_required,
    )

    try:
        regenerated_gate = validate_admission(
            preflight_path=preflight_path,
            attestation_path=attestation_path,
            source_commit=source_commit,
            repository=repository,
            admission_run_id=admission_run_id,
            requested_jobs=requested_jobs,
            require_kvm=runtime_required,
        )
    except (AospAdmissionGateError, OSError, ValueError) as exc:
        raise AospAdmissionContinuityError("admission chain re-validation failed") from exc
    if regenerated_gate != gate:
        raise AospAdmissionContinuityError("retained gate does not equal regenerated admission contract")
    if gate.get("preflight_sha256") != preflight_file_sha or gate.get("attestation_sha256") != attestation_file_sha:
        raise AospAdmissionContinuityError("retained gate is not bound to exact admission file bytes")

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_admission_continuity_evidence",
        "operation": "READ_ONLY_BIND_COMPLETED_RUN_TO_EXACT_ADMISSION",
        "source_commit": source_commit,
        "repository": repository,
        "aosp_run_scope": scope,
        "run_evidence_sha256": run_sha,
        "run_evidence_file_sha256": run_file_sha,
        "admission_workflow_run_id": admission_run_id,
        "requested_jobs": requested_jobs,
        "runtime_kvm_required": runtime_required,
        "preflight_sha256": preflight_file_sha,
        "attestation_sha256": attestation_file_sha,
        "gate_file_sha256": gate_file_sha,
        "admission_chain_verified": True,
        "exact_run_bytes_bound": True,
        "read_only_verification": True,
        "workspace_cleanup_performed": False,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "milestone_promoted": False,
        "beta_gate_passed": False,
        "release_artifact_authorized": False,
        "warnings": [
            "This proves the completed host-side AOSP run retained the exact admission chain that authorized it.",
            "It does not prove a successful physical-device boot, install, rollback, recovery, telephony, camera or root path.",
            "It never authorizes device writes, release publication, milestone promotion or beta-gate promotion.",
        ],
    }
    payload["admission_continuity_sha256"] = _canonical_sha(payload)
    return payload


def validate_admission_continuity(report: dict[str, object]) -> str:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_admission_continuity_evidence"
        or report.get("operation") != "READ_ONLY_BIND_COMPLETED_RUN_TO_EXACT_ADMISSION"
        or report.get("aosp_run_scope") not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}
        or report.get("admission_chain_verified") is not True
        or report.get("exact_run_bytes_bound") is not True
        or report.get("read_only_verification") is not True
        or report.get("workspace_cleanup_performed") is not False
        or any(
            report.get(key) is not False
            for key in (
                "device_write_allowed",
                "physical_device_support_claimed",
                "status_promotion_performed",
                "milestone_promoted",
                "beta_gate_passed",
                "release_artifact_authorized",
            )
        )
    ):
        raise AospAdmissionContinuityError("invalid admission-continuity evidence")
    commit = report.get("source_commit")
    repository = report.get("repository")
    if not isinstance(commit, str) or H40.fullmatch(commit) is None:
        raise AospAdmissionContinuityError("invalid continuity source commit")
    if not isinstance(repository, str) or not repository or len(repository) > 200 or repository.count("/") != 1:
        raise AospAdmissionContinuityError("invalid continuity repository")
    _positive_int(report.get("admission_workflow_run_id"), "admission workflow run id")
    _positive_int(report.get("requested_jobs"), "requested job budget", maximum=256)
    if not isinstance(report.get("runtime_kvm_required"), bool):
        raise AospAdmissionContinuityError("invalid runtime KVM requirement")
    if (report.get("aosp_run_scope") == "BUILD_AND_RUNTIME") != report.get("runtime_kvm_required"):
        raise AospAdmissionContinuityError("continuity scope/KVM requirement mismatch")
    for key in (
        "run_evidence_sha256",
        "run_evidence_file_sha256",
        "preflight_sha256",
        "attestation_sha256",
        "gate_file_sha256",
    ):
        _hex64(report.get(key), key)
    digest = _hex64(report.get("admission_continuity_sha256"), "admission continuity digest")
    if _canonical_sha({key: value for key, value in report.items() if key != "admission_continuity_sha256"}) != digest:
        raise AospAdmissionContinuityError("admission continuity canonical digest mismatch")
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind one completed SwirPhoneOS AOSP run to its exact builder admission")
    parser.add_argument("--run-evidence", required=True, type=Path)
    parser.add_argument("--gate", required=True, type=Path)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--attestation", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    try:
        report = collect_admission_continuity(
            run_evidence_path=args.run_evidence.resolve(),
            gate_path=args.gate.resolve(),
            preflight_path=args.preflight.resolve(),
            attestation_path=args.attestation.resolve(),
            repository=args.repository,
            expected_source_commit=args.source_commit,
        )
        validate_admission_continuity(report)
    except (AospAdmissionContinuityError, AospAdmissionGateError, OSError, RuntimeError, UnicodeError, ValueError):
        print("AOSP admission continuity failed: completed run is not bound to one exact admitted builder contract.", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
