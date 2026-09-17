"""Bind one completed AOSP runtime run to the exact adb trust evidence used.

This module validates already-produced JSON evidence only. It never executes adb,
launches Cuttlefish, mutates a device or promotes project status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

MAX_REPORT_BYTES = 16 * 1024 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class RuntimeTrustBundleError(ValueError):
    """Raised when AOSP runtime/tool evidence cannot be bound safely."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeTrustBundleError("Runtime trust JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_report(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute():
        raise RuntimeTrustBundleError("Runtime trust input path must be absolute.")
    if path.is_symlink() or not path.is_file():
        raise RuntimeTrustBundleError("Runtime trust input must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RuntimeTrustBundleError("Runtime trust input could not be read.") from exc
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise RuntimeTrustBundleError("Runtime trust input has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeTrustBundleError("Runtime trust input must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeTrustBundleError("Runtime trust input root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise RuntimeTrustBundleError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _validate_run(report: dict[str, object]) -> tuple[str, str]:
    if report.get("schema_version") != 1 or report.get("source") != "local_aosp_run_evidence_chain":
        raise RuntimeTrustBundleError("AOSP run evidence schema/source is invalid.")
    if report.get("scope") != "BUILD_AND_RUNTIME":
        raise RuntimeTrustBundleError("Runtime trust requires a completed BUILD_AND_RUNTIME run.")
    if (
        report.get("build_chain_complete") is not True
        or report.get("runtime_chain_complete") is not True
        or report.get("run_evidence_complete") is not True
    ):
        raise RuntimeTrustBundleError("AOSP runtime run evidence is incomplete.")
    if report.get("device_write_allowed") is not False:
        raise RuntimeTrustBundleError("AOSP runtime evidence violates the no-write boundary.")
    if report.get("physical_device_support_claimed") is not False or report.get("status_promotion_performed") is not False:
        raise RuntimeTrustBundleError("AOSP runtime evidence overclaims physical support or promotion.")
    run_digest = _hex64(report.get("run_evidence_sha256"), "run_evidence_sha256")
    fingerprint_digest = _hex64(report.get("build_fingerprint_sha256"), "build_fingerprint_sha256")
    return run_digest, fingerprint_digest


def _validate_capture(report: dict[str, object]) -> tuple[str, str, int]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_runtime_tool_evidence"
        or report.get("operation") != "READ_ONLY_LOCAL_TOOL_HASH"
        or report.get("purpose") != "CUTTLEFISH_RUNTIME_ADB"
        or report.get("tool_name") != "adb"
        or report.get("capture_complete") is not True
    ):
        raise RuntimeTrustBundleError("Captured adb evidence is invalid or incomplete.")
    if (
        report.get("executable") is not True
        or report.get("group_or_world_writable") is not False
        or report.get("canonical_path_required") is not True
        or report.get("tool_executed") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise RuntimeTrustBundleError("Captured adb evidence violates the read-only trust contract.")
    size = report.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise RuntimeTrustBundleError("Captured adb evidence size is invalid.")
    return _hex64(report.get("sha256"), "adb sha256"), _hex64(report.get("path_identity_sha256"), "adb path identity"), size


def _validate_verification(
    report: dict[str, object], *, expected_sha: str, expected_path: str, expected_size: int
) -> None:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_runtime_tool_verification"
        or report.get("operation") != "READ_ONLY_LOCAL_TOOL_REVERIFY"
        or report.get("purpose") != "CUTTLEFISH_RUNTIME_ADB"
        or report.get("tool_name") != "adb"
        or report.get("runtime_tool_unchanged") is not True
    ):
        raise RuntimeTrustBundleError("adb re-verification evidence is invalid or incomplete.")
    if report.get("tool_executed") is not False or report.get("device_write_allowed") is not False or report.get("status_promotion_performed") is not False:
        raise RuntimeTrustBundleError("adb re-verification violates the no-execution/no-write boundary.")
    if report.get("path_identity_sha256") != expected_path or report.get("size") != expected_size:
        raise RuntimeTrustBundleError("adb re-verification belongs to a different local tool identity.")
    if report.get("recorded_sha256") != expected_sha or report.get("observed_sha256") != expected_sha:
        raise RuntimeTrustBundleError("adb bytes changed across the runtime evidence window.")


def create_runtime_trust_bundle(
    run_path: Path,
    tool_path: Path,
    prelaunch_path: Path,
    post_path: Path,
) -> dict[str, object]:
    run, run_file_sha = _load_report(run_path)
    tool, tool_file_sha = _load_report(tool_path)
    prelaunch, pre_file_sha = _load_report(prelaunch_path)
    post, post_file_sha = _load_report(post_path)
    run_digest, fingerprint_digest = _validate_run(run)
    tool_sha, path_identity, tool_size = _validate_capture(tool)
    _validate_verification(prelaunch, expected_sha=tool_sha, expected_path=path_identity, expected_size=tool_size)
    _validate_verification(post, expected_sha=tool_sha, expected_path=path_identity, expected_size=tool_size)
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_runtime_trust_bundle",
        "scope": "CUTTLEFISH_BUILD_RUNTIME_AND_EXACT_ADB",
        "run_evidence_sha256": run_digest,
        "build_fingerprint_sha256": fingerprint_digest,
        "adb_sha256": tool_sha,
        "adb_path_identity_sha256": path_identity,
        "adb_size": tool_size,
        "report_file_sha256": {
            "aosp_run_evidence": run_file_sha,
            "runtime_tool_evidence": tool_file_sha,
            "runtime_tool_prelaunch_verification": pre_file_sha,
            "runtime_tool_post_verification": post_file_sha,
        },
        "runtime_tool_unchanged_across_evidence_window": True,
        "runtime_trust_chain_complete": True,
        "tool_capture_executed_adb": False,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This bundle proves exact local adb byte continuity around one completed Cuttlefish runtime evidence window.",
            "It does not prove physical-device compatibility, authorize phone writes, or satisfy beta hardware gates.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload["runtime_trust_bundle_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind one AOSP runtime run to exact read-only adb trust evidence")
    parser.add_argument("--run-evidence", required=True, type=Path)
    parser.add_argument("--tool-evidence", required=True, type=Path)
    parser.add_argument("--prelaunch", required=True, type=Path)
    parser.add_argument("--post", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = create_runtime_trust_bundle(args.run_evidence, args.tool_evidence, args.prelaunch, args.post)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (RuntimeTrustBundleError, OSError, ValueError):
        print("Runtime trust binding failed: use one complete AOSP runtime run and unchanged strict adb evidence.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
