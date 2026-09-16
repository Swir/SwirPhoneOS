"""Offline, read-only assessment. Android properties are hints, not trusted identity."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_JSON_BYTES = 1_048_576
PROFILE_KEYS = {"schema_version", "id", "codename", "models", "abi", "support_status"}
REQUIRED_PROPERTIES = (
    "ro.product.device", "ro.product.model", "ro.product.cpu.abilist",
    "ro.treble.enabled", "ro.boot.flash.locked",
)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("Non-finite JSON number.")


def load_json(path: Path) -> dict[str, object]:
    """Bounded JSON input; duplicate keys and non-standard numbers are rejected."""
    with path.open("rb") as stream:
        data = stream.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON input exceeds the size limit.")
    result = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                        parse_constant=_reject_constant)
    if not isinstance(result, dict):
        raise ValueError("A JSON object is required.")
    return result


@dataclass(frozen=True)
class DeviceProfile:
    id: str
    codename: str
    models: tuple[str, ...]
    abi: str

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> DeviceProfile:
        if set(data) != PROFILE_KEYS:
            raise ValueError("Invalid profile fields.")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError("Unsupported profile schema.")
        if data["support_status"] != "PLANNED":
            raise ValueError("Only unvalidated PLANNED profiles are supported by this prototype.")
        for key in ("id", "codename", "abi"):
            value = data[key]
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_/-]{0,79}", value):
                raise ValueError("Invalid profile identifier.")
        models = data["models"]
        if not isinstance(models, list) or not models or len(models) > 32:
            raise ValueError("A non-empty model list is required.")
        if any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,79}", v) for v in models):
            raise ValueError("Invalid model name.")
        if len(models) != len(set(models)):
            raise ValueError("Duplicate model name.")
        return cls(str(data["id"]), str(data["codename"]), tuple(models), str(data["abi"]))


@dataclass(frozen=True)
class Assessment:
    profile_id: str
    identity_hint_matches: bool
    architecture_hint_matches: bool
    treble_hint: bool | None
    unlocked_hint: bool | None
    blockers: tuple[str, ...]

    @property
    def write_operations_allowed(self) -> bool:
        """No host-side JSON input can enable a destructive operation."""
        return False

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["write_operations_allowed"] = False
        result["scope"] = "OFFLINE_PROPERTY_HINTS_ONLY"
        return result


def assess(properties: Mapping[str, object], profile: DeviceProfile) -> Assessment:
    """Evaluate an exported property object without running ADB or Fastboot."""
    for key in REQUIRED_PROPERTIES:
        value = properties.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 for c in value)):
            raise ValueError("Invalid device property value.")
    identity = (properties.get("ro.product.device") == profile.codename
                and properties.get("ro.product.model") in profile.models)
    abis = properties.get("ro.product.cpu.abilist") or ""
    architecture = profile.abi in [part.strip() for part in abis.split(",")]
    treble = {"true": True, "false": False}.get(properties.get("ro.treble.enabled"))
    unlocked = {"0": True, "1": False}.get(properties.get("ro.boot.flash.locked"))
    blockers: list[str] = []
    for condition, code in (
        (identity, "DEVICE_IDENTITY_UNCONFIRMED"),
        (architecture, "CPU_ARCHITECTURE_UNCONFIRMED"),
        (treble is True, "TREBLE_UNCONFIRMED"),
        (unlocked is True, "BOOTLOADER_UNLOCK_UNCONFIRMED"),
    ):
        if not condition:
            blockers.append(code)
    blockers.extend(("PHYSICAL_IDENTITY_NOT_VERIFIED", "FIRMWARE_BASELINE_NOT_VALIDATED",
                     "HARDWARE_VALIDATION_MISSING", "RECOVERY_NOT_VALIDATED",
                     "IMAGE_AUTHENTICITY_NOT_VERIFIED", "WRITE_BACKEND_NOT_IMPLEMENTED"))
    return Assessment(profile.id, identity, architecture, treble, unlocked, tuple(blockers))
