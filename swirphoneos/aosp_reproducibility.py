"""Fail-closed comparison of two independently captured AOSP build evidence chains.

The verifier is deliberately read-only. It accepts two already-produced AOSP run
reports and their post-run artifact-continuity reports, proves that both runs were
bound to the same reviewed source inputs, then requires the complete retained
artifact inventory to match byte-for-byte.

A matching pair is evidence for one reproducibility observation only. It never
promotes project milestones, beta gates, device support, releases, flashing or
root state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .aosp_artifact_continuity import (
    AospArtifactContinuityError,
    PRODUCT,
    validate_artifact_continuity,
)

MAX_JSON = 16 * 1024 * 1024
H40 = re.compile(r"[0-9a-f]{40}\Z")
H64 = re.compile(r"[0-9a-f]{64}\Z")


class AospReproducibilityError(ValueError):
    """Raised when two build chains cannot form a trustworthy matching pair."""


def _canonical_sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospReproducibilityError("duplicate JSON key")
        result[key] = value
    return result


def _load(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise AospReproducibilityError("unsafe evidence path")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_JSON:
        raise AospReproducibilityError("invalid evidence size")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospReproducibilityError("invalid evidence JSON") from exc
    if not isinstance(value, dict):
        raise AospReproducibilityError("invalid evidence root")
    return value, hashlib.sha256(raw).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or H64.fullmatch(value) is None:
        raise AospReproducibilityError(f"invalid {field}")
    return value


def _strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise AospReproducibilityError(f"invalid {field}")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 256 or item in seen:
            raise AospReproducibilityError(f"invalid {field}")
        seen.add(item)
        result.append(item)
    return result


def _validate_run(report: dict[str, object]) -> dict[str, object]:
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
        raise AospReproducibilityError("invalid AOSP run evidence")
    if any(
        report.get(key) is not False
        for key in ("device_write_allowed", "physical_device_support_claimed", "status_promotion_performed")
    ):
        raise AospReproducibilityError("run evidence exceeds read-only boundary")

    commit = report.get("source_commit")
    fingerprint = report.get("build_fingerprint")
    if not isinstance(commit, str) or H40.fullmatch(commit) is None:
        raise AospReproducibilityError("invalid source commit")
    if not isinstance(fingerprint, str) or not fingerprint or len(fingerprint) > 1024:
        raise AospReproducibilityError("invalid build fingerprint")
    try:
        fingerprint_sha = hashlib.sha256(fingerprint.encode("ascii", "strict")).hexdigest()
    except UnicodeError as exc:
        raise AospReproducibilityError("non-ASCII build fingerprint") from exc
    if report.get("build_fingerprint_sha256") != fingerprint_sha:
        raise AospReproducibilityError("build fingerprint digest mismatch")

    staged = _hex64(report.get("staged_content_sha256"), "staged content digest")
    app_manifest = _hex64(report.get("app_manifest_sha256"), "app manifest digest")
    workspace = _hex64(report.get("workspace_sha256"), "workspace identity digest")
    packages = sorted(_strings(report.get("source_ready_packages"), "source-ready package set"))
    hashes = report.get("report_file_sha256")
    if not isinstance(hashes, dict):
        raise AospReproducibilityError("missing report hash map")
    resolved_manifest = _hex64(hashes.get("resolved_manifest"), "resolved-manifest file digest")
    build_evidence = _hex64(hashes.get("build_evidence"), "build-evidence file digest")

    run_sha = _hex64(report.get("run_evidence_sha256"), "run evidence digest")
    canonical = {key: value for key, value in report.items() if key not in {"run_evidence_sha256", "run_evidence_complete"}}
    if _canonical_sha(canonical) != run_sha:
        raise AospReproducibilityError("run evidence canonical digest mismatch")

    return {
        "source_commit": commit,
        "scope": scope,
        "workspace_sha256": workspace,
        "staged_content_sha256": staged,
        "resolved_manifest_file_sha256": resolved_manifest,
        "app_manifest_sha256": app_manifest,
        "source_ready_packages": packages,
        "build_fingerprint": fingerprint,
        "run_evidence_sha256": run_sha,
        "build_evidence_file_sha256": build_evidence,
    }


def _validate_continuity(
    report: dict[str, object], *, run: dict[str, object], run_file_sha256: str
) -> dict[str, object]:
    try:
        continuity_sha = validate_artifact_continuity(report)
    except (AospArtifactContinuityError, ValueError) as exc:
        raise AospReproducibilityError("invalid artifact continuity evidence") from exc
    if report.get("source_commit") != run["source_commit"]:
        raise AospReproducibilityError("continuity source commit mismatch")
    if report.get("run_evidence_sha256") != run["run_evidence_sha256"]:
        raise AospReproducibilityError("continuity run digest mismatch")
    if report.get("workspace_identity_sha256") != run["workspace_sha256"]:
        raise AospReproducibilityError("continuity workspace mismatch")
    if report.get("build_fingerprint") != run["build_fingerprint"]:
        raise AospReproducibilityError("continuity build fingerprint mismatch")
    if report.get("build_evidence_file_sha256") != run["build_evidence_file_sha256"]:
        raise AospReproducibilityError("continuity build-evidence binding mismatch")
    hashes = report.get("report_file_sha256")
    if not isinstance(hashes, dict) or hashes.get("aosp_run_evidence") != run_file_sha256:
        raise AospReproducibilityError("continuity is not bound to exact run-evidence bytes")

    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise AospReproducibilityError("continuity artifact inventory is empty")
    normalized: list[dict[str, object]] = []
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise AospReproducibilityError("malformed continuity artifact")
        normalized.append({"path": item["path"], "size": item["size"], "sha256": item["sha256"]})
    return {
        "continuity_sha256": continuity_sha,
        "artifact_set_sha256": _hex64(report.get("artifact_set_sha256"), "artifact-set digest"),
        "artifacts": normalized,
    }


def compare_reproducibility_pair(
    run_a_path: Path,
    continuity_a_path: Path,
    run_b_path: Path,
    continuity_b_path: Path,
    *,
    expected_source_commit: str | None = None,
) -> dict[str, object]:
    """Return a canonical matching-pair report or fail closed on any mismatch."""
    run_a_raw, run_a_file_sha = _load(run_a_path)
    continuity_a_raw, continuity_a_file_sha = _load(continuity_a_path)
    run_b_raw, run_b_file_sha = _load(run_b_path)
    continuity_b_raw, continuity_b_file_sha = _load(continuity_b_path)

    run_a = _validate_run(run_a_raw)
    run_b = _validate_run(run_b_raw)
    if expected_source_commit is not None:
        if H40.fullmatch(expected_source_commit) is None:
            raise AospReproducibilityError("invalid expected source commit")
        if run_a["source_commit"] != expected_source_commit or run_b["source_commit"] != expected_source_commit:
            raise AospReproducibilityError("triggering source commit mismatch")

    comparable_fields = (
        "source_commit",
        "staged_content_sha256",
        "resolved_manifest_file_sha256",
        "app_manifest_sha256",
        "source_ready_packages",
        "build_fingerprint",
    )
    for field in comparable_fields:
        if run_a[field] != run_b[field]:
            raise AospReproducibilityError(f"reviewed build input mismatch: {field}")

    continuity_a = _validate_continuity(continuity_a_raw, run=run_a, run_file_sha256=run_a_file_sha)
    continuity_b = _validate_continuity(continuity_b_raw, run=run_b, run_file_sha256=run_b_file_sha)
    if continuity_a["artifacts"] != continuity_b["artifacts"]:
        raise AospReproducibilityError("build artifact bytes are not reproducible")
    if continuity_a["artifact_set_sha256"] != continuity_b["artifact_set_sha256"]:
        raise AospReproducibilityError("artifact-set digest mismatch")

    artifacts = continuity_a["artifacts"]
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_reproducibility_pair_evidence",
        "operation": "READ_ONLY_COMPARE_TWO_INDEPENDENT_BUILDS",
        "expected_product": PRODUCT,
        "source_commit": run_a["source_commit"],
        "reviewed_input_identity": {
            "resolved_manifest_file_sha256": run_a["resolved_manifest_file_sha256"],
            "staged_content_sha256": run_a["staged_content_sha256"],
            "app_manifest_sha256": run_a["app_manifest_sha256"],
            "source_ready_packages": run_a["source_ready_packages"],
            "build_fingerprint": run_a["build_fingerprint"],
        },
        "run_a": {
            "scope": run_a["scope"],
            "run_evidence_sha256": run_a["run_evidence_sha256"],
            "run_evidence_file_sha256": run_a_file_sha,
            "continuity_sha256": continuity_a["continuity_sha256"],
            "continuity_file_sha256": continuity_a_file_sha,
        },
        "run_b": {
            "scope": run_b["scope"],
            "run_evidence_sha256": run_b["run_evidence_sha256"],
            "run_evidence_file_sha256": run_b_file_sha,
            "continuity_sha256": continuity_b["continuity_sha256"],
            "continuity_file_sha256": continuity_b_file_sha,
        },
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "artifact_set_sha256": continuity_a["artifact_set_sha256"],
        "same_reviewed_inputs": True,
        "artifact_bytes_identical": True,
        "reproducibility_pair_complete": True,
        "reproducibility_observation": "MATCHING_PAIR",
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "milestone_promoted": False,
        "beta_gate_passed": False,
        "release_artifact_authorized": False,
        "warnings": [
            "This proves one matching pair of retained build artifacts for the same reviewed inputs.",
            "One matching pair alone does not complete the reproducible-build milestone or any beta gate.",
            "This is not physical-device, install, rollback, recovery, telephony, camera or root evidence.",
        ],
    }
    payload["reproducibility_pair_sha256"] = _canonical_sha(payload)
    return payload


def validate_reproducibility_pair(report: dict[str, object]) -> str:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_reproducibility_pair_evidence"
        or report.get("operation") != "READ_ONLY_COMPARE_TWO_INDEPENDENT_BUILDS"
        or report.get("expected_product") != PRODUCT
        or report.get("reproducibility_observation") != "MATCHING_PAIR"
        or any(report.get(key) is not True for key in ("same_reviewed_inputs", "artifact_bytes_identical", "reproducibility_pair_complete"))
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
        raise AospReproducibilityError("invalid reproducibility-pair evidence")
    commit = report.get("source_commit")
    if not isinstance(commit, str) or H40.fullmatch(commit) is None:
        raise AospReproducibilityError("invalid reproducibility source commit")
    identity = report.get("reviewed_input_identity")
    if not isinstance(identity, dict):
        raise AospReproducibilityError("missing reviewed input identity")
    for key in ("resolved_manifest_file_sha256", "staged_content_sha256", "app_manifest_sha256"):
        _hex64(identity.get(key), key)
    _strings(identity.get("source_ready_packages"), "source-ready package set")
    if not isinstance(identity.get("build_fingerprint"), str) or not identity.get("build_fingerprint"):
        raise AospReproducibilityError("missing build fingerprint")
    for run_key in ("run_a", "run_b"):
        run = report.get(run_key)
        if not isinstance(run, dict) or run.get("scope") not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}:
            raise AospReproducibilityError("invalid run identity")
        for key in ("run_evidence_sha256", "run_evidence_file_sha256", "continuity_sha256", "continuity_file_sha256"):
            _hex64(run.get(key), key)
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts or report.get("artifact_count") != len(artifacts):
        raise AospReproducibilityError("invalid reproducibility artifact inventory")
    seen: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise AospReproducibilityError("malformed reproducibility artifact")
        path = item.get("path")
        size = item.get("size")
        if not isinstance(path, str) or not path or path in seen:
            raise AospReproducibilityError("invalid reproducibility artifact path")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise AospReproducibilityError("invalid reproducibility artifact size")
        _hex64(item.get("sha256"), "artifact digest")
        seen.add(path)
    if _canonical_sha(artifacts) != report.get("artifact_set_sha256"):
        raise AospReproducibilityError("reproducibility artifact-set digest mismatch")
    digest = _hex64(report.get("reproducibility_pair_sha256"), "reproducibility pair digest")
    if _canonical_sha({key: value for key, value in report.items() if key != "reproducibility_pair_sha256"}) != digest:
        raise AospReproducibilityError("reproducibility pair canonical digest mismatch")
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two exact SwirPhoneOS AOSP build evidence chains")
    parser.add_argument("--run-a", required=True, type=Path)
    parser.add_argument("--continuity-a", required=True, type=Path)
    parser.add_argument("--run-b", required=True, type=Path)
    parser.add_argument("--continuity-b", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    try:
        report = compare_reproducibility_pair(
            args.run_a.resolve(),
            args.continuity_a.resolve(),
            args.run_b.resolve(),
            args.continuity_b.resolve(),
            expected_source_commit=args.source_commit,
        )
        validate_reproducibility_pair(report)
    except (AospReproducibilityError, AospArtifactContinuityError, OSError, RuntimeError, UnicodeError, ValueError):
        print("AOSP reproducibility comparison failed: evidence chains or retained artifact bytes do not match.", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
