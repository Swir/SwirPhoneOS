"""Read-only device profile registry for SwirPhoneOS.

Schema v1 is intentionally metadata-only. It cannot authorize flashing, claim a
verified handset, or carry evidence that would imply a supported device. A
future support-capable schema must be introduced explicitly together with the
physical evidence contract that can justify those stronger claims.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

PROFILE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}/[a-z0-9][a-z0-9._-]{0,63}\Z")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
V1_ALLOWED_STATUS = {"PLANNED_NOT_SUPPORTED", "PROFILED_NOT_VERIFIED"}
REQUIRED_KEYS = {
    "schema_version", "id", "display_name", "codename", "model_allowlist", "status",
    "flash_enabled", "firmware_baseline", "verified_partition_map", "validated_builds",
    "flash_operations", "recovery_evidence", "notes", "sources",
}
MAX_PROFILE_BYTES = 262_144
MAX_PROFILE_COUNT = 256


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
        return False


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


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
    if set(data) != REQUIRED_KEYS:
        raise ProfileError("Profile must match schema v1 exactly.")
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
    if status not in V1_ALLOWED_STATUS:
        raise ProfileError("Schema v1 cannot claim a verified or supported device status.")

    if not isinstance(data["flash_enabled"], bool):
        raise ProfileError("flash_enabled must be boolean.")
    if data["flash_enabled"]:
        raise ProfileError("Schema v1 is metadata-only and cannot enable flashing.")
    if data["flash_operations"] != []:
        raise ProfileError("Schema v1 cannot contain executable flash operations.")

    baseline = data["firmware_baseline"]
    if baseline is not None:
        baseline = _text(baseline, "firmware_baseline", limit=256)

    # These field names deliberately reserve space for a later evidence-backed
    # schema. In v1 they must remain empty so metadata cannot masquerade as
    # physical verification or tested recovery/build support.
    if data["verified_partition_map"] is not None:
        raise ProfileError("Schema v1 cannot claim a verified partition map.")
    if data["validated_builds"] != []:
        raise ProfileError("Schema v1 cannot claim validated device builds.")
    if data["recovery_evidence"] != []:
        raise ProfileError("Schema v1 cannot carry recovery verification evidence.")

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
    if len(set(clean_sources)) != len(clean_sources):
        raise ProfileError("Profile sources contain duplicates.")

    return DeviceProfile(
        profile_id=profile_id,
        display_name=display_name,
        codename=codename,
        model_allowlist=model_allowlist,
        status=status,
        firmware_baseline=baseline,
        sources=tuple(clean_sources),
    )


def load_profile_snapshot(path: Path) -> tuple[DeviceProfile, str]:
    """Load one exact regular profile file and return its raw-file SHA-256.

    The digest lets later evidence bind to the precise reviewed profile bytes
    rather than only to a mutable profile id.
    """
    if path.name != "profile.json" or path.is_symlink() or not path.is_file():
        raise ProfileError("Expected an existing regular non-symlink profile.json file.")
    try:
        size = path.stat().st_size
        if size <= 0 or size > MAX_PROFILE_BYTES:
            raise ProfileError("Profile file is empty or oversized.")
        raw = path.read_bytes()
        if len(raw) != size:
            raise ProfileError("Profile file changed while it was being read.")
        text = raw.decode("utf-8")
        data = json.loads(text, object_pairs_hook=_strict_object)
    except ProfileError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError("Profile could not be read as strict UTF-8 JSON.") from exc
    return validate_profile(data), hashlib.sha256(raw).hexdigest()


def load_profile(path: Path) -> DeviceProfile:
    profile, _ = load_profile_snapshot(path)
    return profile


def discover_profiles(root: Path) -> list[DeviceProfile]:
    if root.is_symlink() or not root.is_dir():
        raise ProfileError("Device profile root must be an existing regular directory, not a symlink.")
    paths = sorted(root.rglob("profile.json"))
    if not paths:
        raise ProfileError("No device profiles were found.")
    if len(paths) > MAX_PROFILE_COUNT:
        raise ProfileError("Device profile registry exceeds the bounded profile count.")

    profiles: list[DeviceProfile] = []
    seen_ids: set[str] = set()
    for path in paths:
        profile = load_profile(path)
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise ProfileError("Device profile escaped the registry root.") from exc
        if len(relative.parts) != 3 or relative.parts[-1] != "profile.json":
            raise ProfileError("Device profiles must use vendor/codename/profile.json layout.")
        expected_id = f"{relative.parts[0]}/{relative.parts[1]}"
        if profile.profile_id != expected_id:
            raise ProfileError("Device profile id does not match its vendor/codename registry path.")
        if profile.profile_id in seen_ids:
            raise ProfileError("Duplicate device profile id.")
        seen_ids.add(profile.profile_id)
        profiles.append(profile)
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
