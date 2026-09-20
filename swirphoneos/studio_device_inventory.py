"""Read-only connected-device inventory for SwirPhoneStudio.

This module is intentionally narrow: it may execute only the non-mutating
``adb devices -l`` and ``fastboot devices`` inventory commands after the owner
has supplied/reviewed local tool paths. Persistable evidence hashes transport
identifiers and can never satisfy a physical-device or support gate by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os
import subprocess
import sys
from typing import Callable, Iterable
import unicodedata

from .identity import assess_profile_hint
from .profiles import DeviceProfile

_MAX_OUTPUT_CHARS = 256 * 1024
_MAX_FIELD_CHARS = 128
_DEFAULT_TIMEOUT_SECONDS = 8.0
_ALLOWED_COMMANDS: dict[str, tuple[str, ...]] = {
    "adb": ("devices", "-l"),
    "fastboot": ("devices",),
}
_ALLOWED_ATTRIBUTES = frozenset({"product", "model", "device"})


@dataclass(frozen=True, order=True)
class DeviceObservation:
    """One privacy-minimized transport observation."""

    transport: str
    identifier_sha256: str
    state: str
    product: str = ""
    model: str = ""
    device: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "transport": self.transport,
            "identifier_sha256": self.identifier_sha256,
            "state": self.state,
            "product": self.product,
            "model": self.model,
            "device": self.device,
        }


@dataclass(frozen=True)
class DeviceInventoryEvidence:
    """Bounded read-only evidence that explicitly carries no support claim."""

    observations: tuple[DeviceObservation, ...]
    adb_attempted: bool
    fastboot_attempted: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "read_only": True,
            "physical_verification": False,
            "support_claim": False,
            "adb_attempted": self.adb_attempted,
            "fastboot_attempted": self.fastboot_attempted,
            "observation_count": len(self.observations),
            "observations": [item.to_dict() for item in self.observations],
        }


@dataclass(frozen=True)
class DeviceProfileHint:
    """Non-authoritative profile assessment for one inventory observation."""

    transport: str
    identifier_sha256: str
    result: str
    candidate_profile_id: str | None
    candidate_display_name: str | None
    profile_status: str | None
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "transport": self.transport,
            "identifier_sha256": self.identifier_sha256,
            "result": self.result,
            "candidate_profile_id": self.candidate_profile_id,
            "candidate_display_name": self.candidate_display_name,
            "profile_status": self.profile_status,
            "evidence": list(self.evidence),
            "identity_verified": False,
            "physical_verification": False,
            "swirphoneos_support": "NOT_VALIDATED",
            "support_claim": False,
            "flash_allowed": False,
        }


def _clean_field(value: str, *, limit: int = _MAX_FIELD_CHARS) -> str:
    # Transport metadata is untrusted display text. Remove Unicode control,
    # bidi-format and other invisible control categories before whitespace
    # normalization so logs/GUI text cannot be visually spoofed by a device.
    visible = "".join(" " if unicodedata.category(char).startswith("C") else char for char in value)
    collapsed = " ".join(visible.split())
    return collapsed[:limit]


def _identifier_digest(identifier: str) -> str:
    return sha256(identifier.encode("utf-8", errors="replace")).hexdigest()


def _validated_tool(path: Path, tool: str, platform_name: str) -> Path:
    if tool not in _ALLOWED_COMMANDS:
        raise ValueError("Unsupported inventory transport.")
    if not path.is_absolute():
        raise ValueError("SDK tool path must be absolute.")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("SDK tool path is not available.") from exc
    if not resolved.is_file():
        raise ValueError("SDK tool path is not a file.")

    expected = f"{tool}.exe" if platform_name == "win32" else tool
    if platform_name == "win32":
        name_matches = resolved.name.casefold() == expected.casefold()
    else:
        name_matches = resolved.name == expected and os.access(resolved, os.X_OK)
    if not name_matches:
        raise ValueError("SDK tool does not match the requested transport.")
    return resolved


def _run_inventory(
    path: Path,
    tool: str,
    *,
    platform_name: str,
    timeout_seconds: float,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    executable = _validated_tool(path, tool, platform_name)
    command = [str(executable), *_ALLOWED_COMMANDS[tool]]
    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"{tool} inventory timed out.") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"{tool} inventory failed with exit code {completed.returncode}.")
    output = completed.stdout or ""
    if len(output) > _MAX_OUTPUT_CHARS:
        raise ValueError(f"{tool} inventory output exceeded the safety limit.")
    return output


def parse_adb_devices(output: str) -> tuple[DeviceObservation, ...]:
    """Parse ``adb devices -l`` without retaining raw serial identifiers."""
    observations: dict[str, DeviceObservation] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices attached") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        identifier, state = parts[0], _clean_field(parts[1], limit=32)
        if not identifier or not state:
            continue
        attrs: dict[str, str] = {}
        for token in parts[2:]:
            key, separator, value = token.partition(":")
            if separator and key in _ALLOWED_ATTRIBUTES:
                attrs[key] = _clean_field(value)
        digest = _identifier_digest(identifier)
        observations[digest] = DeviceObservation(
            transport="adb",
            identifier_sha256=digest,
            state=state,
            product=attrs.get("product", ""),
            model=attrs.get("model", ""),
            device=attrs.get("device", ""),
        )
    return tuple(sorted(observations.values()))


def parse_fastboot_devices(output: str) -> tuple[DeviceObservation, ...]:
    """Parse ``fastboot devices`` without retaining raw serial identifiers."""
    observations: dict[str, DeviceObservation] = {}
    for raw_line in output.splitlines():
        parts = raw_line.split()
        if not parts:
            continue
        identifier = parts[0]
        state = _clean_field(parts[1], limit=32) if len(parts) > 1 else "fastboot"
        digest = _identifier_digest(identifier)
        observations[digest] = DeviceObservation(
            transport="fastboot",
            identifier_sha256=digest,
            state=state or "fastboot",
        )
    return tuple(sorted(observations.values()))


def _profile_match_value(value: str) -> str | None:
    """Return only ASCII inventory metadata to the conservative profile matcher."""
    if not value or not value.isascii():
        return None
    return value


def assess_inventory_profiles(
    evidence: DeviceInventoryEvidence,
    profiles: Iterable[DeviceProfile],
) -> tuple[DeviceProfileHint, ...]:
    """Assess read-only observations against metadata profiles without trust promotion.

    Profile matches remain hints only. They never establish physical identity,
    device support or permission to install, unlock, root, erase, flash or
    restore. Fastboot inventory alone normally has no product metadata and
    therefore remains ``NO_PROFILE_HINT`` until richer read-only diagnostics are
    deliberately collected through the existing capture workflow.
    """
    profile_snapshot = tuple(profiles)
    assessments: list[DeviceProfileHint] = []
    for item in evidence.observations:
        if item.transport == "adb":
            report: dict[str, object] = {
                "codename": _profile_match_value(item.device or item.product),
                "model": _profile_match_value(item.model),
            }
        elif item.transport == "fastboot":
            report = {
                "product_reported": _profile_match_value(item.product or item.device),
            }
        else:
            raise ValueError("Unsupported inventory transport.")

        assessment = assess_profile_hint(item.transport, report, profile_snapshot)
        result = assessment["result"]
        candidate_profile_id = assessment["candidate_profile_id"]
        candidate_display_name = assessment["candidate_display_name"]
        profile_status = assessment["profile_status"]
        match_evidence = assessment["evidence"]
        if (
            not isinstance(result, str)
            or candidate_profile_id is not None and not isinstance(candidate_profile_id, str)
            or candidate_display_name is not None and not isinstance(candidate_display_name, str)
            or profile_status is not None and not isinstance(profile_status, str)
            or not isinstance(match_evidence, list)
            or not all(isinstance(value, str) for value in match_evidence)
        ):
            raise ValueError("Profile assessment returned an invalid shape.")
        assessments.append(
            DeviceProfileHint(
                transport=item.transport,
                identifier_sha256=item.identifier_sha256,
                result=result,
                candidate_profile_id=candidate_profile_id,
                candidate_display_name=candidate_display_name,
                profile_status=profile_status,
                evidence=tuple(match_evidence),
            )
        )
    return tuple(assessments)


def collect_device_inventory(
    *,
    adb_path: Path | None = None,
    fastboot_path: Path | None = None,
    platform_name: str | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> DeviceInventoryEvidence:
    """Collect explicit, read-only transport presence evidence.

    No command is executed for a transport whose path is omitted. The only
    permitted argv suffixes are ``devices -l`` for ADB and ``devices`` for
    Fastboot. The result is diagnostic evidence only and cannot promote device
    support or count as physical verification.
    """
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ValueError("Inventory timeout must be within (0, 60] seconds.")
    platform_value = sys.platform if platform_name is None else platform_name
    observations: list[DeviceObservation] = []

    if adb_path is not None:
        observations.extend(
            parse_adb_devices(
                _run_inventory(
                    adb_path,
                    "adb",
                    platform_name=platform_value,
                    timeout_seconds=timeout_seconds,
                    runner=runner,
                )
            )
        )
    if fastboot_path is not None:
        observations.extend(
            parse_fastboot_devices(
                _run_inventory(
                    fastboot_path,
                    "fastboot",
                    platform_name=platform_value,
                    timeout_seconds=timeout_seconds,
                    runner=runner,
                )
            )
        )

    return DeviceInventoryEvidence(
        observations=tuple(sorted(observations)),
        adb_attempted=adb_path is not None,
        fastboot_attempted=fastboot_path is not None,
    )
