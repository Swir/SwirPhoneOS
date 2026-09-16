"""Conservative profile hints for read-only device diagnostics.

Device-reported ADB/Fastboot values are never treated as trusted hardware
identity and this module can never authorize flashing.
"""
from __future__ import annotations

from typing import Iterable

from .profiles import DeviceProfile

_TRANSPORTS = {"adb", "fastboot"}
_ASSESSMENT_KEYS = {
    "schema_version", "result", "candidate_profile_id", "candidate_display_name",
    "profile_status", "evidence", "identity_verified", "swirphoneos_support",
    "flash_allowed",
}
_REPORT_KEYS = {
    "schema_version", "source", "transport", "transport_report",
    "profile_assessment", "flash_allowed", "warnings",
}


class IdentityAssessmentError(ValueError):
    """Raised when a combined read-only report violates the safety contract."""


def _safe_observation(report: dict[str, object], key: str) -> str | None:
    value = report.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 256 or not value.isascii():
        raise IdentityAssessmentError("Reported identity field is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise IdentityAssessmentError("Reported identity field contains control characters.")
    return value


def _profile_evidence(transport: str, report: dict[str, object], profile: DeviceProfile) -> tuple[str, ...]:
    evidence: list[str] = []
    if transport == "adb":
        codename = _safe_observation(report, "codename")
        model = _safe_observation(report, "model")
        if codename and codename.casefold() == profile.codename.casefold():
            evidence.append("adb_codename_matches_profile_codename")
        if model and any(model.casefold() == item.casefold() for item in profile.model_allowlist):
            evidence.append("adb_model_matches_profile_allowlist")
    elif transport == "fastboot":
        product = _safe_observation(report, "product_reported")
        if product and product.casefold() == profile.codename.casefold():
            evidence.append("fastboot_product_matches_profile_codename")
        if product and any(product.casefold() == item.casefold() for item in profile.model_allowlist):
            evidence.append("fastboot_product_matches_profile_allowlist")
    else:
        raise IdentityAssessmentError("Unsupported diagnostic transport.")
    return tuple(evidence)


def assess_profile_hint(
    transport: str,
    report: dict[str, object],
    profiles: Iterable[DeviceProfile],
) -> dict[str, object]:
    """Return at most one metadata profile hint without asserting identity/support."""
    if transport not in _TRANSPORTS:
        raise IdentityAssessmentError("Unsupported diagnostic transport.")
    candidates: list[tuple[DeviceProfile, tuple[str, ...]]] = []
    for profile in profiles:
        evidence = _profile_evidence(transport, report, profile)
        if evidence:
            candidates.append((profile, evidence))

    if not candidates:
        result = "NO_PROFILE_HINT"
        profile = None
        evidence: tuple[str, ...] = ()
    elif len(candidates) > 1:
        result = "AMBIGUOUS_PROFILE_HINT"
        profile = None
        evidence = ()
    else:
        result = "PROFILE_HINT_ONLY"
        profile, evidence = candidates[0]

    return {
        "schema_version": 1,
        "result": result,
        "candidate_profile_id": profile.profile_id if profile else None,
        "candidate_display_name": profile.display_name if profile else None,
        "profile_status": profile.status if profile else None,
        "evidence": list(evidence),
        "identity_verified": False,
        "swirphoneos_support": "NOT_VALIDATED",
        "flash_allowed": False,
    }


def build_unified_report(
    transport: str,
    transport_report: dict[str, object],
    profiles: Iterable[DeviceProfile],
) -> dict[str, object]:
    """Combine one read-only transport report with non-authoritative profile hints."""
    if transport not in _TRANSPORTS:
        raise IdentityAssessmentError("Unsupported diagnostic transport.")
    if transport_report.get("flash_allowed") is not False:
        raise IdentityAssessmentError("Transport report must remain non-authorizing.")
    if transport_report.get("swirphoneos_support") != "NOT_VALIDATED":
        raise IdentityAssessmentError("Transport report cannot claim SwirPhoneOS support.")
    assessment = assess_profile_hint(transport, transport_report, profiles)
    report = {
        "schema_version": 2,
        "source": "swirphoneos_read_only_transport_plus_profile_hint",
        "transport": transport,
        "transport_report": transport_report,
        "profile_assessment": assessment,
        "flash_allowed": False,
        "warnings": [
            "Device-reported values and profile matches are hints only, not hardware identity proof.",
            "No profile hint can authorize installation, root, unlock, erase, flash or restore.",
            "A supported build requires independent firmware, partition, recovery and physical-device evidence.",
        ],
    }
    validate_unified_report(report)
    return report


def validate_unified_report(report: object) -> None:
    if not isinstance(report, dict) or set(report) != _REPORT_KEYS:
        raise IdentityAssessmentError("Unified report must match schema v2 exactly.")
    if report["schema_version"] != 2 or report["source"] != "swirphoneos_read_only_transport_plus_profile_hint":
        raise IdentityAssessmentError("Unified report provenance is invalid.")
    if report["transport"] not in _TRANSPORTS or report["flash_allowed"] is not False:
        raise IdentityAssessmentError("Unified report transport/safety fields are invalid.")
    transport_report = report["transport_report"]
    if not isinstance(transport_report, dict):
        raise IdentityAssessmentError("Unified transport report is invalid.")
    if transport_report.get("flash_allowed") is not False or transport_report.get("swirphoneos_support") != "NOT_VALIDATED":
        raise IdentityAssessmentError("Nested transport report changed the safety contract.")

    assessment = report["profile_assessment"]
    if not isinstance(assessment, dict) or set(assessment) != _ASSESSMENT_KEYS:
        raise IdentityAssessmentError("Profile assessment must match schema v1 exactly.")
    if assessment["schema_version"] != 1:
        raise IdentityAssessmentError("Unsupported profile assessment schema.")
    if assessment["result"] not in {"NO_PROFILE_HINT", "AMBIGUOUS_PROFILE_HINT", "PROFILE_HINT_ONLY"}:
        raise IdentityAssessmentError("Unknown profile assessment result.")
    if assessment["identity_verified"] is not False or assessment["flash_allowed"] is not False:
        raise IdentityAssessmentError("Profile assessment cannot verify identity or authorize flashing.")
    if assessment["swirphoneos_support"] != "NOT_VALIDATED":
        raise IdentityAssessmentError("Profile assessment cannot claim support.")
    evidence = assessment["evidence"]
    if not isinstance(evidence, list) or len(evidence) > 8 or not all(isinstance(item, str) and item for item in evidence):
        raise IdentityAssessmentError("Profile assessment evidence is invalid.")
    candidate_fields = (
        assessment["candidate_profile_id"], assessment["candidate_display_name"], assessment["profile_status"]
    )
    if assessment["result"] == "PROFILE_HINT_ONLY":
        if not all(isinstance(value, str) and value for value in candidate_fields) or not evidence:
            raise IdentityAssessmentError("Profile hint is incomplete.")
    elif any(value is not None for value in candidate_fields) or evidence:
        raise IdentityAssessmentError("Non-unique profile assessment cannot expose a candidate.")

    warnings = report["warnings"]
    if not isinstance(warnings, list) or len(warnings) != 3 or not all(isinstance(item, str) and item for item in warnings):
        raise IdentityAssessmentError("Unified warnings are invalid.")
