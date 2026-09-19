"""Bind one completed SwirPhoneOS Cuttlefish runtime run to exact AOSP host-tool bytes.

This validator consumes already-produced JSON only. It never executes Cuttlefish
tools, adb, phone writes, flashing, root or status promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .cuttlefish_host_tool_evidence import EXPECTED_TOOLS, MAX_EVIDENCE_BYTES, MAX_TOOL_BYTES

MAX_REPORT_BYTES = 16 * 1024 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class CuttlefishHostToolTrustBundleError(ValueError):
    """Raised when Cuttlefish host-tool trust cannot be bound to one runtime run."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool trust JSON contains a duplicate key.")
        result[key] = value
    return result


def _load(path: Path, *, limit: int = MAX_REPORT_BYTES) -> tuple[dict[str, object], str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise CuttlefishHostToolTrustBundleError("Trust input must be an absolute regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CuttlefishHostToolTrustBundleError("Trust input could not be read.") from exc
    if not raw or len(raw) > limit:
        raise CuttlefishHostToolTrustBundleError("Trust input has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CuttlefishHostToolTrustBundleError("Trust input must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise CuttlefishHostToolTrustBundleError("Trust input root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise CuttlefishHostToolTrustBundleError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _validate_run(report: dict[str, object]) -> tuple[str, str, str, str]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_run_evidence_chain"
        or report.get("scope") != "BUILD_AND_RUNTIME"
        or report.get("build_chain_complete") is not True
        or report.get("runtime_chain_complete") is not True
        or report.get("run_evidence_complete") is not True
    ):
        raise CuttlefishHostToolTrustBundleError("AOSP run is not one complete build-and-runtime evidence chain.")
    if (
        report.get("device_write_allowed") is not False
        or report.get("physical_device_support_claimed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise CuttlefishHostToolTrustBundleError("AOSP run violates the no-write/no-promotion boundary.")
    commit = report.get("source_commit")
    if not isinstance(commit, str) or _HEX40.fullmatch(commit) is None:
        raise CuttlefishHostToolTrustBundleError("AOSP run source commit is invalid.")
    run_digest = _hex64(report.get("run_evidence_sha256"), "run_evidence_sha256")
    canonical = {k: v for k, v in report.items() if k not in {"run_evidence_sha256", "run_evidence_complete"}}
    if run_digest != _sha(canonical):
        raise CuttlefishHostToolTrustBundleError("AOSP run canonical digest is invalid.")
    workspace_digest = _hex64(report.get("workspace_sha256"), "workspace_sha256")
    fingerprint = report.get("build_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint or len(fingerprint) > 1024:
        raise CuttlefishHostToolTrustBundleError("AOSP run build fingerprint is invalid.")
    try:
        expected_fingerprint = hashlib.sha256(fingerprint.encode("ascii", "strict")).hexdigest()
    except UnicodeError as exc:
        raise CuttlefishHostToolTrustBundleError("AOSP run build fingerprint must be ASCII.") from exc
    fingerprint_digest = _hex64(report.get("build_fingerprint_sha256"), "build_fingerprint_sha256")
    if fingerprint_digest != expected_fingerprint:
        raise CuttlefishHostToolTrustBundleError("AOSP run build fingerprint digest is invalid.")
    return run_digest, workspace_digest, fingerprint_digest, commit


def _tool_records(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) != len(EXPECTED_TOOLS):
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool record set is incomplete.")
    out: list[dict[str, object]] = []
    expected_keys = {
        "name", "path_identity_sha256", "size", "sha256", "executable", "group_or_world_writable"
    }
    for item, name in zip(value, EXPECTED_TOOLS, strict=True):
        if not isinstance(item, dict) or set(item) != expected_keys or item.get("name") != name:
            raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool record is malformed or reordered.")
        size = item.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_TOOL_BYTES:
            raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool size is invalid.")
        if item.get("executable") is not True or item.get("group_or_world_writable") is not False:
            raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool permission evidence is invalid.")
        _hex64(item.get("path_identity_sha256"), "host-tool path identity")
        _hex64(item.get("sha256"), "host-tool sha256")
        out.append(item)
    return out


def _validate_capture(report: dict[str, object], expected_workspace: str) -> tuple[str, list[dict[str, object]]]:
    required = {
        "schema_version", "source", "operation", "purpose", "workspace_identity_sha256",
        "tool_count", "tools", "toolset_sha256", "tools_executed", "device_write_allowed",
        "status_promotion_performed", "physical_device_support_claimed", "capture_complete", "warnings",
    }
    if set(report) != required:
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool capture has unknown or missing fields.")
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_cuttlefish_host_tool_evidence"
        or report.get("operation") != "READ_ONLY_AOSP_CUTTLEFISH_TOOL_HASH"
        or report.get("purpose") != "EXACT_AOSP_CUTTLEFISH_LAUNCH_AND_STOP"
        or report.get("capture_complete") is not True
        or report.get("tools_executed") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
        or report.get("physical_device_support_claimed") is not False
    ):
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool capture violates the trust contract.")
    if report.get("workspace_identity_sha256") != expected_workspace:
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host tools belong to a different AOSP workspace.")
    tools = _tool_records(report.get("tools"))
    if report.get("tool_count") != len(EXPECTED_TOOLS):
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool count is invalid.")
    digest = _hex64(report.get("toolset_sha256"), "toolset_sha256")
    if digest != _sha(tools):
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool set digest is invalid.")
    warnings = report.get("warnings")
    if not isinstance(warnings, list) or len(warnings) < 2:
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool warnings are invalid.")
    return digest, tools


def _validate_verification(
    report: dict[str, object], *, expected_workspace: str, expected_toolset: str,
    expected_tools: list[dict[str, object]],
) -> None:
    required = {
        "schema_version", "source", "operation", "purpose", "workspace_identity_sha256",
        "tool_count", "toolset_sha256", "tools", "tools_unchanged", "tools_executed_by_verifier",
        "device_write_allowed", "status_promotion_performed", "physical_device_support_claimed",
    }
    if set(report) != required:
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool verification has unknown or missing fields.")
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_cuttlefish_host_tool_verification"
        or report.get("operation") != "READ_ONLY_AOSP_CUTTLEFISH_TOOL_REVERIFY"
        or report.get("purpose") != "EXACT_AOSP_CUTTLEFISH_LAUNCH_AND_STOP"
        or report.get("tools_unchanged") is not True
        or report.get("tools_executed_by_verifier") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
        or report.get("physical_device_support_claimed") is not False
    ):
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool verification violates the trust contract.")
    if report.get("workspace_identity_sha256") != expected_workspace:
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool verification workspace is inconsistent.")
    if report.get("tool_count") != len(EXPECTED_TOOLS) or report.get("toolset_sha256") != expected_toolset:
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool verification set identity is inconsistent.")
    tools = _tool_records(report.get("tools"))
    if tools != expected_tools or _sha(tools) != expected_toolset:
        raise CuttlefishHostToolTrustBundleError("Cuttlefish host-tool bytes changed across the runtime evidence window.")


def create_cuttlefish_host_tool_trust_bundle(
    run_path: Path, capture_path: Path, prelaunch_path: Path, postreview_path: Path,
) -> dict[str, object]:
    run, run_file_sha = _load(run_path)
    capture, capture_file_sha = _load(capture_path, limit=MAX_EVIDENCE_BYTES)
    prelaunch, prelaunch_file_sha = _load(prelaunch_path, limit=MAX_EVIDENCE_BYTES)
    postreview, postreview_file_sha = _load(postreview_path, limit=MAX_EVIDENCE_BYTES)

    run_digest, workspace_digest, fingerprint_digest, source_commit = _validate_run(run)
    toolset_digest, tools = _validate_capture(capture, workspace_digest)
    _validate_verification(prelaunch, expected_workspace=workspace_digest, expected_toolset=toolset_digest, expected_tools=tools)
    _validate_verification(postreview, expected_workspace=workspace_digest, expected_toolset=toolset_digest, expected_tools=tools)

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_cuttlefish_host_tool_trust_bundle",
        "scope": "EXACT_AOSP_BUILD_RUNTIME_AND_CUTTLEFISH_HOST_TOOLS",
        "source_commit": source_commit,
        "run_evidence_sha256": run_digest,
        "workspace_identity_sha256": workspace_digest,
        "build_fingerprint_sha256": fingerprint_digest,
        "toolset_sha256": toolset_digest,
        "tool_count": len(EXPECTED_TOOLS),
        "tools": tools,
        "report_file_sha256": {
            "aosp_run_evidence": run_file_sha,
            "cuttlefish_host_tool_evidence": capture_file_sha,
            "cuttlefish_host_tool_prelaunch_verification": prelaunch_file_sha,
            "cuttlefish_host_tool_postreview_verification": postreview_file_sha,
        },
        "host_tools_unchanged_across_runtime_review": True,
        "tools_executed_by_trust_validator": False,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "beta_gate_satisfied": False,
        "warnings": [
            "This bundle proves byte continuity only for exact AOSP-built launch_cvd/stop_cvd around one completed Cuttlefish runtime review.",
            "It does not prove physical-device compatibility, installation safety, hardware behavior or beta readiness.",
            "It never authorizes phone writes, flashing, root, release publication or project-status promotion.",
        ],
    }
    payload["cuttlefish_host_tool_trust_bundle_sha256"] = _sha(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind one exact AOSP runtime run to exact Cuttlefish host-tool byte continuity")
    parser.add_argument("--run-evidence", required=True, type=Path)
    parser.add_argument("--tool-evidence", required=True, type=Path)
    parser.add_argument("--prelaunch", required=True, type=Path)
    parser.add_argument("--postreview", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = create_cuttlefish_host_tool_trust_bundle(args.run_evidence, args.tool_evidence, args.prelaunch, args.postreview)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (CuttlefishHostToolTrustBundleError, OSError, RuntimeError, ValueError):
        print(
            "Cuttlefish host-tool trust binding failed: use one exact complete runtime run and unchanged strict host-tool evidence.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
