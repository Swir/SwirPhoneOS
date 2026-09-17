"""Read-only trust evidence for the adb binary used by Cuttlefish runtime checks.

The collector hashes one explicitly selected local adb executable without running
it. Verification re-reads the same canonical executable and fails closed if its
path identity, size, permissions or bytes changed. It performs no Android SDK
command, device I/O, install, flash, reboot, root or project-state promotion.
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
EXPECTED_TOOL_NAME = "adb"
MAX_TOOL_BYTES = 256 * 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class RuntimeToolEvidenceError(ValueError):
    """Raised when a runtime-tool trust request or evidence file is unsafe."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeToolEvidenceError("Runtime-tool evidence JSON contains a duplicate key.")
        result[key] = value
    return result


def _canonical_tool(path: Path) -> tuple[Path, os.stat_result]:
    if not path.is_absolute():
        raise RuntimeToolEvidenceError("Runtime tool path must be absolute.")
    try:
        canonical = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RuntimeToolEvidenceError("Runtime tool path could not be resolved safely.") from exc
    if canonical != path:
        raise RuntimeToolEvidenceError("Runtime tool path must already be canonical and contain no aliases.")
    if path.is_symlink():
        raise RuntimeToolEvidenceError("Runtime tool must not be a symlink.")
    try:
        metadata = canonical.stat()
    except OSError as exc:
        raise RuntimeToolEvidenceError("Runtime tool metadata could not be inspected.") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeToolEvidenceError("Runtime tool must be a regular file.")
    if canonical.name != EXPECTED_TOOL_NAME:
        raise RuntimeToolEvidenceError("Runtime tool must be the explicitly selected adb executable.")
    if metadata.st_size <= 0 or metadata.st_size > MAX_TOOL_BYTES:
        raise RuntimeToolEvidenceError("Runtime tool size is outside the accepted bound.")
    if not os.access(canonical, os.X_OK):
        raise RuntimeToolEvidenceError("Runtime tool is not executable by the current builder account.")
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeToolEvidenceError("Runtime tool must not be group/world writable.")
    return canonical, metadata


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RuntimeToolEvidenceError("Runtime tool bytes could not be read safely.") from exc
    return digest.hexdigest()


def capture_runtime_tool(path: Path) -> dict[str, object]:
    """Hash one canonical local adb executable without executing it."""
    canonical, metadata = _canonical_tool(path)
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "local_runtime_tool_evidence",
        "operation": "READ_ONLY_LOCAL_TOOL_HASH",
        "purpose": "CUTTLEFISH_RUNTIME_ADB",
        "tool_name": EXPECTED_TOOL_NAME,
        "path_identity_sha256": hashlib.sha256(str(canonical).encode("utf-8")).hexdigest(),
        "size": metadata.st_size,
        "sha256": _sha256_file(canonical),
        "executable": True,
        "group_or_world_writable": False,
        "canonical_path_required": True,
        "tool_executed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This report proves only the exact local adb file bytes selected for runtime checks.",
            "Capturing this report does not execute adb or contact an Android/Cuttlefish device.",
            "A matching adb binary does not prove a successful build, boot, app runtime or physical-device support.",
        ],
        "capture_complete": True,
    }


def load_runtime_tool_evidence(path: Path) -> dict[str, object]:
    if not path.is_absolute():
        raise RuntimeToolEvidenceError("Runtime-tool evidence path must be absolute.")
    if path.is_symlink() or not path.is_file():
        raise RuntimeToolEvidenceError("Runtime-tool evidence must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RuntimeToolEvidenceError("Runtime-tool evidence could not be read.") from exc
    if not raw or len(raw) > MAX_EVIDENCE_BYTES:
        raise RuntimeToolEvidenceError("Runtime-tool evidence has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeToolEvidenceError("Runtime-tool evidence must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeToolEvidenceError("Runtime-tool evidence root must be an object.")
    return value


def _validate_recorded_evidence(evidence: dict[str, object]) -> None:
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeToolEvidenceError("Runtime-tool evidence schema is unsupported.")
    if evidence.get("source") != "local_runtime_tool_evidence":
        raise RuntimeToolEvidenceError("Runtime-tool evidence source is invalid.")
    if evidence.get("operation") != "READ_ONLY_LOCAL_TOOL_HASH":
        raise RuntimeToolEvidenceError("Runtime-tool evidence operation is invalid.")
    if evidence.get("purpose") != "CUTTLEFISH_RUNTIME_ADB" or evidence.get("tool_name") != EXPECTED_TOOL_NAME:
        raise RuntimeToolEvidenceError("Runtime-tool evidence purpose/tool identity is invalid.")
    if evidence.get("capture_complete") is not True:
        raise RuntimeToolEvidenceError("Runtime-tool evidence is incomplete.")
    if evidence.get("executable") is not True or evidence.get("group_or_world_writable") is not False:
        raise RuntimeToolEvidenceError("Runtime-tool evidence permission state is invalid.")
    if evidence.get("canonical_path_required") is not True or evidence.get("tool_executed") is not False:
        raise RuntimeToolEvidenceError("Runtime-tool evidence violates the read-only canonical-path contract.")
    if evidence.get("device_write_allowed") is not False or evidence.get("status_promotion_performed") is not False:
        raise RuntimeToolEvidenceError("Runtime-tool evidence violates the no-write/no-promotion boundary.")
    size = evidence.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > MAX_TOOL_BYTES:
        raise RuntimeToolEvidenceError("Runtime-tool evidence size is invalid.")
    for field in ("path_identity_sha256", "sha256"):
        value = evidence.get(field)
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            raise RuntimeToolEvidenceError(f"Runtime-tool evidence {field} is invalid.")


def verify_runtime_tool(path: Path, evidence: dict[str, object]) -> dict[str, object]:
    """Re-hash the selected adb and require exact continuity with captured evidence."""
    _validate_recorded_evidence(evidence)
    current = capture_runtime_tool(path)
    compared = ("tool_name", "path_identity_sha256", "size", "sha256")
    if any(current.get(field) != evidence.get(field) for field in compared):
        raise RuntimeToolEvidenceError("Runtime tool no longer matches the captured trust evidence.")
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "local_runtime_tool_verification",
        "operation": "READ_ONLY_LOCAL_TOOL_REVERIFY",
        "purpose": "CUTTLEFISH_RUNTIME_ADB",
        "tool_name": EXPECTED_TOOL_NAME,
        "path_identity_sha256": current["path_identity_sha256"],
        "size": current["size"],
        "recorded_sha256": evidence["sha256"],
        "observed_sha256": current["sha256"],
        "runtime_tool_unchanged": True,
        "tool_executed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SwirPhoneOS read-only Cuttlefish adb trust evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture", help="Hash one canonical local adb executable without running it")
    capture.add_argument("--adb", required=True, type=Path)
    verify = sub.add_parser("verify", help="Re-hash adb and compare it with a captured evidence file")
    verify.add_argument("--adb", required=True, type=Path)
    verify.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            result = capture_runtime_tool(args.adb)
        else:
            result = verify_runtime_tool(args.adb, load_runtime_tool_evidence(args.evidence))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (RuntimeToolEvidenceError, OSError, ValueError):
        print("Runtime tool evidence failed: use one canonical trusted local adb executable and untampered evidence.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
