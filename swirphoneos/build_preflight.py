"""Bounded, read-only AOSP build-host and workspace preflight.

The preflight inspects local host/workspace metadata and the installed Repo
launcher bytes only. It never executes external commands, installs packages,
downloads Android source, changes system configuration, deletes stale state,
or starts a build. Persistent self-hosted runners are rejected when required
host tooling is missing, the Repo launcher is too old/unverifiable, or
unreviewed workspace state could contaminate an evidence-producing build.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import platform as host_platform
import re
import shutil

MIN_FREE_BYTES = 400 * 1024**3
MIN_RAM_BYTES = 64 * 1024**3
MIN_GLIBC = (2, 17)
MIN_REPO_LAUNCHER = (2, 4)
MAX_REPO_LAUNCHER_BYTES = 1024 * 1024

# Command counterparts for the current official AOSP Ubuntu package guidance,
# plus Repo/Python/Bash needed by the checked-in evidence workflow. Header/dev
# libraries from that package list cannot be proven safely by command lookup and
# remain an explicit operator responsibility.
REQUIRED_COMMANDS = (
    "git",
    "repo",
    "bash",
    "python3",
    "gpg",
    "flex",
    "bison",
    "gcc",
    "g++",
    "zip",
    "curl",
    "xmllint",
    "xsltproc",
    "unzip",
    "fc-list",
)
ADVISORY_COMMANDS = ("make",)
SUPPORTED_ARCHES = {"x86_64", "amd64"}
VERSION = re.compile(r"([0-9]+)\.([0-9]+)")
REPO_VERSION_ASSIGNMENT = re.compile(
    rb"(?m)^\s*VERSION\s*=\s*\(\s*([0-9]+)\s*,\s*([0-9]+)(?:\s*,\s*[0-9]+)?\s*\)"
)
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
    workspace_identity_sha256: str = "0" * 64
    workspace_writable: bool = True
    dangerous_workspace_root: bool = False
    repo_initialized: bool = False
    repo_local_manifests_present: bool = False
    repo_legacy_local_manifest_present: bool = False
    out_tree_nonempty: bool = False
    vendor_swir_is_symlink: bool = False
    free_inodes: int | None = None
    repo_launcher_version: str | None = None


def _version_tuple(value: str | None) -> tuple[int, int] | None:
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


def _has_any_entry(path: Path) -> bool:
    """Return whether a path contains state, treating aliases/files as state."""
    if path.is_symlink():
        return True
    if not path.exists():
        return False
    if not path.is_dir():
        return True
    try:
        next(path.iterdir())
    except StopIteration:
        return False
    except OSError as exc:
        raise BuildPreflightError("Workspace state could not be inspected safely.") from exc
    return True


def _free_inodes(workspace: Path) -> int | None:
    if not hasattr(os, "statvfs"):
        return None
    try:
        return int(os.statvfs(workspace).f_favail)
    except (OSError, ValueError, OverflowError):
        return None


def _workspace_identity(workspace: Path) -> str:
    try:
        canonical = str(workspace.resolve(strict=True))
    except (OSError, RuntimeError) as exc:
        raise BuildPreflightError("Workspace canonical identity could not be resolved.") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _repo_launcher_version(executable: str | None) -> str | None:
    """Read the official Repo launcher VERSION tuple without executing Repo."""
    if not executable:
        return None
    try:
        path = Path(executable).resolve(strict=True)
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size <= 0 or size > MAX_REPO_LAUNCHER_BYTES:
            return None
        raw = path.read_bytes()
    except (OSError, RuntimeError, ValueError):
        return None
    match = REPO_VERSION_ASSIGNMENT.search(raw)
    if match is None:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    return f"{major}.{minor}"


def capture_host(workspace: Path) -> HostSnapshot:
    """Capture bounded host/workspace facts without subprocesses or network access."""
    if not workspace.is_absolute():
        raise BuildPreflightError("Workspace must be an absolute directory path.")
    if not workspace.is_dir():
        raise BuildPreflightError("Workspace directory does not exist.")
    try:
        canonical = workspace.resolve(strict=True)
        free_bytes = shutil.disk_usage(canonical).free
    except (OSError, RuntimeError) as exc:
        raise BuildPreflightError("Workspace disk usage could not be inspected safely.") from exc

    dangerous_roots = {Path("/").resolve()}
    try:
        dangerous_roots.add(Path.home().resolve(strict=True))
    except (OSError, RuntimeError):
        pass

    repo_root = canonical / ".repo"
    local_manifests = repo_root / "local_manifests"
    legacy_local_manifest = repo_root / "local_manifest.xml"
    out_tree = canonical / "out"
    vendor_swir = canonical / "vendor" / "swir"

    libc_name, libc_version = host_platform.libc_ver()
    glibc_version = libc_version if libc_name.lower() == "glibc" and libc_version else None
    command_names = tuple(dict.fromkeys((*REQUIRED_COMMANDS, *ADVISORY_COMMANDS)))
    command_paths = {name: shutil.which(name) for name in command_names}
    commands = {name: path is not None for name, path in command_paths.items()}
    return HostSnapshot(
        system=host_platform.system().lower(),
        machine=host_platform.machine().lower(),
        glibc_version=glibc_version,
        ram_bytes=_ram_bytes(),
        free_bytes=free_bytes,
        commands=commands,
        kvm_available=os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK),
        workspace_identity_sha256=_workspace_identity(canonical),
        workspace_writable=os.access(canonical, os.W_OK | os.X_OK),
        dangerous_workspace_root=canonical in dangerous_roots,
        repo_initialized=repo_root.is_dir() and not repo_root.is_symlink(),
        repo_local_manifests_present=_has_any_entry(local_manifests),
        repo_legacy_local_manifest_present=legacy_local_manifest.exists() or legacy_local_manifest.is_symlink(),
        out_tree_nonempty=_has_any_entry(out_tree),
        vendor_swir_is_symlink=vendor_swir.is_symlink(),
        free_inodes=_free_inodes(canonical),
        repo_launcher_version=_repo_launcher_version(command_paths.get("repo")),
    )


def evaluate_preflight(snapshot: HostSnapshot) -> dict[str, object]:
    """Evaluate official host requirements plus clean evidence-workspace gates."""
    is_linux = snapshot.system == "linux"
    is_x86_64 = snapshot.machine in SUPPORTED_ARCHES
    glibc = _version_tuple(snapshot.glibc_version)
    glibc_ok = glibc is not None and glibc >= MIN_GLIBC
    repo_version = _version_tuple(snapshot.repo_launcher_version)
    repo_version_ok = repo_version is not None and repo_version >= MIN_REPO_LAUNCHER
    disk_ok = snapshot.free_bytes >= MIN_FREE_BYTES
    ram_known = snapshot.ram_bytes is not None
    ram_ok = ram_known and snapshot.ram_bytes >= MIN_RAM_BYTES
    required_tools_ok = all(snapshot.commands.get(name, False) for name in REQUIRED_COMMANDS)
    workspace_safe = (
        snapshot.workspace_writable
        and not snapshot.dangerous_workspace_root
        and not snapshot.repo_local_manifests_present
        and not snapshot.repo_legacy_local_manifest_present
        and not snapshot.out_tree_nonempty
        and not snapshot.vendor_swir_is_symlink
    )
    sync_ready = (
        is_linux
        and is_x86_64
        and glibc_ok
        and disk_ok
        and required_tools_ok
        and repo_version_ok
        and workspace_safe
    )
    build_ready = sync_ready and ram_ok

    checks = [
        {"id": "linux", "passed": is_linux, "required_for": "sync+build"},
        {"id": "x86_64", "passed": is_x86_64, "required_for": "sync+build"},
        {"id": "glibc_2_17_plus", "passed": glibc_ok, "required_for": "sync+build"},
        {"id": "free_disk_400_gib", "passed": disk_ok, "required_for": "sync+build"},
        {"id": "ram_64_gib", "passed": ram_ok, "required_for": "full_build"},
    ]
    checks.extend(
        {"id": f"command_{name}", "passed": bool(snapshot.commands.get(name)), "required_for": "sync+build"}
        for name in REQUIRED_COMMANDS
    )
    checks.extend(
        [
            {"id": "repo_launcher_2_4_plus", "passed": repo_version_ok, "required_for": "sync+build"},
            {"id": "workspace_writable", "passed": snapshot.workspace_writable, "required_for": "sync+build"},
            {"id": "workspace_not_dangerous_root", "passed": not snapshot.dangerous_workspace_root, "required_for": "sync+build"},
            {"id": "no_repo_local_manifests", "passed": not snapshot.repo_local_manifests_present, "required_for": "sync+build"},
            {"id": "no_legacy_repo_local_manifest", "passed": not snapshot.repo_legacy_local_manifest_present, "required_for": "sync+build"},
            {"id": "fresh_out_tree", "passed": not snapshot.out_tree_nonempty, "required_for": "sync+build"},
            {"id": "vendor_swir_not_symlink", "passed": not snapshot.vendor_swir_is_symlink, "required_for": "sync+build"},
        ]
    )
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
            "free_inodes": snapshot.free_inodes,
            "repo_launcher_version": snapshot.repo_launcher_version,
        },
        "workspace": {
            "identity_sha256": snapshot.workspace_identity_sha256,
            "writable": snapshot.workspace_writable,
            "dangerous_root": snapshot.dangerous_workspace_root,
            "repo_initialized": snapshot.repo_initialized,
            "local_manifests_present": snapshot.repo_local_manifests_present,
            "legacy_local_manifest_present": snapshot.repo_legacy_local_manifest_present,
            "out_tree_nonempty": snapshot.out_tree_nonempty,
            "vendor_swir_is_symlink": snapshot.vendor_swir_is_symlink,
            "cleanup_performed": False,
        },
        "requirements": {
            "minimum_free_bytes": MIN_FREE_BYTES,
            "minimum_ram_bytes": MIN_RAM_BYTES,
            "minimum_glibc": "2.17",
            "minimum_repo_launcher": "2.4",
            "required_command_checks": list(REQUIRED_COMMANDS),
        },
        "checks": checks,
        "advisory_commands": advisory,
        "warnings": [
            "Passing this preflight is not evidence of a successful AOSP build.",
            "The Repo launcher version is parsed from bounded launcher bytes; Repo is not executed by this preflight.",
            "Observable command checks cannot prove that every required development header/library package is installed.",
            "The evidence workflow requires a clean out/ tree; this preflight never deletes stale output automatically.",
            "Repo local manifests are rejected so persistent runners cannot silently add unreviewed source projects.",
            "Existing regular vendor/swir content is validated later by exact staging-tree closure; symlinked vendor/swir is rejected here.",
            "This check does not install Ubuntu packages, configure KVM/Cuttlefish, or verify proprietary vendor inputs.",
            "A source sync must use the pinned release tag and preserve repo manifest -r output before reproducibility is claimed.",
        ],
        "sources": list(SOURCES),
    }
