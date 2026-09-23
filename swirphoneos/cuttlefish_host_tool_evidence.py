"""Read-only byte trust for the exact AOSP-built Cuttlefish host tools.

Android 17 installs the legacy ``launch_cvd``/``stop_cvd`` entry points as
symlinks in the Cuttlefish host bin directory. The collector accepts only
those expected in-tree aliases, resolves them to canonical regular files in
the same host bin directory, hashes the resolved bytes with inode/size/mtime
continuity checks, and emits no raw host path. Verification repeats that same
resolution and hashing and fails closed on any target drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

SCHEMA_VERSION = 1
EXPECTED_TOOLS = ("launch_cvd", "stop_cvd")
MAX_TOOL_BYTES = 512 * 1024 * 1024
MAX_EVIDENCE_BYTES = 256 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_CAPTURE_KEYS = {
    "schema_version", "source", "operation", "purpose",
    "workspace_identity_sha256", "tool_count", "tools", "toolset_sha256",
    "tools_executed", "device_write_allowed", "status_promotion_performed",
    "physical_device_support_claimed", "capture_complete", "warnings",
}
_TOOL_KEYS = {
    "name", "path_identity_sha256", "size", "sha256", "executable",
    "group_or_world_writable",
}


class CuttlefishHostToolEvidenceError(ValueError):
    """Raised when exact Cuttlefish host-tool evidence is unsafe or malformed."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CuttlefishHostToolEvidenceError("Cuttlefish host-tool evidence contains a duplicate JSON key.")
        result[key] = value
    return result


def _sha(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _workspace(path: Path) -> Path:
    if os.name != "posix":
        raise CuttlefishHostToolEvidenceError("Cuttlefish host-tool evidence is supported only on the Linux/POSIX AOSP builder.")
    if not path.is_absolute():
        raise CuttlefishHostToolEvidenceError("AOSP workspace must be absolute.")
    raw = str(path)
    if not raw or any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        raise CuttlefishHostToolEvidenceError("AOSP workspace path contains control characters.")
    try:
        root = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CuttlefishHostToolEvidenceError("AOSP workspace could not be resolved safely.") from exc
    if root != path or root == Path(root.anchor) or not root.is_dir():
        raise CuttlefishHostToolEvidenceError("AOSP workspace must already be canonical and must not be a filesystem root.")
    repo = root / ".repo"
    envsetup = root / "build" / "envsetup.sh"
    if repo.is_symlink() or not repo.is_dir() or envsetup.is_symlink() or not envsetup.is_file():
        raise CuttlefishHostToolEvidenceError("AOSP workspace identity is incomplete or aliased.")
    return root


def _tool_path(root: Path, name: str) -> Path:
    if name not in EXPECTED_TOOLS:
        raise CuttlefishHostToolEvidenceError("Unexpected Cuttlefish host tool.")
    bin_dir = root / "out" / "host" / "linux-x86" / "bin"
    try:
        canonical_bin = bin_dir.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CuttlefishHostToolEvidenceError("AOSP Cuttlefish host bin directory is missing.") from exc
    if canonical_bin != bin_dir or not canonical_bin.is_dir():
        raise CuttlefishHostToolEvidenceError("AOSP Cuttlefish host bin directory must be canonical.")
    path = bin_dir / name
    try:
        canonical = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CuttlefishHostToolEvidenceError(f"{name} is missing from the exact AOSP host output.") from exc
    if canonical.parent != canonical_bin:
        raise CuttlefishHostToolEvidenceError(f"{name} must resolve inside the exact AOSP host bin directory.")
    return canonical


def _metadata(path: Path) -> os.stat_result:
    try:
        meta = path.stat()
    except OSError as exc:
        raise CuttlefishHostToolEvidenceError("Cuttlefish host-tool metadata could not be inspected.") from exc
    if not stat.S_ISREG(meta.st_mode):
        raise CuttlefishHostToolEvidenceError("Cuttlefish host tool must be a regular file.")
    if meta.st_size <= 0 or meta.st_size > MAX_TOOL_BYTES:
        raise CuttlefishHostToolEvidenceError("Cuttlefish host-tool size is outside the accepted bound.")
    if not os.access(path, os.X_OK):
        raise CuttlefishHostToolEvidenceError("Cuttlefish host tool is not executable by the builder account.")
    if meta.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise CuttlefishHostToolEvidenceError("Cuttlefish host tool must not be group/world writable.")
    return meta


def _identity(meta: os.stat_result) -> tuple[int, int, int, int]:
    return (meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns)


def _hash_stable(path: Path, expected: os.stat_result) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise CuttlefishHostToolEvidenceError("Cuttlefish host-tool bytes could not be opened safely.") from exc
    digest = hashlib.sha256()
    total = 0
    try:
        opened = os.fstat(fd)
        if _identity(opened) != _identity(expected) or not stat.S_ISREG(opened.st_mode):
            raise CuttlefishHostToolEvidenceError("Cuttlefish host tool changed before hashing.")
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > expected.st_size:
                raise CuttlefishHostToolEvidenceError("Cuttlefish host tool grew while hashing.")
            digest.update(chunk)
        closed_state = os.fstat(fd)
    except OSError as exc:
        raise CuttlefishHostToolEvidenceError("Cuttlefish host-tool bytes could not be read safely.") from exc
    finally:
        os.close(fd)
    try:
        after = path.stat()
    except OSError as exc:
        raise CuttlefishHostToolEvidenceError("Cuttlefish host tool disappeared after hashing.") from exc
    if total != expected.st_size or _identity(closed_state) != _identity(expected) or _identity(after) != _identity(expected):
        raise CuttlefishHostToolEvidenceError("Cuttlefish host tool changed while hashing.")
    return digest.hexdigest()


def _capture_one(root: Path, name: str) -> dict[str, object]:
    path = _tool_path(root, name)
    meta = _metadata(path)
    return {
        "name": name,
        "path_identity_sha256": hashlib.sha256(str(path).encode("utf-8")).hexdigest(),
        "size": meta.st_size,
        "sha256": _hash_stable(path, meta),
        "executable": True,
        "group_or_world_writable": False,
    }


def capture_host_tools(workspace: Path) -> dict[str, object]:
    root = _workspace(workspace)
    tools = [_capture_one(root, name) for name in EXPECTED_TOOLS]
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source": "local_cuttlefish_host_tool_evidence",
        "operation": "READ_ONLY_AOSP_CUTTLEFISH_TOOL_HASH",
        "purpose": "EXACT_AOSP_CUTTLEFISH_LAUNCH_AND_STOP",
        "workspace_identity_sha256": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        "tool_count": len(tools),
        "tools": tools,
        "toolset_sha256": _sha(tools),
        "tools_executed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "physical_device_support_claimed": False,
        "capture_complete": True,
        "warnings": [
            "This report hashes only the exact AOSP-built launch_cvd and stop_cvd host entry points after resolving in-bin aliases; it does not execute them.",
            "Matching host-tool bytes do not prove Android boot, app runtime, physical-device support or beta readiness.",
            "No phone write, flash, root, release publication or status promotion is authorized by this evidence.",
        ],
    }
    return payload


def load_host_tool_evidence(path: Path) -> dict[str, object]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise CuttlefishHostToolEvidenceError("Host-tool evidence must be an absolute regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CuttlefishHostToolEvidenceError("Host-tool evidence could not be read.") from exc
    if not raw or len(raw) > MAX_EVIDENCE_BYTES:
        raise CuttlefishHostToolEvidenceError("Host-tool evidence has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CuttlefishHostToolEvidenceError("Host-tool evidence must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise CuttlefishHostToolEvidenceError("Host-tool evidence root must be an object.")
    return value


def _validate_tool_record(item: object, expected_name: str) -> dict[str, object]:
    if not isinstance(item, dict) or set(item) != _TOOL_KEYS or item.get("name") != expected_name:
        raise CuttlefishHostToolEvidenceError("Host-tool record shape or ordering is invalid.")
    if item.get("executable") is not True or item.get("group_or_world_writable") is not False:
        raise CuttlefishHostToolEvidenceError("Host-tool permission evidence is invalid.")
    size = item.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_TOOL_BYTES:
        raise CuttlefishHostToolEvidenceError("Host-tool evidence size is invalid.")
    for field in ("path_identity_sha256", "sha256"):
        value = item.get(field)
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            raise CuttlefishHostToolEvidenceError(f"Host-tool {field} is invalid.")
    return item


def validate_capture(report: dict[str, object]) -> list[dict[str, object]]:
    if set(report) != _CAPTURE_KEYS:
        raise CuttlefishHostToolEvidenceError("Host-tool capture contains unknown or missing fields.")
    if (
        report.get("schema_version") != SCHEMA_VERSION
        or report.get("source") != "local_cuttlefish_host_tool_evidence"
        or report.get("operation") != "READ_ONLY_AOSP_CUTTLEFISH_TOOL_HASH"
        or report.get("purpose") != "EXACT_AOSP_CUTTLEFISH_LAUNCH_AND_STOP"
        or report.get("capture_complete") is not True
        or report.get("tools_executed") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
        or report.get("physical_device_support_claimed") is not False
    ):
        raise CuttlefishHostToolEvidenceError("Host-tool capture violates the read-only trust contract.")
    workspace_identity = report.get("workspace_identity_sha256")
    if not isinstance(workspace_identity, str) or _HEX64.fullmatch(workspace_identity) is None:
        raise CuttlefishHostToolEvidenceError("Host-tool workspace identity is invalid.")
    tools = report.get("tools")
    if not isinstance(tools, list) or report.get("tool_count") != len(EXPECTED_TOOLS) or len(tools) != len(EXPECTED_TOOLS):
        raise CuttlefishHostToolEvidenceError("Host-tool capture does not contain the exact reviewed tool set.")
    normalized = [_validate_tool_record(item, name) for item, name in zip(tools, EXPECTED_TOOLS, strict=True)]
    digest = report.get("toolset_sha256")
    if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None or digest != _sha(normalized):
        raise CuttlefishHostToolEvidenceError("Host-tool set digest is invalid.")
    warnings = report.get("warnings")
    if not isinstance(warnings, list) or len(warnings) < 2 or any(not isinstance(item, str) or not item for item in warnings):
        raise CuttlefishHostToolEvidenceError("Host-tool capture warnings are invalid.")
    return normalized


def verify_host_tools(workspace: Path, evidence: dict[str, object]) -> dict[str, object]:
    recorded = validate_capture(evidence)
    current = capture_host_tools(workspace)
    current_tools = validate_capture(current)
    if current["workspace_identity_sha256"] != evidence["workspace_identity_sha256"]:
        raise CuttlefishHostToolEvidenceError("AOSP workspace identity changed after host-tool capture.")
    if current_tools != recorded or current["toolset_sha256"] != evidence["toolset_sha256"]:
        raise CuttlefishHostToolEvidenceError("Cuttlefish host tools changed after trust capture.")
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "local_cuttlefish_host_tool_verification",
        "operation": "READ_ONLY_AOSP_CUTTLEFISH_TOOL_REVERIFY",
        "purpose": "EXACT_AOSP_CUTTLEFISH_LAUNCH_AND_STOP",
        "workspace_identity_sha256": evidence["workspace_identity_sha256"],
        "tool_count": len(EXPECTED_TOOLS),
        "toolset_sha256": evidence["toolset_sha256"],
        "tools": current_tools,
        "tools_unchanged": True,
        "tools_executed_by_verifier": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "physical_device_support_claimed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only exact AOSP Cuttlefish launch/stop host-tool byte evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture", help="Hash exact AOSP-built launch_cvd and stop_cvd without executing them")
    capture.add_argument("--workspace", required=True, type=Path)
    verify = sub.add_parser("verify", help="Re-hash exact AOSP-built Cuttlefish host tools and compare to evidence")
    verify.add_argument("--workspace", required=True, type=Path)
    verify.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        workspace = args.workspace
        if args.command == "capture":
            result = capture_host_tools(workspace)
        else:
            result = verify_host_tools(workspace, load_host_tool_evidence(args.evidence))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (CuttlefishHostToolEvidenceError, OSError, RuntimeError, ValueError):
        print(
            "Cuttlefish host-tool evidence failed: require canonical untampered AOSP launch_cvd/stop_cvd output and strict evidence.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
