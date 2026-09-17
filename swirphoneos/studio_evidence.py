"""Strict local evidence review helpers for SwirPhoneStudio.

This module performs no Android SDK or device I/O. It accepts only current
fail-closed SwirRoot-readiness or physical-device-validation reports, validates
their integrity, and exposes bounded summaries suitable for the desktop UI.
A reviewed report can never become authorization to write to a phone.
"""
from __future__ import annotations

import json
from pathlib import Path

from .device_physical_validation import (
    DevicePhysicalValidationError,
    validate_physical_validation_report,
)
from .swirroot_readiness import SwirRootReadinessError, validate_swirroot_readiness


class StudioEvidenceError(ValueError):
    """Raised when a local evidence file is unsafe, malformed or unsupported."""


_MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
_ROOT_SUMMARY_KEYS = {
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
_PHYSICAL_SUMMARY_KEYS = {
    "schema_version",
    "source",
    "validation_session_id",
    "profile_id",
    "target_build",
    "support_candidate_review_ready",
    "known_capability_failures",
    "missing_requirements",
    "support_status",
    "support_claim_allowed",
    "profile_promotion_allowed",
    "device_write_allowed",
    "root_allowed",
}


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StudioEvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_local_json(path: Path) -> dict[str, object]:
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
    if not isinstance(document, dict):
        raise StudioEvidenceError("Evidence JSON root must be an object.")
    return document


def load_swirroot_readiness(path: Path) -> dict[str, object]:
    """Load one regular local SwirRoot readiness JSON and validate it fail-closed."""
    document = _load_local_json(path)
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
    if set(summary) != _ROOT_SUMMARY_KEYS:
        raise StudioEvidenceError("Internal Studio readiness summary drifted from its contract.")
    if summary["hardware_root_authorized"] is not False:
        raise StudioEvidenceError("Correlation-only hardware evidence cannot authorize root.")
    if summary["transition_ready"] is not False or summary["device_write_allowed"] is not False:
        raise StudioEvidenceError("Studio readiness review cannot authorize a device mutation.")
    return summary


def load_public_swirroot_readiness_summary(path: Path) -> dict[str, object]:
    """Validate and summarize one local readiness report without device access."""
    return public_swirroot_readiness_summary(load_swirroot_readiness(path))


def load_device_physical_validation(path: Path) -> dict[str, object]:
    """Load one generated physical-validation bundle for local review only."""
    document = _load_local_json(path)
    try:
        return validate_physical_validation_report(document)
    except DevicePhysicalValidationError as exc:
        raise StudioEvidenceError("Evidence is not a valid physical-device validation report.") from exc


def public_device_physical_validation_summary(report: object) -> dict[str, object]:
    """Return a bounded, explicitly non-authorizing physical-support review summary."""
    try:
        validated = validate_physical_validation_report(report)
    except DevicePhysicalValidationError as exc:
        raise StudioEvidenceError("Evidence is not a valid physical-device validation report.") from exc
    summary = {
        "schema_version": 1,
        "source": "swirphoneos_studio_physical_validation_summary",
        "validation_session_id": validated["validation_session_id"],
        "profile_id": validated["profile_id"],
        "target_build": validated["target_build"],
        "support_candidate_review_ready": validated["support_candidate_review_ready"],
        "known_capability_failures": list(validated["known_capability_failures"]),
        "missing_requirements": list(validated["missing_requirements"]),
        "support_status": validated["support_status"],
        "support_claim_allowed": validated["support_claim_allowed"],
        "profile_promotion_allowed": validated["profile_promotion_allowed"],
        "device_write_allowed": validated["device_write_allowed"],
        "root_allowed": validated["root_allowed"],
    }
    if set(summary) != _PHYSICAL_SUMMARY_KEYS:
        raise StudioEvidenceError("Internal Studio physical-validation summary drifted from its contract.")
    for key in ("support_claim_allowed", "profile_promotion_allowed", "device_write_allowed", "root_allowed"):
        if summary[key] is not False:
            raise StudioEvidenceError("Studio physical-validation review cannot authorize support or device mutation.")
    if summary["support_status"] != "NOT_SUPPORTED":
        raise StudioEvidenceError("Schema-v1 physical review cannot display a promoted support status.")
    return summary


def load_public_device_physical_validation_summary(path: Path) -> dict[str, object]:
    """Validate and summarize one local physical-validation report without device access."""
    return public_device_physical_validation_summary(load_device_physical_validation(path))
