"""Read-only byte trust for the exact host tools used to synchronize AOSP sources.

The collector resolves the `repo` and `git` commands selected by PATH, hashes the
canonical executable targets without running them, and records only hashed path
identities. Verification repeats the same lookup and fails closed on path,
permission, metadata, or byte drift. It performs no source sync, build, device I/O,
flash, root, release publication, or project-status promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
from typing import Any

SCHEMA_VERSION = 1
EXPECTED_TOOLS = ("repo", "git")
MAX_TOOL_BYTES = 256 * 1024 * 1024
MAX_EVIDENCE_BYTES = 256 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_CAPTURE_KEYS = {
    "schema_version", "source", "operation", "purpose", "tool_count", "tools",
    "toolset_sha256", "tools_executed", "device_write_allowed",
    "status_promotion_performed", "physical_device_support_claimed",
    "capture_complete", "warnings",
}
_TOOL_KEYS = {
    "name", "lookup_path_identity_sha256", "canonical_path_identity_sha256",
    "lookup_is_symlink", "size", "sha256", "executable",
    "group_or_world_writable",
}
_VERIFICATION_KEYS = {
    "schema_version", "source", "operation", "purpose", "tool_count", "tools",
    "toolset_sha256", "tools_unchanged", "tools_executed_by_verifier",
    "device_write_allowed", "status_promotion_performed",
    "physical_device_support_claimed",
}


class AospSourceToolEvidenceError(ValueError):
    """Raised when source-tool trust evidence is unsafe, ambiguous, or malformed."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospSourceToolEvidenceError("AOSP source-tool evidence contains a duplicate JSON key.")
        result[key] = value
    return result


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _path_identity(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _lookup_tool(name: str) -> tuple[Path, Path, os.stat_result, bool]:
    if os.name != "posix":
        raise AospSourceToolEvidenceError("AOSP source-tool trust capture is supported only on the Linux/POSIX builder.")
    if name not in EXPECTED_TOOLS:
        raise AospSourceToolEvidenceError("Unexpected AOSP source tool.")
    resolved_lookup = shutil.which(name)
    if not resolved_lookup:
        raise AospSourceToolEvidenceError(f"Required source tool {name} was not found on PATH.")
    lookup = Path(resolved_lookup)
    if not lookup.is_absolute():
        raise AospSourceToolEvidenceError("PATH-selected source tool must resolve to an absolute lookup path.")
    raw_lookup = str(lookup)
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw_lookup):
        raise AospSourceToolEvidenceError("Source-tool lookup path contains control characters.")
    try:
        lookup_meta = lookup.lstat()
    except OSError as exc:
        raise AospSourceToolEvidenceError("Source-tool lookup metadata could not be inspected.") from exc
    if not (stat.S_ISREG(lookup_meta.st_mode) or stat.S_ISLNK(lookup_meta.st_mode)):
        raise AospSourceToolEvidenceError("PATH-selected source tool must be a regular file or symlink to one.")
    lookup_is_symlink = stat.S_ISLNK(lookup_meta.st_mode)
    try:
        canonical = lookup.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AospSourceToolEvidenceError("Source-tool canonical target could not be resolved safely.") from exc
    if not canonical.is_absolute() or canonical.name != name:
        raise AospSourceToolEvidenceError("Source-tool canonical target identity is unexpected.")
    try:
        meta = canonical.stat()
    except OSError as exc:
        raise AospSourceToolEvidenceError("Source-tool canonical metadata could not be inspected.") from exc
    if not stat.S_ISREG(meta.st_mode):
        raise AospSourceToolEvidenceError("Source-tool canonical target must be a regular file.")
    if meta.st_size <= 0 or meta.st_size > MAX_TOOL_BYTES:
        raise AospSourceToolEvidenceError("Source-tool size is outside the accepted bound.")
    if not os.access(canonical, os.X_OK):
        raise AospSourceToolEvidenceError("Source tool is not executable by the builder account.")
    if meta.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise AospSourceToolEvidenceError("Source tool must not be group/world writable.")
    return lookup, canonical, meta, lookup_is_symlink


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
        raise AospSourceToolEvidenceError("Source-tool bytes could not be opened safely.") from exc
    digest = hashlib.sha256()
    total = 0
    try:
        opened = os.fstat(fd)
        if _identity(opened) != _identity(expected) or not stat.S_ISREG(opened.st_mode):
            raise AospSourceToolEvidenceError("Source tool changed before hashing.")
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > expected.st_size:
                raise AospSourceToolEvidenceError("Source tool grew while hashing.")
            digest.update(chunk)
        closed_state = os.fstat(fd)
    except OSError as exc:
        raise AospSourceToolEvidenceError("Source-tool bytes could not be read safely.") from exc
    finally:
        os.close(fd)
    try:
        after = path.stat()
    except OSError as exc:
        raise AospSourceToolEvidenceError("Source tool disappeared after hashing.") from exc
    if total != expected.st_size or _identity(closed_state) != _identity(expected) or _identity(after) != _identity(expected):
        raise AospSourceToolEvidenceError("Source tool changed while hashing.")
    return digest.hexdigest()


def _capture_one(name: str) -> dict[str, object]:
    lookup, canonical, meta, lookup_is_symlink = _lookup_tool(name)
    return {
        "name": name,
        "lookup_path_identity_sha256": _path_identity(lookup),
        "canonical_path_identity_sha256": _path_identity(canonical),
        "lookup_is_symlink": lookup_is_symlink,
        "size": meta.st_size,
        "sha256": _hash_stable(canonical, meta),
        "executable": True,
        "group_or_world_writable": False,
    }


def capture_source_tools() -> dict[str, object]:
    """Hash the PATH-selected repo/git executable bytes without running either tool."""
    tools = [_capture_one(name) for name in EXPECTED_TOOLS]
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "local_aosp_source_tool_evidence",
        "operation": "READ_ONLY_AOSP_SOURCE_TOOL_HASH",
        "purpose": "PINNED_AOSP_REPO_GIT_SOURCE_SYNC",
        "tool_count": len(tools),
        "tools": tools,
        "toolset_sha256": _sha(tools),
        "tools_executed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "physical_device_support_claimed": False,
        "capture_complete": True,
        "warnings": [
            "This report hashes only the PATH-selected repo and git executable bytes; it does not run source-sync commands.",
            "Matching source-tool bytes do not prove a successful source sync, Android build, boot, physical-device support, or beta readiness.",
            "No phone write, flash, root, release publication, or project-status promotion is authorized by this evidence.",
        ],
    }


def load_source_tool_evidence(path: Path) -> dict[str, object]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise AospSourceToolEvidenceError("Source-tool evidence must be an absolute regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AospSourceToolEvidenceError("Source-tool evidence could not be read.") from exc
    if not raw or len(raw) > MAX_EVIDENCE_BYTES:
        raise AospSourceToolEvidenceError("Source-tool evidence has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospSourceToolEvidenceError("Source-tool evidence must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise AospSourceToolEvidenceError("Source-tool evidence root must be an object.")
    return value


def _validate_tool_record(item: object, expected_name: str) -> dict[str, object]:
    if not isinstance(item, dict) or set(item) != _TOOL_KEYS or item.get("name") != expected_name:
        raise AospSourceToolEvidenceError("Source-tool record shape or ordering is invalid.")
    if item.get("executable") is not True or item.get("group_or_world_writable") is not False:
        raise AospSourceToolEvidenceError("Source-tool permission evidence is invalid.")
    if not isinstance(item.get("lookup_is_symlink"), bool):
        raise AospSourceToolEvidenceError("Source-tool lookup alias evidence is invalid.")
    size = item.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_TOOL_BYTES:
        raise AospSourceToolEvidenceError("Source-tool evidence size is invalid.")
    for field in ("lookup_path_identity_sha256", "canonical_path_identity_sha256", "sha256"):
        value = item.get(field)
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            raise AospSourceToolEvidenceError(f"Source-tool {field} is invalid.")
    return item


def validate_capture(report: dict[str, object]) -> list[dict[str, object]]:
    if set(report) != _CAPTURE_KEYS:
        raise AospSourceToolEvidenceError("Source-tool capture contains unknown or missing fields.")
    if (
        report.get("schema_version") != SCHEMA_VERSION
        or report.get("source") != "local_aosp_source_tool_evidence"
        or report.get("operation") != "READ_ONLY_AOSP_SOURCE_TOOL_HASH"
        or report.get("purpose") != "PINNED_AOSP_REPO_GIT_SOURCE_SYNC"
        or report.get("capture_complete") is not True
        or report.get("tools_executed") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
        or report.get("physical_device_support_claimed") is not False
    ):
        raise AospSourceToolEvidenceError("Source-tool capture violates the read-only trust contract.")
    tools = report.get("tools")
    if not isinstance(tools, list) or report.get("tool_count") != len(EXPECTED_TOOLS) or len(tools) != len(EXPECTED_TOOLS):
        raise AospSourceToolEvidenceError("Source-tool capture does not contain the exact reviewed tool set.")
    normalized = [_validate_tool_record(item, name) for item, name in zip(tools, EXPECTED_TOOLS, strict=True)]
    digest = report.get("toolset_sha256")
    if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None or digest != _sha(normalized):
        raise AospSourceToolEvidenceError("Source-tool set digest is invalid.")
    warnings = report.get("warnings")
    if not isinstance(warnings, list) or len(warnings) < 2 or any(not isinstance(item, str) or not item for item in warnings):
        raise AospSourceToolEvidenceError("Source-tool capture warnings are invalid.")
    return normalized


def validate_verification(report: dict[str, object], expected_tools: list[dict[str, object]], expected_digest: str) -> None:
    if set(report) != _VERIFICATION_KEYS:
        raise AospSourceToolEvidenceError("Source-tool verification contains unknown or missing fields.")
    if (
        report.get("schema_version") != SCHEMA_VERSION
        or report.get("source") != "local_aosp_source_tool_verification"
        or report.get("operation") != "READ_ONLY_AOSP_SOURCE_TOOL_REVERIFY"
        or report.get("purpose") != "PINNED_AOSP_REPO_GIT_SOURCE_SYNC"
        or report.get("tools_unchanged") is not True
        or report.get("tools_executed_by_verifier") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
        or report.get("physical_device_support_claimed") is not False
    ):
        raise AospSourceToolEvidenceError("Source-tool verification violates the read-only trust contract.")
    tools = report.get("tools")
    if not isinstance(tools, list) or report.get("tool_count") != len(EXPECTED_TOOLS):
        raise AospSourceToolEvidenceError("Source-tool verification has an invalid tool count.")
    normalized = [_validate_tool_record(item, name) for item, name in zip(tools, EXPECTED_TOOLS, strict=True)]
    if normalized != expected_tools or report.get("toolset_sha256") != expected_digest:
        raise AospSourceToolEvidenceError("Source-tool verification belongs to different tool bytes or path identities.")


def verify_source_tools(evidence: dict[str, object]) -> dict[str, object]:
    recorded = validate_capture(evidence)
    current = capture_source_tools()
    current_tools = validate_capture(current)
    if current_tools != recorded or current["toolset_sha256"] != evidence["toolset_sha256"]:
        raise AospSourceToolEvidenceError("AOSP source tools changed after trust capture.")
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "local_aosp_source_tool_verification",
        "operation": "READ_ONLY_AOSP_SOURCE_TOOL_REVERIFY",
        "purpose": "PINNED_AOSP_REPO_GIT_SOURCE_SYNC",
        "tool_count": len(EXPECTED_TOOLS),
        "tools": current_tools,
        "toolset_sha256": evidence["toolset_sha256"],
        "tools_unchanged": True,
        "tools_executed_by_verifier": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "physical_device_support_claimed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only exact repo/git byte evidence for AOSP source synchronization")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capture", help="Hash PATH-selected repo and git executables without running them")
    verify = sub.add_parser("verify", help="Re-hash PATH-selected repo/git and compare them with captured evidence")
    verify.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            result = capture_source_tools()
        else:
            result = verify_source_tools(load_source_tool_evidence(args.evidence))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (AospSourceToolEvidenceError, OSError, RuntimeError, ValueError):
        print(
            "AOSP source-tool evidence failed: require stable safe PATH-selected repo/git executables and untampered evidence.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
