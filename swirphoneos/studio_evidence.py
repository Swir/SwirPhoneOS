"""Strict local evidence review helpers for SwirPhoneStudio.

This module performs no Android SDK or device I/O. It accepts only current
fail-closed evidence projections, validates their integrity, and exposes
bounded summaries suitable for the desktop UI. A reviewed report can never
become authorization to write to a phone, claim device support, or enable
SwirRoot.
"""
from __future__ import annotations

import json
from pathlib import Path

from .device_support_readiness import (
    DeviceSupportReadinessError,
    validate_device_support_readiness,
)
from .swirroot_readiness import SwirRootReadinessError, validate_swirroot_readiness


class StudioEvidenceError(ValueError):
    """Raised when a local evidence file is unsafe, malformed or unsupported."""


_MAX_EVIDENCE_BYTES = 262_144
_SWIRROOT_SUMMARY_KEYS = {
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
_DEVICE_SUPPORT_SUMMARY_KEYS = {
    "schema_version",
    "source",
    "profile_id",
    "profile_status",
    "device_model",
    "device_codename",
    "observed_current_build",
    "target_build",
    "missing_requirements",
    "capability_status",
    "support_status",
    "support_claim_allowed",
    "profile_promotion_allowed",
    "install_allowed",
    "device_write_allowed",
    "root_allowed",
    "evidence_sha256",
}


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StudioEvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_local_json(path: Path) -> object:
    """Read one bounded regular UTF-8 JSON file without resolving symlinks."""
    if not path.is_absolute():
        raise StudioEvidenceError("Evidence path must be absolute.")
    if path.suffix.lower() != ".json":
        raise StudioEvidenceError("Evidence file must use the .json extension.")
    if not path.is_file() or path.is_symlink():
        raise StudioEvidenceError("Evidence must be an existing regular file, not a symlink.")
    try:
        if path.stat().st_size > _MAX_EVIDENCE_BYTES:
            raise StudioEvidenceError("Evidence file is oversized.")
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except StudioEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StudioEvidenceError("Evidence file could not be read as strict UTF-8 JSON.") from exc


def load_swirroot_readiness(path: Path) -> dict[str, object]:
    """Load one local SwirRoot readiness report and validate it fail-closed."""
    try:
        return validate_swirroot_readiness(_load_local_json(path))
    except SwirRootReadinessError as exc:
        raise StudioEvidenceError("Evidence is not a valid SwirRoot readiness report.") from exc


def public_swirroot_readiness_summary(report: object) -> dict[str, object]:
    """Return only bounded SwirRoot readiness fields needed by the read-only UI."""
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
    if set(summary) != _SWIRROOT_SUMMARY_KEYS:
        raise StudioEvidenceError("Internal Studio readiness summary drifted from its contract.")
    if summary["hardware_root_authorized"] is not False:
        raise StudioEvidenceError("Correlation-only hardware evidence cannot authorize root.")
    if summary["transition_ready"] is not False or summary["device_write_allowed"] is not False:
        raise StudioEvidenceError("Studio readiness review cannot authorize a device mutation.")
    return summary


def load_public_swirroot_readiness_summary(path: Path) -> dict[str, object]:
    """Validate and summarize one local SwirRoot report without device access."""
    return public_swirroot_readiness_summary(load_swirroot_readiness(path))


def load_device_support_readiness(path: Path) -> dict[str, object]:
    """Load one local support-readiness report without device access."""
    try:
        return validate_device_support_readiness(_load_local_json(path))
    except DeviceSupportReadinessError as exc:
        raise StudioEvidenceError("Evidence is not a valid device support readiness report.") from exc


def public_device_support_readiness_summary(report: object) -> dict[str, object]:
    """Create a bounded, explicitly non-authorizing support review projection."""
    try:
        validated = validate_device_support_readiness(report)
    except DeviceSupportReadinessError as exc:
        raise StudioEvidenceError("Evidence is not a valid device support readiness report.") from exc
    summary = {
        "schema_version": 1,
        "source": "swirphoneos_studio_device_support_readiness_summary",
        "profile_id": validated["profile_id"],
        "profile_status": validated["profile_status"],
        "device_model": validated["device_model"],
        "device_codename": validated["device_codename"],
        "observed_current_build": validated["observed_current_build"],
        "target_build": validated["target_build"],
        "missing_requirements": list(validated["missing_requirements"]),
        "capability_status": dict(validated["capability_status"]),
        "support_status": validated["support_status"],
        "support_claim_allowed": validated["support_claim_allowed"],
        "profile_promotion_allowed": validated["profile_promotion_allowed"],
        "install_allowed": validated["install_allowed"],
        "device_write_allowed": validated["device_write_allowed"],
        "root_allowed": validated["root_allowed"],
        "evidence_sha256": validated["evidence_sha256"],
    }
    if set(summary) != _DEVICE_SUPPORT_SUMMARY_KEYS:
        raise StudioEvidenceError("Internal Studio device support summary drifted from its contract.")
    if summary["support_status"] != "NOT_SUPPORTED" or summary["support_claim_allowed"] is not False:
        raise StudioEvidenceError("Preparation-only evidence cannot claim device support.")
    for field in ("profile_promotion_allowed", "install_allowed", "device_write_allowed", "root_allowed"):
        if summary[field] is not False:
            raise StudioEvidenceError("Studio device support review cannot authorize a device mutation.")
    return summary


def load_public_device_support_readiness_summary(path: Path) -> dict[str, object]:
    """Validate and summarize one local support-readiness report without device I/O."""
    return public_device_support_readiness_summary(load_device_support_readiness(path))
