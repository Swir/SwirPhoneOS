"""Read-only exact host/toolchain evidence for one AOSP build window.

The collector hashes the exact executable bytes of the required host commands
already accepted by build_preflight. It never executes those commands, installs
packages, mutates the workspace, starts a build, or touches a physical device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
from typing import Any

from .build_preflight import REQUIRED_COMMANDS

MAX_TOOL_BYTES = 128 * 1024 * 1024
MAX_OS_RELEASE_BYTES = 64 * 1024
_MAX_REPORT_BYTES = 16 * 1024 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_PHASES = {"PRE_BUILD", "POST_BUILD"}


class AospHostEvidenceError(ValueError):
    """Raised when exact host evidence cannot be captured or validated."""


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path, *, max_bytes: int) -> tuple[int, str]:
    try:
        before = path.stat()
        if not path.is_file():
            raise AospHostEvidenceError("Host tool identity must resolve to a regular file.")
        size = int(before.st_size)
        if size <= 0 or size > max_bytes:
            raise AospHostEvidenceError("Host tool identity has an invalid file size.")
        digest = hashlib.sha256()
        read = 0
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                read += len(chunk)
                if read > max_bytes:
                    raise AospHostEvidenceError("Host tool changed size while being hashed.")
                digest.update(chunk)
        after = path.stat()
    except OSError as exc:
        raise AospHostEvidenceError("Host tool bytes could not be read safely.") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_id != after_id or read != size:
        raise AospHostEvidenceError("Host tool changed while its exact bytes were being hashed.")
    return size, digest.hexdigest()


def _tool_identity(name: str) -> dict[str, object]:
    executable = shutil.which(name)
    if not executable:
        raise AospHostEvidenceError(f"Required host tool is missing: {name}.")
    try:
        resolved = Path(executable).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AospHostEvidenceError(f"Required host tool path could not be resolved: {name}.") from exc
    if not os.access(resolved, os.X_OK):
        raise AospHostEvidenceError(f"Required host tool is not executable: {name}.")
    size, digest = _sha256_file(resolved, max_bytes=MAX_TOOL_BYTES)
    return {
        "name": name,
        "size": size,
        "sha256": digest,
        "path_identity_sha256": hashlib.sha256(str(resolved).encode("utf-8")).hexdigest(),
    }


def _workspace_identity(workspace: Path) -> str:
    if not workspace.is_absolute():
        raise AospHostEvidenceError("AOSP workspace must be an absolute directory path.")
    try:
        canonical = workspace.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AospHostEvidenceError("AOSP workspace identity could not be resolved.") from exc
    if not canonical.is_dir():
        raise AospHostEvidenceError("AOSP workspace must resolve to a directory.")
    return hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()


def _bounded_file_sha(path: Path, *, max_bytes: int) -> str | None:
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            return None
        size = resolved.stat().st_size
        if size <= 0 or size > max_bytes:
            return None
        return hashlib.sha256(resolved.read_bytes()).hexdigest()
    except (OSError, RuntimeError):
        return None


def _ram_bytes() -> int | None:
    path = Path("/proc/meminfo")
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="ascii", errors="strict").splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    return int(parts[1]) * 1024
    except (OSError, UnicodeError, ValueError):
        return None
    return None


def _resource_snapshot(workspace: Path) -> dict[str, object]:
    try:
        disk = shutil.disk_usage(workspace)
    except OSError as exc:
        raise AospHostEvidenceError("AOSP workspace disk resources could not be inspected.") from exc
    free_inodes: int | None = None
    if hasattr(os, "statvfs"):
        try:
            free_inodes = int(os.statvfs(workspace).f_favail)
        except (OSError, ValueError, OverflowError):
            free_inodes = None
    return {
        "ram_bytes": _ram_bytes(),
        "free_bytes": int(disk.free),
        "free_inodes": free_inodes,
    }


def collect_host_evidence(workspace: Path, phase: str) -> dict[str, object]:
    phase = phase.upper()
    if phase not in _PHASES:
        raise AospHostEvidenceError("Host evidence phase must be PRE_BUILD or POST_BUILD.")
    workspace_sha = _workspace_identity(workspace)
    tools = [_tool_identity(name) for name in REQUIRED_COMMANDS]
    tools.sort(key=lambda item: str(item["name"]))
    toolchain_sha = _canonical_sha(tools)
    libc_name, libc_version = platform.libc_ver()
    static_host = {
        "system": platform.system().lower(),
        "machine": platform.machine().lower(),
        "glibc_version": libc_version if libc_name.lower() == "glibc" and libc_version else None,
        "kernel_release_sha256": hashlib.sha256(platform.release().encode("utf-8")).hexdigest(),
        "os_release_sha256": _bounded_file_sha(Path("/etc/os-release"), max_bytes=MAX_OS_RELEASE_BYTES),
    }
    host_identity_sha = _canonical_sha(static_host)
    environment_identity_sha = _canonical_sha({
        "workspace_identity_sha256": workspace_sha,
        "host_identity_sha256": host_identity_sha,
        "toolchain_sha256": toolchain_sha,
    })
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_host_environment_evidence",
        "operation": "READ_ONLY_BUILD_HOST_IDENTITY",
        "phase": phase,
        "workspace_identity_sha256": workspace_sha,
        "host": static_host,
        "host_identity_sha256": host_identity_sha,
        "required_commands": list(REQUIRED_COMMANDS),
        "tools": tools,
        "tool_count": len(tools),
        "toolchain_sha256": toolchain_sha,
        "environment_identity_sha256": environment_identity_sha,
        "resources": _resource_snapshot(workspace),
        "kvm_available": os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK),
        "host_evidence_complete": True,
        "device_write_allowed": False,
        "build_verified": False,
        "boot_verified": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This report fingerprints the build host and required tool bytes without executing them.",
            "Resource counters may change during a build and are intentionally excluded from environment_identity_sha256.",
            "Passing host evidence does not prove an Android build, boot, physical-device support, installation safety, root support, or beta readiness.",
        ],
    }
    payload["host_evidence_sha256"] = _canonical_sha(payload)
    return payload


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospHostEvidenceError("Host evidence JSON contains a duplicate key.")
        result[key] = value
    return result


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise AospHostEvidenceError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def validate_host_evidence(
    report: dict[str, object], *, expected_phase: str | None = None
) -> tuple[str, str, str, str, bool]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_host_environment_evidence"
        or report.get("operation") != "READ_ONLY_BUILD_HOST_IDENTITY"
        or report.get("host_evidence_complete") is not True
    ):
        raise AospHostEvidenceError("AOSP host evidence identity is invalid or incomplete.")
    phase = report.get("phase")
    if phase not in _PHASES or (expected_phase is not None and phase != expected_phase):
        raise AospHostEvidenceError("AOSP host evidence phase is invalid.")
    if (
        report.get("device_write_allowed") is not False
        or report.get("build_verified") is not False
        or report.get("boot_verified") is not False
        or report.get("physical_device_support_claimed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise AospHostEvidenceError("AOSP host evidence violates the no-write/no-promotion boundary.")
    workspace_sha = _hex64(report.get("workspace_identity_sha256"), "workspace_identity_sha256")
    host = report.get("host")
    if not isinstance(host, dict) or set(host) != {
        "system", "machine", "glibc_version", "kernel_release_sha256", "os_release_sha256"
    }:
        raise AospHostEvidenceError("AOSP host static identity is malformed.")
    if not isinstance(host.get("system"), str) or not host.get("system"):
        raise AospHostEvidenceError("AOSP host system identity is invalid.")
    if not isinstance(host.get("machine"), str) or not host.get("machine"):
        raise AospHostEvidenceError("AOSP host machine identity is invalid.")
    _hex64(host.get("kernel_release_sha256"), "kernel_release_sha256")
    if host.get("os_release_sha256") is not None:
        _hex64(host.get("os_release_sha256"), "os_release_sha256")
    host_identity_sha = _hex64(report.get("host_identity_sha256"), "host_identity_sha256")
    if _canonical_sha(host) != host_identity_sha:
        raise AospHostEvidenceError("AOSP host static identity digest is invalid.")

    required = report.get("required_commands")
    if required != list(REQUIRED_COMMANDS):
        raise AospHostEvidenceError("AOSP host evidence required-command set does not match build preflight.")
    tools = report.get("tools")
    if not isinstance(tools, list) or len(tools) != len(REQUIRED_COMMANDS) or report.get("tool_count") != len(tools):
        raise AospHostEvidenceError("AOSP host tool inventory is incomplete.")
    expected_names = sorted(REQUIRED_COMMANDS)
    seen_names: list[str] = []
    for item in tools:
        if not isinstance(item, dict) or set(item) != {"name", "size", "sha256", "path_identity_sha256"}:
            raise AospHostEvidenceError("AOSP host tool record is malformed.")
        name = item.get("name")
        size = item.get("size")
        if not isinstance(name, str) or name not in REQUIRED_COMMANDS:
            raise AospHostEvidenceError("AOSP host tool name is invalid.")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > MAX_TOOL_BYTES:
            raise AospHostEvidenceError("AOSP host tool size is invalid.")
        _hex64(item.get("sha256"), "tool sha256")
        _hex64(item.get("path_identity_sha256"), "tool path identity sha256")
        seen_names.append(name)
    if sorted(seen_names) != expected_names or len(set(seen_names)) != len(seen_names):
        raise AospHostEvidenceError("AOSP host tool inventory has missing or duplicate required commands.")
    canonical_tools = sorted(tools, key=lambda item: str(item["name"]))
    toolchain_sha = _hex64(report.get("toolchain_sha256"), "toolchain_sha256")
    if _canonical_sha(canonical_tools) != toolchain_sha:
        raise AospHostEvidenceError("AOSP host toolchain digest is invalid.")

    resources = report.get("resources")
    if not isinstance(resources, dict) or set(resources) != {"ram_bytes", "free_bytes", "free_inodes"}:
        raise AospHostEvidenceError("AOSP host resource snapshot is malformed.")
    free_bytes = resources.get("free_bytes")
    if not isinstance(free_bytes, int) or isinstance(free_bytes, bool) or free_bytes < 0:
        raise AospHostEvidenceError("AOSP host free-byte counter is invalid.")
    for key in ("ram_bytes", "free_inodes"):
        value = resources.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise AospHostEvidenceError(f"AOSP host resource counter is invalid: {key}.")
    if not isinstance(report.get("kvm_available"), bool):
        raise AospHostEvidenceError("AOSP host KVM availability flag is invalid.")

    environment_sha = _hex64(report.get("environment_identity_sha256"), "environment_identity_sha256")
    expected_environment_sha = _canonical_sha({
        "workspace_identity_sha256": workspace_sha,
        "host_identity_sha256": host_identity_sha,
        "toolchain_sha256": toolchain_sha,
    })
    if environment_sha != expected_environment_sha:
        raise AospHostEvidenceError("AOSP host environment identity digest is invalid.")
    evidence_sha = _hex64(report.get("host_evidence_sha256"), "host_evidence_sha256")
    canonical_report = {key: value for key, value in report.items() if key != "host_evidence_sha256"}
    if _canonical_sha(canonical_report) != evidence_sha:
        raise AospHostEvidenceError("AOSP host evidence canonical digest is invalid.")
    return evidence_sha, workspace_sha, environment_sha, toolchain_sha, bool(report["kvm_available"])


def load_host_evidence(path: Path, *, expected_phase: str | None = None) -> tuple[dict[str, object], str]:
    if not path.is_absolute():
        raise AospHostEvidenceError("Host evidence path must be absolute.")
    if path.is_symlink() or not path.is_file():
        raise AospHostEvidenceError("Host evidence input must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AospHostEvidenceError("Host evidence input could not be read.") from exc
    if not raw or len(raw) > _MAX_REPORT_BYTES:
        raise AospHostEvidenceError("Host evidence input has an invalid size.")
    try:
        report = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospHostEvidenceError("Host evidence input must be strict UTF-8 JSON.") from exc
    if not isinstance(report, dict):
        raise AospHostEvidenceError("Host evidence input root must be an object.")
    validate_host_evidence(report, expected_phase=expected_phase)
    return report, hashlib.sha256(raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture exact read-only AOSP host/toolchain evidence")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("PRE_BUILD", "POST_BUILD"))
    args = parser.parse_args(argv)
    try:
        report = collect_host_evidence(args.workspace, args.phase)
    except (AospHostEvidenceError, OSError, ValueError):
        print(
            "AOSP host evidence capture failed: exact required host/tool identity could not be proven.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
