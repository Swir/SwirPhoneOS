"""Read-only device profile registry for SwirPhoneOS.

Schema v1 is intentionally metadata-only. It cannot authorize flashing.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

PROFILE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}/[a-z0-9][a-z0-9._-]{0,63}\Z")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
ALLOWED_STATUS = {
    "PLANNED_NOT_SUPPORTED",
    "PROFILED_NOT_VERIFIED",
    "VERIFIED",
}
REQUIRED_KEYS = {
    "schema_version",
    "id",
    "display_name",
    "codename",
    "model_allowlist",
    "status",
    "flash_enabled",
    "firmware_baseline",
    "verified_partition_map",
    "validated_builds",
    "flash_operations",
    "recovery_evidence",
    "notes",
    "sources",
}


class ProfileError(ValueError):
    """Raised when a profile cannot be trusted even as metadata."""


@dataclass(frozen=True)
class DeviceProfile:
    profile_id: str
    display_name: str
    codename: str
    model_allowlist: tuple[str, ...]
    status: str
    firmware_baseline: str | None
    sources: tuple[str, ...]

    @property
    def flash_allowed(self) -> bool:
        # Schema v1 is deliberately non-executable.
        return False


def _text(value: object, field: str, *, token: bool = False, limit: int = 256) -> str:
    if not isinstance(value, str):
        raise ProfileError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise ProfileError(f"{field} has an invalid value.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ProfileError(f"{field} contains control characters.")
    if token and not TOKEN.fullmatch(value):
        raise ProfileError(f"{field} is not a safe token.")
    return value


def validate_profile(data: object) -> DeviceProfile:
    if not isinstance(data, dict):
        raise ProfileError("Profile root must be a JSON object.")
    keys = set(data)
    if keys != REQUIRED_KEYS:
        missing = REQUIRED_KEYS - keys
        extra = keys - REQUIRED_KEYS
        problem = "missing required fields" if missing else "unknown fields"
        raise ProfileError(f"Profile has {problem}; schema v1 is strict.")
    if data["schema_version"] != 1:
        raise ProfileError("Unsupported profile schema version.")

    profile_id = _text(data["id"], "id", limit=129)
    if not PROFILE_ID.fullmatch(profile_id):
        raise ProfileError("id must use vendor/codename safe-token form.")
    display_name = _text(data["display_name"], "display_name", limit=128)
    codename = _text(data["codename"], "codename", token=True)

    models = data["model_allowlist"]
    if not isinstance(models, list) or not models or len(models) > 64:
        raise ProfileError("model_allowlist must contain 1-64 entries.")
    model_allowlist = tuple(_text(item, "model_allowlist entry", token=True) for item in models)
    if len(set(model_allowlist)) != len(model_allowlist):
        raise ProfileError("model_allowlist contains duplicates.")

    status = _text(data["status"], "status")
    if status not in ALLOWED_STATUS:
        raise ProfileError("Unknown profile status.")

    if not isinstance(data["flash_enabled"], bool):
        raise ProfileError("flash_enabled must be boolean.")
    if data["flash_enabled"]:
        raise ProfileError("Schema v1 is metadata-only and cannot enable flashing.")
    if data["flash_operations"] != []:
        raise ProfileError("Schema v1 cannot contain executable flash operations.")

    baseline = data["firmware_baseline"]
    if baseline is not None:
        baseline = _text(baseline, "firmware_baseline", limit=256)

    if data["verified_partition_map"] is not None and not isinstance(data["verified_partition_map"], dict):
        raise ProfileError("verified_partition_map must be null or an object.")
    for field in ("validated_builds", "recovery_evidence"):
        value = data[field]
        if not isinstance(value, list) or len(value) > 256:
            raise ProfileError(f"{field} must be a bounded list.")
        for item in value:
            _text(item, f"{field} entry", limit=512)

    _text(data["notes"], "notes", limit=2048)
    sources = data["sources"]
    if not isinstance(sources, list) or not sources or len(sources) > 64:
        raise ProfileError("sources must contain 1-64 HTTPS URLs.")
    clean_sources: list[str] = []
    for source in sources:
        source = _text(source, "source", limit=512)
        if not source.startswith("https://"):
            raise ProfileError("Profile sources must use HTTPS.")
        clean_sources.append(source)

    return DeviceProfile(
        profile_id=profile_id,
        display_name=display_name,
        codename=codename,
        model_allowlist=model_allowlist,
        status=status,
        firmware_baseline=baseline,
        sources=tuple(clean_sources),
    )


def load_profile(path: Path) -> DeviceProfile:
    if not path.is_file() or path.name != "profile.json":
        raise ProfileError("Expected an existing profile.json file.")
    try:
        text = path.read_text(encoding="utf-8")
        if len(text) > 262144:
            raise ProfileError("Profile file is oversized.")
        data = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError("Profile could not be read as strict UTF-8 JSON.") from exc
    return validate_profile(data)


def discover_profiles(root: Path) -> list[DeviceProfile]:
    if not root.is_dir():
        raise ProfileError("Device profile root does not exist.")
    profiles = [load_profile(path) for path in sorted(root.rglob("profile.json"))]
    if not profiles:
        raise ProfileError("No device profiles were found.")
    seen_ids: set[str] = set()
    for profile in profiles:
        if profile.profile_id in seen_ids:
            raise ProfileError("Duplicate device profile id.")
        seen_ids.add(profile.profile_id)
    return profiles


def public_profile_summary(profile: DeviceProfile) -> dict[str, object]:
    return {
        "id": profile.profile_id,
        "display_name": profile.display_name,
        "codename": profile.codename,
        "model_allowlist": list(profile.model_allowlist),
        "status": profile.status,
        "firmware_baseline": profile.firmware_baseline,
        "flash_allowed": False,
        "sources": list(profile.sources),
    }
