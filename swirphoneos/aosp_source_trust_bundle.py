"""Bind one AOSP run to exact clean pre/post-build Git source evidence.

This module validates existing evidence files only. It does not execute Git,
build Android, mutate the AOSP workspace, or touch a physical device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


class AospSourceTrustBundleError(ValueError):
    """Raised when build/run evidence cannot be bound to clean source state."""


MAX_REPORT_BYTES = 16 * 1024 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospSourceTrustBundleError("Source trust JSON contains a duplicate key.")
        result[key] = value
    return result


def _load(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute():
        raise AospSourceTrustBundleError("Source trust input paths must be absolute.")
    if path.is_symlink() or not path.is_file():
        raise AospSourceTrustBundleError("Source trust input must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AospSourceTrustBundleError("Source trust input could not be read.") from exc
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise AospSourceTrustBundleError("Source trust input has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospSourceTrustBundleError("Source trust input must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise AospSourceTrustBundleError("Source trust input root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise AospSourceTrustBundleError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _validate_run(report: dict[str, object]) -> tuple[str, str, str]:
    if report.get("schema_version") != 1 or report.get("source") != "local_aosp_run_evidence_chain":
        raise AospSourceTrustBundleError("AOSP run evidence identity is invalid.")
    if report.get("scope") not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}:
        raise AospSourceTrustBundleError("AOSP run evidence scope is invalid.")
    if report.get("build_chain_complete") is not True or report.get("run_evidence_complete") is not True:
        raise AospSourceTrustBundleError("AOSP build chain is incomplete.")
    if (
        report.get("device_write_allowed") is not False
        or report.get("physical_device_support_claimed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise AospSourceTrustBundleError("AOSP run evidence violates the no-write/no-promotion boundary.")
    source_commit = report.get("source_commit")
    if not isinstance(source_commit, str) or _HEX40.fullmatch(source_commit) is None:
        raise AospSourceTrustBundleError("AOSP run source commit is invalid.")
    run_digest = _hex64(report.get("run_evidence_sha256"), "run_evidence_sha256")
    canonical = {
        key: value
        for key, value in report.items()
        if key not in {"run_evidence_sha256", "run_evidence_complete"}
    }
    if _canonical_sha(canonical) != run_digest:
        raise AospSourceTrustBundleError("AOSP run evidence canonical digest is invalid.")
    workspace_sha = _hex64(report.get("workspace_sha256"), "workspace_sha256")
    file_hashes = report.get("report_file_sha256")
    if not isinstance(file_hashes, dict):
        raise AospSourceTrustBundleError("AOSP run evidence file-hash inventory is missing.")
    resolved_report_file_sha = _hex64(file_hashes.get("resolved_manifest"), "resolved manifest report file sha256")
    return run_digest, workspace_sha, resolved_report_file_sha


def _validate_resolved_manifest(report: dict[str, object]) -> tuple[str, int]:
    if (
        report.get("schema_version") != 1
        or report.get("all_projects_pinned") is not True
        or report.get("build_verified") is not False
        or report.get("boot_verified") is not False
    ):
        raise AospSourceTrustBundleError("Resolved-manifest evidence is invalid or overclaims runtime state.")
    digest = _hex64(report.get("sha256"), "resolved manifest sha256")
    count = report.get("project_count")
    unique = report.get("unique_path_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0 or unique != count:
        raise AospSourceTrustBundleError("Resolved-manifest project/path counts are invalid.")
    return digest, count


def _validate_source_report(
    report: dict[str, object], *, expected_manifest_sha: str, expected_project_count: int, expected_workspace_sha: str
) -> tuple[str, str, str, int, str]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_source_checkout_integrity"
        or report.get("operation") != "READ_ONLY_GIT_WORKTREE_VERIFICATION"
        or report.get("source_checkout_verified") is not True
        or report.get("all_project_heads_match") is not True
        or report.get("all_tracked_worktrees_clean") is not True
        or report.get("all_untracked_worktrees_clean") is not True
        or report.get("git_tool_executed_read_only") is not True
    ):
        raise AospSourceTrustBundleError("AOSP source checkout evidence is incomplete.")
    if (
        report.get("device_write_allowed") is not False
        or report.get("build_verified") is not False
        or report.get("boot_verified") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise AospSourceTrustBundleError("AOSP source checkout evidence violates the no-write/no-promotion boundary.")
    if report.get("workspace_identity_sha256") != expected_workspace_sha:
        raise AospSourceTrustBundleError("AOSP source evidence belongs to a different workspace.")
    if report.get("resolved_manifest_sha256") != expected_manifest_sha:
        raise AospSourceTrustBundleError("AOSP source evidence belongs to a different resolved manifest.")
    count = report.get("project_count")
    if count != expected_project_count or report.get("verified_project_count") != expected_project_count:
        raise AospSourceTrustBundleError("AOSP source evidence does not cover the complete manifest project set.")

    projects = report.get("projects")
    if not isinstance(projects, list) or len(projects) != expected_project_count:
        raise AospSourceTrustBundleError("AOSP source project inventory is incomplete.")
    seen: set[str] = set()
    canonical_projects: list[dict[str, str]] = []
    for item in projects:
        if not isinstance(item, dict) or set(item) != {
            "path", "revision", "head", "head_matches_manifest", "tracked_clean", "untracked_clean"
        }:
            raise AospSourceTrustBundleError("AOSP source project record is malformed.")
        path = item.get("path")
        revision = item.get("revision")
        head = item.get("head")
        if not isinstance(path, str) or not path or path in seen:
            raise AospSourceTrustBundleError("AOSP source project path is invalid or duplicated.")
        if not isinstance(revision, str) or _HEX40.fullmatch(revision) is None or head != revision:
            raise AospSourceTrustBundleError("AOSP source project HEAD/revision identity is invalid.")
        if item.get("head_matches_manifest") is not True or item.get("tracked_clean") is not True or item.get("untracked_clean") is not True:
            raise AospSourceTrustBundleError("AOSP source project is not proven exact and clean.")
        seen.add(path)
        canonical_projects.append({"path": path, "revision": revision, "head": str(head)})
    canonical_projects.sort(key=lambda item: item["path"])
    aggregate = _hex64(report.get("aggregate_state_sha256"), "aggregate_state_sha256")
    if _canonical_sha(canonical_projects) != aggregate:
        raise AospSourceTrustBundleError("AOSP source aggregate state digest is invalid.")

    git_tool = report.get("git_tool")
    if not isinstance(git_tool, dict) or set(git_tool) != {"size", "sha256", "path_identity_sha256"}:
        raise AospSourceTrustBundleError("Git tool identity is malformed.")
    size = git_tool.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise AospSourceTrustBundleError("Git tool size is invalid.")
    git_sha = _hex64(git_tool.get("sha256"), "git tool sha256")
    git_path = _hex64(git_tool.get("path_identity_sha256"), "git path identity sha256")

    evidence_digest = _hex64(report.get("source_evidence_sha256"), "source_evidence_sha256")
    canonical_report = {key: value for key, value in report.items() if key != "source_evidence_sha256"}
    if _canonical_sha(canonical_report) != evidence_digest:
        raise AospSourceTrustBundleError("AOSP source evidence canonical digest is invalid.")
    return evidence_digest, aggregate, git_sha, size, git_path


def create_source_trust_bundle(
    run_path: Path,
    resolved_manifest_evidence_path: Path,
    prebuild_source_path: Path,
    postbuild_source_path: Path,
) -> dict[str, object]:
    run, run_file_sha = _load(run_path)
    resolved, resolved_file_sha = _load(resolved_manifest_evidence_path)
    pre, pre_file_sha = _load(prebuild_source_path)
    post, post_file_sha = _load(postbuild_source_path)

    run_digest, workspace_sha, expected_resolved_file_sha = _validate_run(run)
    if resolved_file_sha != expected_resolved_file_sha:
        raise AospSourceTrustBundleError("Resolved-manifest evidence bytes differ from those bound by the AOSP run.")
    manifest_sha, project_count = _validate_resolved_manifest(resolved)
    pre_identity = _validate_source_report(
        pre,
        expected_manifest_sha=manifest_sha,
        expected_project_count=project_count,
        expected_workspace_sha=workspace_sha,
    )
    post_identity = _validate_source_report(
        post,
        expected_manifest_sha=manifest_sha,
        expected_project_count=project_count,
        expected_workspace_sha=workspace_sha,
    )
    if pre_identity[1:] != post_identity[1:]:
        raise AospSourceTrustBundleError("AOSP source or exact Git tool identity changed across the build evidence window.")

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_source_trust_bundle",
        "scope": "BUILD_WITH_EXACT_CLEAN_SOURCE_CONTINUITY",
        "run_evidence_sha256": run_digest,
        "resolved_manifest_sha256": manifest_sha,
        "workspace_identity_sha256": workspace_sha,
        "project_count": project_count,
        "aggregate_source_state_sha256": pre_identity[1],
        "git_sha256": pre_identity[2],
        "git_size": pre_identity[3],
        "git_path_identity_sha256": pre_identity[4],
        "prebuild_source_evidence_sha256": pre_identity[0],
        "postbuild_source_evidence_sha256": post_identity[0],
        "report_file_sha256": {
            "aosp_run_evidence": run_file_sha,
            "resolved_manifest_evidence": resolved_file_sha,
            "source_prebuild_evidence": pre_file_sha,
            "source_postbuild_evidence": post_file_sha,
        },
        "source_checkout_unchanged_across_build_window": True,
        "source_trust_chain_complete": True,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This bundle proves clean exact Git checkout continuity around one completed host-side AOSP build chain.",
            "It does not prove runtime boot, physical-device compatibility, installation safety, root support, or beta readiness.",
        ],
    }
    payload["source_trust_bundle_sha256"] = _canonical_sha(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind one completed AOSP run to exact clean pre/post-build source evidence")
    parser.add_argument("--run-evidence", required=True, type=Path)
    parser.add_argument("--resolved-manifest-evidence", required=True, type=Path)
    parser.add_argument("--source-pre", required=True, type=Path)
    parser.add_argument("--source-post", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = create_source_trust_bundle(
            args.run_evidence.resolve(),
            args.resolved_manifest_evidence.resolve(),
            args.source_pre.resolve(),
            args.source_post.resolve(),
        )
    except (AospSourceTrustBundleError, OSError, ValueError):
        print(
            "AOSP source trust binding failed: use one completed run plus unchanged exact clean source evidence.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
