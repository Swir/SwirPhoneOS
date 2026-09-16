"""Offline validation for the candidate AOSP platform baseline.

This module does not download source code or claim a reproducible Android build.
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
ALLOWED_STATUS = {"CANDIDATE_NOT_PINNED", "PINNED_NOT_BUILT", "BUILT_VERIFIED"}
REQUIRED_KEYS = {
    "schema_version",
    "status",
    "checked_date",
    "platform",
    "api_level",
    "manifest_url",
    "tracking_manifest",
    "resolved_release_branch",
    "candidate_release_tag",
    "candidate_build_id",
    "candidate_security_patch_level",
    "download_started",
    "build_completed",
    "sources",
    "notes",
}


class PlatformBaselineError(ValueError):
    """Raised when platform discovery metadata is malformed or overstated."""


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
    download_started: bool
    build_completed: bool
    sources: tuple[str, ...]

    @property
    def milestone_complete(self) -> bool:
        return self.status == "BUILT_VERIFIED" and self.build_completed


def _bounded_text(value: object, field: str, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise PlatformBaselineError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise PlatformBaselineError(f"{field} is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise PlatformBaselineError(f"{field} contains control characters.")
    return value


def validate_baseline(data: object) -> PlatformBaseline:
    if not isinstance(data, dict) or set(data) != REQUIRED_KEYS:
        raise PlatformBaselineError("AOSP baseline must match schema v1 exactly.")
    if data["schema_version"] != 1:
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
    if not manifest_url.startswith("https://android.googlesource.com/"):
        raise PlatformBaselineError("manifest_url must use the official Android Git host.")

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
    if status == "BUILT_VERIFIED" and not build_completed:
        raise PlatformBaselineError("BUILT_VERIFIED requires build_completed=true.")

    sources_raw = data["sources"]
    if not isinstance(sources_raw, list) or not sources_raw or len(sources_raw) > 32:
        raise PlatformBaselineError("sources must be a non-empty bounded list.")
    sources: list[str] = []
    for source in sources_raw:
        source = _bounded_text(source, "source")
        if not source.startswith("https://source.android.com/"):
            raise PlatformBaselineError("Platform sources must use source.android.com.")
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
        "status": baseline.status,
        "checked_date": baseline.checked_date,
        "platform": baseline.platform,
        "api_level": baseline.api_level,
        "tracking_manifest": baseline.tracking_manifest,
        "resolved_release_branch": baseline.resolved_release_branch,
        "candidate_release_tag": baseline.candidate_release_tag,
        "candidate_build_id": baseline.candidate_build_id,
        "security_patch_level": baseline.security_patch_level,
        "download_started": baseline.download_started,
        "build_completed": baseline.build_completed,
        "aosp_milestone_complete": baseline.milestone_complete,
        "sources": list(baseline.sources),
    }
