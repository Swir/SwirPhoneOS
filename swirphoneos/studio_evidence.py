"""Strict local evidence review helpers for SwirPhoneStudio.

This module performs no Android SDK or device I/O. It accepts only the current
fail-closed SwirRoot readiness projection, validates its integrity, and exposes
a bounded summary suitable for the desktop UI. A reviewed report can never
become authorization to write to a phone.
"""
from __future__ import annotations

import json
from pathlib import Path

from .swirroot_readiness import SwirRootReadinessError, validate_swirroot_readiness


class StudioEvidenceError(ValueError):
    """Raised when a local evidence file is unsafe, malformed or unsupported."""


_MAX_EVIDENCE_BYTES = 262_144
_SUMMARY_KEYS = {
    "schema_version",
    "source",
    "action",
    "profile_id",
    "exact_build",
    "transaction_id",
    "missing_requirements",
    "policy_backend_available",
    "hardware_root_authorized",
    "transition_ready",
    "device_write_allowed",
}


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StudioEvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_swirroot_readiness(path: Path) -> dict[str, object]:
    """Load one regular local JSON evidence file and validate it fail-closed."""
    if not path.is_absolute():
        raise StudioEvidenceError("Evidence path must be absolute.")
    if path.suffix.lower() != ".json":
        raise StudioEvidenceError("Evidence file must use the .json extension.")
    if not path.is_file() or path.is_symlink():
        raise StudioEvidenceError("Evidence must be an existing regular file, not a symlink.")
    try:
        if path.stat().st_size > _MAX_EVIDENCE_BYTES:
            raise StudioEvidenceError("Evidence file is oversized.")
        document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except StudioEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StudioEvidenceError("Evidence file could not be read as strict UTF-8 JSON.") from exc
    try:
        return validate_swirroot_readiness(document)
    except SwirRootReadinessError as exc:
        raise StudioEvidenceError("Evidence is not a valid SwirRoot readiness report.") from exc


def public_swirroot_readiness_summary(report: object) -> dict[str, object]:
    """Return only bounded readiness fields needed by the read-only Studio UI."""
    try:
        validated = validate_swirroot_readiness(report)
    except SwirRootReadinessError as exc:
        raise StudioEvidenceError("Evidence is not a valid SwirRoot readiness report.") from exc
    summary = {
        "schema_version": 1,
        "source": "swirphoneos_studio_swirroot_readiness_summary",
        "action": validated["action"],
        "profile_id": validated["profile_id"],
        "exact_build": validated["exact_build"],
        "transaction_id": validated["transaction_id"],
        "missing_requirements": list(validated["missing_requirements"]),
        "policy_backend_available": validated["policy_backend_available"],
        "hardware_root_authorized": validated["hardware_root_authorized"],
        "transition_ready": validated["transition_ready"],
        "device_write_allowed": validated["device_write_allowed"],
    }
    if set(summary) != _SUMMARY_KEYS:
        raise StudioEvidenceError("Internal Studio readiness summary drifted from its contract.")
    if summary["hardware_root_authorized"] is not False:
        raise StudioEvidenceError("Correlation-only hardware evidence cannot authorize root.")
    if summary["transition_ready"] is not False or summary["device_write_allowed"] is not False:
        raise StudioEvidenceError("Studio readiness review cannot authorize a device mutation.")
    return summary


def load_public_swirroot_readiness_summary(path: Path) -> dict[str, object]:
    """Validate and summarize one local readiness report without device access."""
    return public_swirroot_readiness_summary(load_swirroot_readiness(path))
