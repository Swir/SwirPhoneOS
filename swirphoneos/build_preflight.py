"""Bounded, read-only AOSP build-host preflight.

The preflight inspects local host metadata only. It never installs packages,
downloads Android source, changes system configuration, or starts a build.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform as host_platform
import re
import shutil

MIN_FREE_BYTES = 400 * 1024**3
MIN_RAM_BYTES = 64 * 1024**3
MIN_GLIBC = (2, 17)
REQUIRED_COMMANDS = ("git", "repo")
ADVISORY_COMMANDS = ("bash", "python3", "curl", "zip", "unzip")
SUPPORTED_ARCHES = {"x86_64", "amd64"}
VERSION = re.compile(r"([0-9]+)\.([0-9]+)")
SOURCES = (
    "https://source.android.com/docs/setup/start",
    "https://source.android.com/docs/setup/start/requirements",
)


class BuildPreflightError(ValueError):
    """Raised when a preflight request itself is invalid."""


@dataclass(frozen=True)
class HostSnapshot:
    system: str
    machine: str
    glibc_version: str | None
    ram_bytes: int | None
    free_bytes: int
    commands: dict[str, bool]
    kvm_available: bool


def _glibc_tuple(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    match = VERSION.search(value)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


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


def capture_host(workspace: Path) -> HostSnapshot:
    """Capture bounded host facts without subprocesses or network access."""
    if not workspace.is_absolute():
        raise BuildPreflightError("Workspace must be an absolute directory path.")
    if not workspace.is_dir():
        raise BuildPreflightError("Workspace directory does not exist.")
    try:
        free_bytes = shutil.disk_usage(workspace).free
    except OSError as exc:
        raise BuildPreflightError("Workspace disk usage could not be inspected.") from exc

    libc_name, libc_version = host_platform.libc_ver()
    glibc_version = libc_version if libc_name.lower() == "glibc" and libc_version else None
    commands = {
        name: shutil.which(name) is not None
        for name in (*REQUIRED_COMMANDS, *ADVISORY_COMMANDS)
    }
    return HostSnapshot(
        system=host_platform.system().lower(),
        machine=host_platform.machine().lower(),
        glibc_version=glibc_version,
        ram_bytes=_ram_bytes(),
        free_bytes=free_bytes,
        commands=commands,
        kvm_available=os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK),
    )


def evaluate_preflight(snapshot: HostSnapshot) -> dict[str, object]:
    """Evaluate official AOSP host requirements without changing the host."""
    is_linux = snapshot.system == "linux"
    is_x86_64 = snapshot.machine in SUPPORTED_ARCHES
    glibc = _glibc_tuple(snapshot.glibc_version)
    glibc_ok = glibc is not None and glibc >= MIN_GLIBC
    disk_ok = snapshot.free_bytes >= MIN_FREE_BYTES
    ram_known = snapshot.ram_bytes is not None
    ram_ok = ram_known and snapshot.ram_bytes >= MIN_RAM_BYTES
    required_tools_ok = all(snapshot.commands.get(name, False) for name in REQUIRED_COMMANDS)
    sync_ready = is_linux and is_x86_64 and glibc_ok and disk_ok and required_tools_ok
    build_ready = sync_ready and ram_ok

    checks = [
        {"id": "linux", "passed": is_linux, "required_for": "sync+build"},
        {"id": "x86_64", "passed": is_x86_64, "required_for": "sync+build"},
        {"id": "glibc_2_17_plus", "passed": glibc_ok, "required_for": "sync+build"},
        {"id": "free_disk_400_gib", "passed": disk_ok, "required_for": "sync+build"},
        {"id": "ram_64_gib", "passed": ram_ok, "required_for": "full_build"},
        {"id": "git", "passed": bool(snapshot.commands.get("git")), "required_for": "sync+build"},
        {"id": "repo", "passed": bool(snapshot.commands.get("repo")), "required_for": "sync+build"},
    ]
    advisory = [
        {"id": name, "available": bool(snapshot.commands.get(name))}
        for name in ADVISORY_COMMANDS
    ]
    return {
        "schema_version": 1,
        "operation": "READ_ONLY_HOST_PREFLIGHT",
        "ready_for_source_sync": sync_ready,
        "ready_for_full_build": build_ready,
        "cuttlefish_kvm_available": snapshot.kvm_available,
        "host": {
            "system": snapshot.system,
            "machine": snapshot.machine,
            "glibc_version": snapshot.glibc_version,
            "ram_bytes": snapshot.ram_bytes,
            "free_bytes": snapshot.free_bytes,
        },
        "requirements": {
            "minimum_free_bytes": MIN_FREE_BYTES,
            "minimum_ram_bytes": MIN_RAM_BYTES,
            "minimum_glibc": "2.17",
        },
        "checks": checks,
        "advisory_commands": advisory,
        "warnings": [
            "Passing this preflight is not evidence of a successful AOSP build.",
            "This check does not install Ubuntu packages, configure KVM/Cuttlefish, or verify proprietary vendor inputs.",
            "A source sync must use the pinned release tag and preserve repo manifest -r output before reproducibility is claimed.",
        ],
        "sources": list(SOURCES),
    }
