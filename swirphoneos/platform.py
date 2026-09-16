"""Offline validation for the pinned AOSP platform baseline.

This module validates reproducibility metadata only. It does not download source
code, execute Repo, build Android, or claim a successful platform build.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")
TAG = re.compile(r"android-[0-9]+\.[0-9]+\.[0-9]+_r[0-9]+\Z")
BUILD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
ALLOWED_STATUS = {"CANDIDATE_NOT_PINNED", "PINNED_NOT_BUILT", "BUILT_VERIFIED"}
ALLOWED_SOURCE_PREFIXES = (
    "https://source.android.com/",
    "https://android.googlesource.com/",
)
REQUIRED_KEYS = {
    "schema_version", "status", "checked_date", "platform", "api_level", "manifest_url",
    "tracking_manifest", "resolved_release_branch", "candidate_release_tag", "candidate_build_id",
    "candidate_security_patch_level", "manifest_commit", "manifest_tree", "tag_object",
    "repo_init_revision", "download_started", "build_completed", "sources", "notes",
}


class PlatformBaselineError(ValueError):
    """Raised when platform baseline metadata is malformed or overstated."""


@dataclass(frozen=True)
class PlatformBaseline:
    status: str
    checked_date: str
    platform: str
    api_level: int
    manifest_url: str
    tracking_manifest: str
    resolved_release_branch: str
    candidate_release_tag: str
    candidate_build_id: str
    security_patch_level: str
    manifest_commit: str | None
    manifest_tree: str | None
    tag_object: str | None
    repo_init_revision: str | None
    download_started: bool
    build_completed: bool
    sources: tuple[str, ...]

    @property
    def pinned(self) -> bool:
        return all(
            value is not None
            for value in (self.manifest_commit, self.manifest_tree, self.tag_object, self.repo_init_revision)
        )

    @property
    def milestone_complete(self) -> bool:
        return self.status == "BUILT_VERIFIED" and self.pinned and self.build_completed


def _bounded_text(value: object, field: str, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise PlatformBaselineError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise PlatformBaselineError(f"{field} is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise PlatformBaselineError(f"{field} contains control characters.")
    return value


def _optional_sha(value: object, field: str) -> str | None:
    if value is None:
        return None
    value = _bounded_text(value, field, 40)
    if not SHA1.fullmatch(value):
        raise PlatformBaselineError(f"{field} must be a 40-character lowercase Git SHA-1.")
    return value


def validate_baseline(data: object) -> PlatformBaseline:
    if not isinstance(data, dict) or set(data) != REQUIRED_KEYS:
        raise PlatformBaselineError("AOSP baseline must match schema v2 exactly.")
    if data["schema_version"] != 2:
        raise PlatformBaselineError("Unsupported AOSP baseline schema version.")

    status = _bounded_text(data["status"], "status", 64)
    if status not in ALLOWED_STATUS:
        raise PlatformBaselineError("Unknown AOSP baseline status.")

    checked_date = _bounded_text(data["checked_date"], "checked_date", 10)
    try:
        date.fromisoformat(checked_date)
    except ValueError as exc:
        raise PlatformBaselineError("checked_date must be ISO YYYY-MM-DD.") from exc

    platform = _bounded_text(data["platform"], "platform", 64)
    api_level = data["api_level"]
    if not isinstance(api_level, int) or isinstance(api_level, bool) or not 1 <= api_level <= 1000:
        raise PlatformBaselineError("api_level is invalid.")

    manifest_url = _bounded_text(data["manifest_url"], "manifest_url")
    if manifest_url != "https://android.googlesource.com/platform/manifest":
        raise PlatformBaselineError("manifest_url must be the official Android manifest repository.")

    tracking = _bounded_text(data["tracking_manifest"], "tracking_manifest", 128)
    branch = _bounded_text(data["resolved_release_branch"], "resolved_release_branch", 128)
    if not TOKEN.fullmatch(tracking) or not TOKEN.fullmatch(branch):
        raise PlatformBaselineError("Manifest/branch token is invalid.")

    tag = _bounded_text(data["candidate_release_tag"], "candidate_release_tag", 128)
    if not TAG.fullmatch(tag):
        raise PlatformBaselineError("candidate_release_tag is invalid.")
    build_id = _bounded_text(data["candidate_build_id"], "candidate_build_id", 64)
    if not BUILD_ID.fullmatch(build_id):
        raise PlatformBaselineError("candidate_build_id is invalid.")

    patch = _bounded_text(data["candidate_security_patch_level"], "candidate_security_patch_level", 10)
    try:
        date.fromisoformat(patch)
    except ValueError as exc:
        raise PlatformBaselineError("candidate_security_patch_level must be an ISO date.") from exc

    manifest_commit = _optional_sha(data["manifest_commit"], "manifest_commit")
    manifest_tree = _optional_sha(data["manifest_tree"], "manifest_tree")
    tag_object = _optional_sha(data["tag_object"], "tag_object")
    repo_init_revision_raw = data["repo_init_revision"]
    repo_init_revision = None if repo_init_revision_raw is None else _bounded_text(
        repo_init_revision_raw, "repo_init_revision", 128
    )
    if repo_init_revision is not None and not TAG.fullmatch(repo_init_revision):
        raise PlatformBaselineError("repo_init_revision must be an exact Android release tag.")

    pin_values = (manifest_commit, manifest_tree, tag_object, repo_init_revision)
    if status == "CANDIDATE_NOT_PINNED":
        if any(value is not None for value in pin_values):
            raise PlatformBaselineError("An unpinned candidate cannot contain partial pin metadata.")
    else:
        if any(value is None for value in pin_values):
            raise PlatformBaselineError("Pinned/built baselines require complete manifest pin metadata.")
        if repo_init_revision != tag:
            raise PlatformBaselineError("repo_init_revision must match candidate_release_tag.")

    download_started = data["download_started"]
    build_completed = data["build_completed"]
    if not isinstance(download_started, bool) or not isinstance(build_completed, bool):
        raise PlatformBaselineError("download/build flags must be booleans.")
    if build_completed and not download_started:
        raise PlatformBaselineError("A build cannot complete before source acquisition starts.")
    if status == "CANDIDATE_NOT_PINNED" and (download_started or build_completed):
        raise PlatformBaselineError("An unpinned candidate cannot claim source download/build completion.")
    if status == "PINNED_NOT_BUILT" and build_completed:
        raise PlatformBaselineError("PINNED_NOT_BUILT cannot claim a completed build.")
    if status == "BUILT_VERIFIED" and not (download_started and build_completed):
        raise PlatformBaselineError("BUILT_VERIFIED requires downloaded source and a completed build.")

    sources_raw = data["sources"]
    if not isinstance(sources_raw, list) or not sources_raw or len(sources_raw) > 32:
        raise PlatformBaselineError("sources must be a non-empty bounded list.")
    sources: list[str] = []
    for source in sources_raw:
        source = _bounded_text(source, "source")
        if not source.startswith(ALLOWED_SOURCE_PREFIXES):
            raise PlatformBaselineError("Platform sources must use official Android documentation/Git hosts.")
        sources.append(source)

    _bounded_text(data["notes"], "notes", 4096)
    return PlatformBaseline(
        status=status,
        checked_date=checked_date,
        platform=platform,
        api_level=api_level,
        manifest_url=manifest_url,
        tracking_manifest=tracking,
        resolved_release_branch=branch,
        candidate_release_tag=tag,
        candidate_build_id=build_id,
        security_patch_level=patch,
        manifest_commit=manifest_commit,
        manifest_tree=manifest_tree,
        tag_object=tag_object,
        repo_init_revision=repo_init_revision,
        download_started=download_started,
        build_completed=build_completed,
        sources=tuple(sources),
    )


def load_baseline(path: Path) -> PlatformBaseline:
    if not path.is_file():
        raise PlatformBaselineError("AOSP baseline file does not exist.")
    try:
        text = path.read_text(encoding="utf-8")
        if len(text) > 262144:
            raise PlatformBaselineError("AOSP baseline file is oversized.")
        data = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlatformBaselineError("AOSP baseline could not be read as UTF-8 JSON.") from exc
    return validate_baseline(data)


def public_baseline_summary(baseline: PlatformBaseline) -> dict[str, object]:
    return {
        "schema_version": 2,
        "status": baseline.status,
        "checked_date": baseline.checked_date,
        "platform": baseline.platform,
        "api_level": baseline.api_level,
        "tracking_manifest": baseline.tracking_manifest,
        "resolved_release_branch": baseline.resolved_release_branch,
        "candidate_release_tag": baseline.candidate_release_tag,
        "candidate_build_id": baseline.candidate_build_id,
        "security_patch_level": baseline.security_patch_level,
        "manifest_commit": baseline.manifest_commit,
        "manifest_tree": baseline.manifest_tree,
        "tag_object": baseline.tag_object,
        "repo_init_revision": baseline.repo_init_revision,
        "pinned": baseline.pinned,
        "download_started": baseline.download_started,
        "build_completed": baseline.build_completed,
        "aosp_milestone_complete": baseline.milestone_complete,
        "sources": list(baseline.sources),
    }
