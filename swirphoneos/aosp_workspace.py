"""Deterministic host-side orchestration for a pinned SwirPhoneOS AOSP workspace.

The helpers in this module deliberately stop before claiming an Android build or
boot. They generate a bounded build plan, validate a resolved ``repo manifest
-r`` snapshot and can stage the checked-in product definition plus explicitly
listed Swir app source into an initialized owner-controlled AOSP checkout only
after an explicit execute flag. No function talks to a phone or enables flashing.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import xml.etree.ElementTree as ET

from .platform import PlatformBaseline
from .product_contract import ProductContract


class AospWorkspaceError(ValueError):
    """Raised when reproducible-workspace evidence or input is unsafe/invalid."""


_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_MAX_MANIFEST_BYTES = 16 * 1024 * 1024
_MAX_STAGE_FILE_BYTES = 2 * 1024 * 1024
_MAX_STAGE_TOTAL_BYTES = 32 * 1024 * 1024
_MAX_STAGE_FILES = 512
_LEGACY_STAGE_FILES = ("AndroidProducts.mk", "swirphoneos_cf_x86_64.mk")


@dataclass(frozen=True)
class AospWorkspacePlan:
    workspace: Path
    manifest_url: str
    revision: str
    lunch_choice: str
    jobs: int
    commands: tuple[tuple[str, ...], ...]
    stage_destination: Path


@dataclass(frozen=True)
class ResolvedManifestEvidence:
    project_count: int
    unique_path_count: int
    sha256: str
    all_projects_pinned: bool


@dataclass(frozen=True)
class StageEntry:
    source: PurePosixPath
    destination: PurePosixPath


def _safe_workspace(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == Path(resolved.anchor):
        raise AospWorkspaceError("AOSP workspace must not be a filesystem root.")
    return resolved


def make_workspace_plan(
    baseline: PlatformBaseline,
    contract: ProductContract,
    workspace: Path,
    *,
    jobs: int = 8,
) -> AospWorkspacePlan:
    """Return an argv-only plan for an exact pinned baseline and Swir product."""
    if not baseline.pinned or baseline.repo_init_revision is None:
        raise AospWorkspaceError("AOSP baseline is not completely pinned.")
    if baseline.status == "CANDIDATE_NOT_PINNED":
        raise AospWorkspaceError("Unpinned AOSP candidates cannot create a workspace plan.")
    if not isinstance(jobs, int) or isinstance(jobs, bool) or not 1 <= jobs <= 256:
        raise AospWorkspaceError("jobs must be an integer between 1 and 256.")
    root = _safe_workspace(workspace)
    stage_destination = root / "vendor" / "swir"
    build_script = (
        "set -euo pipefail; "
        "source build/envsetup.sh; "
        f"lunch {contract.lunch_choice}; "
        f"m -j{jobs}"
    )
    commands = (
        (
            "repo",
            "init",
            "-u",
            baseline.manifest_url,
            "-b",
            baseline.repo_init_revision,
        ),
        ("repo", "sync", "-c", "--no-tags", "--optimized-fetch", "--prune", f"-j{jobs}"),
        ("repo", "manifest", "-r", "-o", "swirphoneos-pinned-manifest.xml"),
        ("python", "-m", "swirphoneos", "stage-product", "--workspace", str(root), "--execute"),
        ("bash", "-lc", build_script),
    )
    return AospWorkspacePlan(
        workspace=root,
        manifest_url=baseline.manifest_url,
        revision=baseline.repo_init_revision,
        lunch_choice=contract.lunch_choice,
        jobs=jobs,
        commands=commands,
        stage_destination=stage_destination,
    )


def public_workspace_plan(plan: AospWorkspacePlan) -> dict[str, object]:
    return {
        "schema_version": 2,
        "workspace": str(plan.workspace),
        "manifest_url": plan.manifest_url,
        "revision": plan.revision,
        "lunch_choice": plan.lunch_choice,
        "jobs": plan.jobs,
        "commands": [list(command) for command in plan.commands],
        "stage_destination": str(plan.stage_destination),
        "device_write_allowed": False,
        "build_verified": False,
        "boot_verified": False,
        "note": "Plan only. Source sync, explicit source staging, build and boot require local execution/evidence.",
    }


def _read_manifest(path: Path) -> str:
    if not path.is_file():
        raise AospWorkspaceError("Resolved manifest snapshot does not exist.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AospWorkspaceError("Resolved manifest snapshot could not be read.") from exc
    if not raw or len(raw) > _MAX_MANIFEST_BYTES:
        raise AospWorkspaceError("Resolved manifest snapshot has an invalid size.")
    try:
        return raw.decode("utf-8")
    except UnicodeError as exc:
        raise AospWorkspaceError("Resolved manifest snapshot must be UTF-8.") from exc


def validate_resolved_manifest(path: Path) -> ResolvedManifestEvidence:
    """Validate evidence captured with ``repo manifest -r``."""
    text = _read_manifest(path)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise AospWorkspaceError("Resolved manifest snapshot is not valid XML.") from exc
    if root.tag != "manifest":
        raise AospWorkspaceError("Resolved manifest root element must be <manifest>.")

    projects = root.findall("project")
    if not projects:
        raise AospWorkspaceError("Resolved manifest contains no projects.")
    paths: set[str] = set()
    names: set[str] = set()
    all_pinned = True
    for project in projects:
        name = (project.get("name") or "").strip()
        project_path = (project.get("path") or name).strip()
        revision = (project.get("revision") or "").strip()
        if not name or not project_path:
            raise AospWorkspaceError("Resolved manifest project is missing name/path identity.")
        if name in names or project_path in paths:
            raise AospWorkspaceError("Resolved manifest contains duplicate project identity/path.")
        names.add(name)
        paths.add(project_path)
        if not _SHA1.fullmatch(revision):
            all_pinned = False

    if not all_pinned:
        raise AospWorkspaceError("Resolved manifest contains a floating/non-SHA project revision.")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ResolvedManifestEvidence(
        project_count=len(projects),
        unique_path_count=len(paths),
        sha256=digest,
        all_projects_pinned=True,
    )


def public_manifest_evidence(evidence: ResolvedManifestEvidence) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_count": evidence.project_count,
        "unique_path_count": evidence.unique_path_count,
        "sha256": evidence.sha256,
        "all_projects_pinned": evidence.all_projects_pinned,
        "build_verified": False,
        "boot_verified": False,
    }


def _safe_relative(value: object, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        raise AospWorkspaceError(f"Stage {field} must be a non-empty POSIX relative path.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise AospWorkspaceError(f"Stage {field} may not escape its root.")
    return path


def _load_stage_entries(product_root: Path) -> tuple[StageEntry, ...]:
    manifest = product_root / "stage_manifest.json"
    if not manifest.exists():
        return tuple(
            StageEntry(PurePosixPath(name), PurePosixPath("vendor/swir/products") / name)
            for name in _LEGACY_STAGE_FILES
        )
    if not manifest.is_file() or manifest.is_symlink():
        raise AospWorkspaceError("AOSP stage manifest must be a regular file.")
    try:
        raw = manifest.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AospWorkspaceError("AOSP stage manifest is unreadable or invalid JSON.") from exc
    if len(raw) > 262_144:
        raise AospWorkspaceError("AOSP stage manifest is oversized.")
    if not isinstance(data, dict) or set(data) != {"schema_version", "files"} or data["schema_version"] != 1:
        raise AospWorkspaceError("AOSP stage manifest must match schema v1 exactly.")
    files = data["files"]
    if not isinstance(files, list) or not 2 <= len(files) <= _MAX_STAGE_FILES:
        raise AospWorkspaceError("AOSP stage manifest file count is invalid.")

    entries: list[StageEntry] = []
    sources: set[PurePosixPath] = set()
    destinations: set[PurePosixPath] = set()
    total_bytes = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {"source", "destination"}:
            raise AospWorkspaceError("AOSP stage entry must match schema exactly.")
        source_rel = _safe_relative(item["source"], "source")
        destination_rel = _safe_relative(item["destination"], "destination")
        if not destination_rel.as_posix().startswith("vendor/swir/"):
            raise AospWorkspaceError("AOSP stage destination must remain under vendor/swir/.")
        if source_rel in sources or destination_rel in destinations:
            raise AospWorkspaceError("AOSP stage sources and destinations must be unique.")
        source = product_root / Path(*source_rel.parts)
        if not source.is_file() or source.is_symlink():
            raise AospWorkspaceError("AOSP stage source is missing or not a regular file.")
        size = source.stat().st_size
        if size <= 0 or size > _MAX_STAGE_FILE_BYTES:
            raise AospWorkspaceError("AOSP stage source has an invalid size.")
        total_bytes += size
        if total_bytes > _MAX_STAGE_TOTAL_BYTES:
            raise AospWorkspaceError("AOSP stage bundle is oversized.")
        sources.add(source_rel)
        destinations.add(destination_rel)
        entries.append(StageEntry(source_rel, destination_rel))
    return tuple(entries)


def stage_product_tree(
    product_root: Path,
    workspace: Path,
    *,
    execute: bool = False,
) -> dict[str, object]:
    """Plan or explicitly copy the bounded Swir product/app source bundle into AOSP."""
    source = product_root.expanduser().resolve()
    target_root = _safe_workspace(workspace)
    entries = _load_stage_entries(source)
    planned = [
        {
            "source": str(source / Path(*entry.source.parts)),
            "destination": str(target_root / Path(*entry.destination.parts)),
        }
        for entry in entries
    ]
    if execute:
        if not (target_root / ".repo").is_dir() or not (target_root / "build" / "envsetup.sh").is_file():
            raise AospWorkspaceError("Refusing to stage into a directory that is not an initialized AOSP checkout.")
        for entry in entries:
            src = source / Path(*entry.source.parts)
            dst = target_root / Path(*entry.destination.parts)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    return {
        "schema_version": 2,
        "workspace": str(target_root),
        "destination_root": str(target_root / "vendor" / "swir"),
        "file_count": len(entries),
        "files": planned,
        "executed": execute,
        "device_write_allowed": False,
        "note": "Stages only manifest-whitelisted Swir AOSP product/app source; it does not build Android or write to a phone.",
    }
