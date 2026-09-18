"""Read-only integrity evidence for a synchronized AOSP Repo workspace.

The collector verifies that every project in a captured ``repo manifest -r``
snapshot is checked out at that exact commit and has no tracked or non-ignored
untracked source drift. It executes only a narrow set of read-only Git queries;
it never runs Repo, changes the checkout, builds Android, or touches a phone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET


class AospSourceEvidenceError(ValueError):
    """Raised when synchronized AOSP source cannot be proven exact and clean."""


MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_GIT_TOOL_BYTES = 128 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 30
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospSourceEvidenceError("JSON contains a duplicate key.")
        result[key] = value
    return result


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(value: object) -> str:
    return _sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )


def _read_manifest(path: Path) -> tuple[bytes, ET.Element]:
    if path.is_symlink() or not path.is_file():
        raise AospSourceEvidenceError("Resolved Repo manifest must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AospSourceEvidenceError("Resolved Repo manifest could not be read.") from exc
    if not raw or len(raw) > MAX_MANIFEST_BYTES:
        raise AospSourceEvidenceError("Resolved Repo manifest has an invalid size.")
    try:
        text = raw.decode("utf-8", "strict")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as exc:
        raise AospSourceEvidenceError("Resolved Repo manifest must be valid UTF-8 XML.") from exc
    if root.tag != "manifest":
        raise AospSourceEvidenceError("Resolved Repo manifest root must be <manifest>.")
    return raw, root


def _safe_project_path(value: str) -> PurePosixPath:
    if not value or "\\" in value or "\x00" in value:
        raise AospSourceEvidenceError("Manifest project path is unsafe.")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/"):
        raise AospSourceEvidenceError("Manifest project path must be relative.")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise AospSourceEvidenceError("Manifest project path contains an unsafe segment.")
    return path


def _manifest_projects(root: ET.Element) -> tuple[tuple[str, PurePosixPath, str], ...]:
    projects: list[tuple[str, PurePosixPath, str]] = []
    seen_names: set[str] = set()
    seen_paths: set[str] = set()
    for element in root.findall("project"):
        name = (element.get("name") or "").strip()
        path_text = (element.get("path") or name).strip()
        revision = (element.get("revision") or "").strip()
        if not name or name in seen_names:
            raise AospSourceEvidenceError("Resolved Repo manifest project name is missing or duplicated.")
        path = _safe_project_path(path_text)
        path_key = path.as_posix()
        if path_key in seen_paths:
            raise AospSourceEvidenceError("Resolved Repo manifest project path is duplicated.")
        if _HEX40.fullmatch(revision) is None:
            raise AospSourceEvidenceError("Resolved Repo manifest contains a floating project revision.")
        seen_names.add(name)
        seen_paths.add(path_key)
        projects.append((name, path, revision))
    if not projects:
        raise AospSourceEvidenceError("Resolved Repo manifest contains no projects.")
    return tuple(projects)


def _canonical_workspace(workspace: Path) -> Path:
    if not workspace.is_absolute():
        raise AospSourceEvidenceError("AOSP workspace must be an absolute path.")
    if workspace.is_symlink() or not workspace.is_dir():
        raise AospSourceEvidenceError("AOSP workspace must be a real directory, not a symlink.")
    try:
        root = workspace.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AospSourceEvidenceError("AOSP workspace identity could not be resolved.") from exc
    if root == Path(root.anchor):
        raise AospSourceEvidenceError("AOSP workspace must not be a filesystem root.")
    if not (root / ".repo").is_dir() or (root / ".repo").is_symlink():
        raise AospSourceEvidenceError("AOSP workspace is not an initialized Repo checkout.")
    return root


def _tool_identity() -> tuple[Path, int, str, str]:
    executable = shutil.which("git")
    if not executable:
        raise AospSourceEvidenceError("Git executable is unavailable.")
    try:
        path = Path(executable).resolve(strict=True)
        info = path.stat()
        if not path.is_file() or info.st_size <= 0 or info.st_size > MAX_GIT_TOOL_BYTES:
            raise AospSourceEvidenceError("Git executable has an invalid file identity.")
        if os.name != "nt" and stat.S_IMODE(info.st_mode) & 0o022:
            raise AospSourceEvidenceError("Git executable is group/world writable.")
        raw = path.read_bytes()
    except (OSError, RuntimeError) as exc:
        raise AospSourceEvidenceError("Git executable identity could not be captured.") from exc
    if len(raw) != info.st_size:
        raise AospSourceEvidenceError("Git executable changed while it was being read.")
    path_identity = _sha256_bytes(str(path).encode("utf-8"))
    return path, info.st_size, _sha256_bytes(raw), path_identity


def _project_directory(root: Path, relative: PurePosixPath) -> Path:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise AospSourceEvidenceError("Manifest project path traverses a symbolic link.")
    if not current.is_dir():
        raise AospSourceEvidenceError("Manifest project checkout is missing.")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise AospSourceEvidenceError("Manifest project checkout escapes the AOSP workspace.") from exc
    return resolved


def _run_git(git: Path, project: Path, args: tuple[str, ...], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env.update({"LC_ALL": "C", "LANG": "C", "GIT_OPTIONAL_LOCKS": "0"})
    command = [
        str(git),
        "-c", "core.fsmonitor=false",
        "-c", "core.untrackedCache=false",
        "-C", str(project),
        *args,
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AospSourceEvidenceError("Read-only Git verification could not execute safely.") from exc
    if len(result.stdout) > MAX_GIT_OUTPUT_BYTES or len(result.stderr) > MAX_GIT_OUTPUT_BYTES:
        raise AospSourceEvidenceError("Read-only Git verification produced oversized output.")
    if check and result.returncode != 0:
        raise AospSourceEvidenceError("Read-only Git verification rejected a project checkout.")
    return result


def _nested_project_prefixes(project_path: PurePosixPath, all_paths: tuple[PurePosixPath, ...]) -> tuple[str, ...]:
    prefix = project_path.as_posix() + "/"
    nested: list[str] = []
    for candidate in all_paths:
        value = candidate.as_posix()
        if value.startswith(prefix):
            nested.append(value[len(prefix):])
    return tuple(sorted(nested))


def _is_nested_repo_entry(entry: str, nested_prefixes: tuple[str, ...]) -> bool:
    normalized = entry.rstrip("/")
    return any(normalized == prefix or normalized.startswith(prefix + "/") for prefix in nested_prefixes)


def _verify_project(
    *,
    git: Path,
    root: Path,
    project_path: PurePosixPath,
    revision: str,
    all_paths: tuple[PurePosixPath, ...],
) -> dict[str, object]:
    project = _project_directory(root, project_path)
    top = _run_git(git, project, ("rev-parse", "--show-toplevel")).stdout
    try:
        top_text = top.decode("utf-8", "strict").strip()
        top_path = Path(top_text).resolve(strict=True)
    except (UnicodeError, OSError, RuntimeError) as exc:
        raise AospSourceEvidenceError("Git project root identity is invalid.") from exc
    if top_path != project:
        raise AospSourceEvidenceError("Manifest project path is not the Git worktree root.")

    head_raw = _run_git(git, project, ("rev-parse", "--verify", "HEAD^{commit}")).stdout
    try:
        head = head_raw.decode("ascii", "strict").strip()
    except UnicodeError as exc:
        raise AospSourceEvidenceError("Git HEAD identity is not ASCII.") from exc
    if _HEX40.fullmatch(head) is None or head != revision:
        raise AospSourceEvidenceError("Git HEAD does not match the resolved Repo manifest revision.")

    diff = _run_git(git, project, ("diff", "--quiet", "--no-ext-diff", "HEAD", "--"), check=False)
    if diff.returncode not in (0, 1):
        raise AospSourceEvidenceError("Tracked source drift could not be inspected safely.")
    if diff.returncode == 1:
        raise AospSourceEvidenceError("Tracked AOSP source differs from the resolved manifest checkout.")

    untracked_raw = _run_git(git, project, ("ls-files", "--others", "--exclude-standard", "-z")).stdout
    try:
        values = [item for item in untracked_raw.decode("utf-8", "strict").split("\x00") if item]
    except UnicodeError as exc:
        raise AospSourceEvidenceError("Untracked source path is not valid UTF-8.") from exc
    nested_prefixes = _nested_project_prefixes(project_path, all_paths)
    unexpected = [item for item in values if not _is_nested_repo_entry(item, nested_prefixes)]
    if unexpected:
        raise AospSourceEvidenceError("AOSP project contains non-ignored untracked source outside nested Repo projects.")

    return {
        "path": project_path.as_posix(),
        "revision": revision,
        "head": head,
        "head_matches_manifest": True,
        "tracked_clean": True,
        "untracked_clean": True,
    }


def collect_source_checkout_evidence(workspace: Path, manifest_path: Path) -> dict[str, object]:
    """Verify exact Repo project HEADs and clean source state without changing the workspace."""
    root = _canonical_workspace(workspace)
    raw_manifest, manifest_root = _read_manifest(manifest_path)
    projects = _manifest_projects(manifest_root)
    git, git_size, git_sha, git_path_identity = _tool_identity()
    all_paths = tuple(project[1] for project in projects)

    records: list[dict[str, object]] = []
    for _name, project_path, revision in projects:
        records.append(
            _verify_project(
                git=git,
                root=root,
                project_path=project_path,
                revision=revision,
                all_paths=all_paths,
            )
        )
    records.sort(key=lambda item: str(item["path"]))
    state_digest = _canonical_sha256(
        [{"path": item["path"], "revision": item["revision"], "head": item["head"]} for item in records]
    )
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_source_checkout_integrity",
        "operation": "READ_ONLY_GIT_WORKTREE_VERIFICATION",
        "workspace_identity_sha256": _sha256_bytes(str(root).encode("utf-8")),
        "resolved_manifest_sha256": _sha256_bytes(raw_manifest),
        "project_count": len(projects),
        "verified_project_count": len(records),
        "git_tool": {
            "size": git_size,
            "sha256": git_sha,
            "path_identity_sha256": git_path_identity,
        },
        "projects": records,
        "aggregate_state_sha256": state_digest,
        "all_project_heads_match": True,
        "all_tracked_worktrees_clean": True,
        "all_untracked_worktrees_clean": True,
        "source_checkout_verified": True,
        "git_tool_executed_read_only": True,
        "device_write_allowed": False,
        "build_verified": False,
        "boot_verified": False,
        "status_promotion_performed": False,
        "warnings": [
            "This evidence verifies synchronized Git project bytes/state only; it is not proof that Android built or booted.",
            "Non-ignored untracked paths are rejected except exact nested Repo project roots from the same resolved manifest.",
            "No Repo sync, checkout, reset, clean, build, phone write, flash, unlock, root or status promotion is performed.",
        ],
    }
    payload["source_evidence_sha256"] = _canonical_sha256(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify exact clean AOSP Repo source state without mutating it")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = collect_source_checkout_evidence(args.workspace, args.manifest)
    except (AospSourceEvidenceError, OSError, ValueError):
        print(
            "AOSP source verification failed: require one exact clean Repo checkout matching the resolved manifest.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
