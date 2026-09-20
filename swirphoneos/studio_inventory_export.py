"""Deterministic, privacy-minimized export for SwirPhoneStudio device inventory.

The export format is intentionally diagnostic-only. It carries explicit negative
claims for physical verification, support and flashing authorization so a saved
inventory snapshot cannot be confused with beta/device acceptance evidence.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from .studio_device_inventory import DeviceInventoryEvidence, DeviceProfileHint


def build_inventory_bundle(
    evidence: DeviceInventoryEvidence,
    profile_hints: Iterable[DeviceProfileHint] = (),
) -> dict[str, object]:
    """Build a deterministic export bundle and reject detached/duplicate hints."""
    observation_keys = {
        (item.transport, item.identifier_sha256)
        for item in evidence.observations
    }
    seen: set[tuple[str, str]] = set()
    serialized_hints: list[dict[str, object]] = []
    for hint in profile_hints:
        key = (hint.transport, hint.identifier_sha256)
        if key not in observation_keys:
            raise ValueError("Profile hint does not belong to this inventory snapshot.")
        if key in seen:
            raise ValueError("Duplicate profile hint for one inventory observation.")
        seen.add(key)
        serialized_hints.append(hint.to_dict())

    serialized_hints.sort(
        key=lambda item: (
            str(item["transport"]),
            str(item["identifier_sha256"]),
        )
    )
    return {
        "schema_version": 1,
        "kind": "swirphoneos_read_only_device_inventory",
        "read_only": True,
        "physical_verification": False,
        "support_claim": False,
        "flash_allowed": False,
        "beta_gate_evidence": False,
        "inventory": evidence.to_dict(),
        "profile_hints": serialized_hints,
    }


def serialize_inventory_bundle(
    evidence: DeviceInventoryEvidence,
    profile_hints: Iterable[DeviceProfileHint] = (),
) -> bytes:
    """Serialize inventory evidence canonically for stable hashing and review."""
    payload = build_inventory_bundle(evidence, profile_hints)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        separators=(",", ": "),
    ) + "\n"
    return text.encode("utf-8")


def write_inventory_bundle(
    destination: Path,
    evidence: DeviceInventoryEvidence,
    profile_hints: Iterable[DeviceProfileHint] = (),
) -> str:
    """Create one evidence file without overwriting an existing path.

    Returns the SHA-256 of the exact UTF-8 bytes written. The caller must provide
    an absolute path under an already existing directory. Exclusive creation is
    deliberate so an older evidence artifact cannot be silently replaced.
    """
    if not destination.is_absolute():
        raise ValueError("Inventory evidence destination must be absolute.")
    parent = destination.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError("Inventory evidence parent directory must already exist.")

    payload = serialize_inventory_bundle(evidence, profile_hints)
    with destination.open("xb") as handle:
        handle.write(payload)
    return sha256(payload).hexdigest()
