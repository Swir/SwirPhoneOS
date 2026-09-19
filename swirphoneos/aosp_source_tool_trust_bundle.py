"""Bind one completed AOSP run to exact repo/git source-sync tool bytes.

This module validates already-produced JSON evidence only. It never executes
repo/git, synchronizes AOSP, builds Android, launches Cuttlefish, mutates a
phone, or promotes project status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .aosp_source_tool_evidence import (
    AospSourceToolEvidenceError,
    EXPECTED_TOOLS,
    validate_capture,
    validate_verification,
)

MAX_REPORT_BYTES = 16 * 1024 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class AospSourceToolTrustBundleError(ValueError):
    """Raised when one AOSP run cannot be bound to exact source-tool bytes."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospSourceToolTrustBundleError("Source-tool trust input contains a duplicate JSON key.")
        result[key] = value
    return result


def _load_report(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise AospSourceToolTrustBundleError("Source-tool trust input must be an absolute regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AospSourceToolTrustBundleError("Source-tool trust input could not be read.") from exc
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise AospSourceToolTrustBundleError("Source-tool trust input has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospSourceToolTrustBundleError("Source-tool trust input must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise AospSourceToolTrustBundleError("Source-tool trust input root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise AospSourceToolTrustBundleError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _validate_run(report: dict[str, object]) -> tuple[str, str, str]:
    if report.get("schema_version") != 1 or report.get("source") != "local_aosp_run_evidence_chain":
        raise AospSourceToolTrustBundleError("AOSP run evidence schema/source is invalid.")
    if report.get("scope") not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}:
        raise AospSourceToolTrustBundleError("Source-tool trust requires a completed AOSP build run.")
    if report.get("build_chain_complete") is not True or report.get("run_evidence_complete") is not True:
        raise AospSourceToolTrustBundleError("AOSP build run evidence is incomplete.")
    if report.get("device_write_allowed") is not False:
        raise AospSourceToolTrustBundleError("AOSP run evidence violates the no-write boundary.")
    if report.get("physical_device_support_claimed") is not False or report.get("status_promotion_performed") is not False:
        raise AospSourceToolTrustBundleError("AOSP run evidence overclaims physical support or project promotion.")
    source_commit = report.get("source_commit")
    if not isinstance(source_commit, str) or _HEX40.fullmatch(source_commit) is None:
        raise AospSourceToolTrustBundleError("AOSP run source commit is invalid.")
    run_digest = _hex64(report.get("run_evidence_sha256"), "run_evidence_sha256")
    canonical = {key: value for key, value in report.items() if key not in {"run_evidence_sha256", "run_evidence_complete"}}
    expected = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    if run_digest != expected:
        raise AospSourceToolTrustBundleError("AOSP run evidence canonical digest is invalid.")
    return run_digest, source_commit, str(report["scope"])


def create_source_tool_trust_bundle(
    run_path: Path,
    tool_path: Path,
    post_sync_path: Path,
    post_build_path: Path,
) -> dict[str, object]:
    run, run_file_sha = _load_report(run_path)
    capture, capture_file_sha = _load_report(tool_path)
    post_sync, post_sync_file_sha = _load_report(post_sync_path)
    post_build, post_build_file_sha = _load_report(post_build_path)

    run_digest, source_commit, scope = _validate_run(run)
    try:
        tools = validate_capture(capture)
        toolset_digest = _hex64(capture.get("toolset_sha256"), "source-tool toolset_sha256")
        validate_verification(post_sync, tools, toolset_digest)
        validate_verification(post_build, tools, toolset_digest)
    except (AospSourceToolEvidenceError, ValueError) as exc:
        raise AospSourceToolTrustBundleError("Source-tool evidence is invalid or changed across the AOSP build window.") from exc

    tool_hashes = {str(item["name"]): str(item["sha256"]) for item in tools}
    if set(tool_hashes) != set(EXPECTED_TOOLS):
        raise AospSourceToolTrustBundleError("Source-tool evidence does not cover the exact repo/git set.")

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_source_tool_trust_bundle",
        "scope": "AOSP_BUILD_AND_EXACT_REPO_GIT",
        "aosp_run_scope": scope,
        "source_commit": source_commit,
        "run_evidence_sha256": run_digest,
        "toolset_sha256": toolset_digest,
        "tool_sha256": tool_hashes,
        "report_file_sha256": {
            "aosp_run_evidence": run_file_sha,
            "aosp_source_tool_evidence": capture_file_sha,
            "aosp_source_tool_postsync_verification": post_sync_file_sha,
            "aosp_source_tool_postbuild_verification": post_build_file_sha,
        },
        "source_tools_unchanged_across_sync_and_build": True,
        "source_tool_trust_chain_complete": True,
        "source_tools_executed_by_trust_collector": False,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This bundle proves exact repo/git byte continuity around one completed AOSP source-sync/build evidence window.",
            "It does not prove Android boot, physical-device compatibility, authorize device writes, or satisfy beta hardware gates.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload["source_tool_trust_bundle_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind one completed AOSP build run to exact repo/git trust evidence")
    parser.add_argument("--run-evidence", required=True, type=Path)
    parser.add_argument("--tool-evidence", required=True, type=Path)
    parser.add_argument("--post-sync", required=True, type=Path)
    parser.add_argument("--post-build", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = create_source_tool_trust_bundle(
            args.run_evidence,
            args.tool_evidence,
            args.post_sync,
            args.post_build,
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (AospSourceToolTrustBundleError, OSError, RuntimeError, ValueError):
        print(
            "AOSP source-tool trust binding failed: use one complete build run and unchanged strict repo/git evidence.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
