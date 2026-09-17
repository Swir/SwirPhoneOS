"""Fail-closed correlation of read-only ADB and Fastboot observations.

This module never contacts a device. It validates two previously captured
`inspect-device` JSON reports, correlates their non-secret reported identity,
and can compare the result with a preparation-only transaction plan.
Correlation is useful evidence, but it is explicitly not hardware verification
and can never authorize flashing, root, unlock or any write.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from .identity import IdentityAssessmentError, validate_unified_report
from .profiles import DeviceProfile
from .transaction_evidence import TransactionPlan

MAX_JSON_BYTES = 1024 * 1024
REPORT_KEYS = {
    "schema_version", "source", "state", "profile_id", "profile_status",
    "adb_model_reported", "adb_codename_reported", "adb_build_fingerprint_reported",
    "adb_slot_reported", "fastboot_product_reported", "fastboot_slot_reported",
    "partition_hints_reported", "correlations", "hardware_verified",
    "swirphoneos_support", "write_allowed", "flash_allowed", "root_allowed",
    "evidence_sha256", "warnings",
}


class HardwareEvidenceError(ValueError):
    """Raised when read-only cross-transport evidence is incomplete or contradictory."""


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise HardwareEvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_report(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise HardwareEvidenceError("Evidence input must be an existing regular JSON file.")
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise HardwareEvidenceError("Evidence input is oversized.")
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except HardwareEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HardwareEvidenceError("Evidence input could not be read as strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise HardwareEvidenceError("Evidence input root must be a JSON object.")
    return value


def _text(value: object, field: str, *, optional: bool = False, limit: int = 512) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise HardwareEvidenceError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise HardwareEvidenceError(f"{field} has an invalid value.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise HardwareEvidenceError(f"{field} contains control characters.")
    return value


def _candidate(report: dict[str, object], transport: str) -> tuple[str, str]:
    try:
        validate_unified_report(report)
    except IdentityAssessmentError as exc:
        raise HardwareEvidenceError("Unified transport report failed validation.") from exc
    if report.get("transport") != transport:
        raise HardwareEvidenceError(f"Expected a {transport} unified report.")
    assessment = report.get("profile_assessment")
    if not isinstance(assessment, dict) or assessment.get("result") != "PROFILE_HINT_ONLY":
        raise HardwareEvidenceError("A unique metadata profile hint is required from both transports.")
    profile_id = _text(assessment.get("candidate_profile_id"), "candidate_profile_id", limit=129)
    profile_status = _text(assessment.get("profile_status"), "profile_status", limit=64)
    assert profile_id is not None and profile_status is not None
    return profile_id, profile_status


def _slot_from_adb(transport: dict[str, object]) -> str | None:
    direct = _text(transport.get("slot_reported"), "adb slot", optional=True, limit=16)
    suffix = _text(transport.get("slot_suffix_reported"), "adb slot suffix", optional=True, limit=16)
    if direct is not None:
        direct = direct.removeprefix("_")
    if suffix is not None:
        suffix = suffix.removeprefix("_")
    if direct and suffix and direct != suffix:
        raise HardwareEvidenceError("ADB slot and slot suffix contradict each other.")
    return direct or suffix


def _partition_hints(value: object) -> list[dict[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 64:
        raise HardwareEvidenceError("Fastboot partition hints must be a bounded list.")
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"name", "has_slot_reported", "size_bytes_reported"}:
            raise HardwareEvidenceError("Fastboot partition hint schema is invalid.")
        name = _text(item["name"], "partition name", limit=64)
        assert name is not None
        if name in seen:
            raise HardwareEvidenceError("Fastboot partition hints contain duplicates.")
        seen.add(name)
        has_slot = item["has_slot_reported"]
        size = item["size_bytes_reported"]
        if has_slot is not None and type(has_slot) is not bool:
            raise HardwareEvidenceError("Partition slot hint must be boolean or null.")
        if size is not None and (type(size) is not int or size <= 0 or size > 16 * 1024**4):
            raise HardwareEvidenceError("Partition size hint is invalid.")
        result.append({"name": name, "has_slot_reported": has_slot, "size_bytes_reported": size})
    return result


def _profile_by_id(profiles: Iterable[DeviceProfile], profile_id: str) -> DeviceProfile:
    matches = [profile for profile in profiles if profile.profile_id == profile_id]
    if len(matches) != 1:
        raise HardwareEvidenceError("Correlated profile id is not uniquely present in the local registry.")
    return matches[0]


def create_hardware_evidence(
    adb_unified: dict[str, object],
    fastboot_unified: dict[str, object],
    profiles: Iterable[DeviceProfile],
) -> dict[str, object]:
    """Correlate two read-only observations without claiming physical identity."""
    adb_profile_id, adb_profile_status = _candidate(adb_unified, "adb")
    fastboot_profile_id, fastboot_profile_status = _candidate(fastboot_unified, "fastboot")
    if adb_profile_id != fastboot_profile_id or adb_profile_status != fastboot_profile_status:
        raise HardwareEvidenceError("ADB and Fastboot reports do not point to the same profile metadata.")
    profile = _profile_by_id(profiles, adb_profile_id)
    if profile.status != adb_profile_status:
        raise HardwareEvidenceError("Profile status changed after the observations were captured.")

    adb = adb_unified.get("transport_report")
    fastboot = fastboot_unified.get("transport_report")
    if not isinstance(adb, dict) or not isinstance(fastboot, dict):
        raise HardwareEvidenceError("Nested transport reports are missing.")

    model = _text(adb.get("model"), "ADB model", limit=128)
    codename = _text(adb.get("codename"), "ADB codename", limit=128)
    fingerprint = _text(adb.get("build_fingerprint_reported"), "ADB build fingerprint", limit=512)
    product = _text(fastboot.get("product_reported"), "Fastboot product", limit=128)
    assert model is not None and codename is not None and fingerprint is not None and product is not None

    if codename.casefold() != profile.codename.casefold() or product.casefold() != profile.codename.casefold():
        raise HardwareEvidenceError("ADB/Fastboot codename correlation failed.")
    if not any(model.casefold() == item.casefold() for item in profile.model_allowlist):
        raise HardwareEvidenceError("ADB model is outside the profile allowlist.")

    adb_slot = _slot_from_adb(adb)
    fastboot_slot = _text(fastboot.get("current_slot_reported"), "Fastboot current slot", optional=True, limit=16)
    if fastboot_slot is not None:
        fastboot_slot = fastboot_slot.removeprefix("_")
    if adb_slot and fastboot_slot and adb_slot != fastboot_slot:
        raise HardwareEvidenceError("ADB and Fastboot current-slot observations disagree.")

    adb_bootloader = _text(adb.get("bootloader_reported"), "ADB bootloader state", optional=True, limit=32)
    fastboot_bootloader = _text(fastboot.get("bootloader_reported"), "Fastboot bootloader state", optional=True, limit=32)
    if adb_bootloader not in {None, "unknown"} and fastboot_bootloader not in {None, "unknown"} and adb_bootloader != fastboot_bootloader:
        raise HardwareEvidenceError("ADB and Fastboot bootloader-state observations disagree.")

    hints = _partition_hints(fastboot.get("partition_hints_reported"))
    correlations = [
        "profile_id_matches_across_transports",
        "adb_model_matches_profile_allowlist",
        "adb_codename_matches_profile_codename",
        "fastboot_product_matches_profile_codename",
        "adb_build_fingerprint_recorded",
    ]
    if adb_slot and fastboot_slot:
        correlations.append("active_slot_matches_across_transports")
    if adb_bootloader not in {None, "unknown"} and fastboot_bootloader not in {None, "unknown"}:
        correlations.append("bootloader_state_matches_across_transports")
    if hints:
        correlations.append("fastboot_partition_hints_recorded")

    core: dict[str, object] = {
        "schema_version": 1,
        "source": "swirphoneos_cross_transport_read_only_hardware_evidence",
        "state": "CORRELATED_READ_ONLY_NOT_VERIFIED",
        "profile_id": profile.profile_id,
        "profile_status": profile.status,
        "adb_model_reported": model,
        "adb_codename_reported": codename,
        "adb_build_fingerprint_reported": fingerprint,
        "adb_slot_reported": adb_slot,
        "fastboot_product_reported": product,
        "fastboot_slot_reported": fastboot_slot,
        "partition_hints_reported": hints,
        "correlations": correlations,
        "hardware_verified": False,
        "swirphoneos_support": "NOT_VALIDATED",
        "write_allowed": False,
        "flash_allowed": False,
        "root_allowed": False,
        "warnings": [
            "Cross-transport correlation is not cryptographic proof that both reports came from the same physical phone.",
            "Fastboot partition values are device-reported hints, not a verified partition map or restore recipe.",
            "No installation, root, unlock, reboot, erase, flash, relock or restore operation is authorized by this evidence.",
        ],
    }
    canonical = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    result = dict(core)
    result["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    validate_hardware_evidence(result)
    return result


def validate_hardware_evidence(report: object) -> dict[str, object]:
    if not isinstance(report, dict) or set(report) != REPORT_KEYS:
        raise HardwareEvidenceError("Hardware evidence must match schema v1 exactly.")
    if report["schema_version"] != 1 or report["source"] != "swirphoneos_cross_transport_read_only_hardware_evidence":
        raise HardwareEvidenceError("Hardware evidence provenance is invalid.")
    if report["state"] != "CORRELATED_READ_ONLY_NOT_VERIFIED":
        raise HardwareEvidenceError("Hardware evidence state is invalid.")
    for key in ("hardware_verified", "write_allowed", "flash_allowed", "root_allowed"):
        if report[key] is not False:
            raise HardwareEvidenceError("Read-only evidence cannot authorize or verify device mutation.")
    if report["swirphoneos_support"] != "NOT_VALIDATED":
        raise HardwareEvidenceError("Read-only evidence cannot claim SwirPhoneOS support.")
    for key in ("profile_id", "profile_status", "adb_model_reported", "adb_codename_reported", "adb_build_fingerprint_reported", "fastboot_product_reported"):
        _text(report[key], key, limit=512)
    _text(report["adb_slot_reported"], "adb_slot_reported", optional=True, limit=16)
    _text(report["fastboot_slot_reported"], "fastboot_slot_reported", optional=True, limit=16)
    _partition_hints(report["partition_hints_reported"])
    correlations = report["correlations"]
    if not isinstance(correlations, list) or not 5 <= len(correlations) <= 16 or not all(isinstance(item, str) and item for item in correlations):
        raise HardwareEvidenceError("Correlation evidence is incomplete.")
    warnings = report["warnings"]
    if not isinstance(warnings, list) or len(warnings) != 3 or not all(isinstance(item, str) and item for item in warnings):
        raise HardwareEvidenceError("Hardware evidence warnings are invalid.")
    digest = _text(report["evidence_sha256"], "evidence_sha256", limit=64)
    if digest is None or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise HardwareEvidenceError("Hardware evidence SHA-256 is invalid.")
    core = {key: value for key, value in report.items() if key != "evidence_sha256"}
    expected = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    if digest != expected:
        raise HardwareEvidenceError("Hardware evidence integrity hash mismatch.")
    return report


def load_hardware_evidence(path: Path) -> dict[str, object]:
    return validate_hardware_evidence(load_json_report(path))


def assess_transaction_hardware(plan: TransactionPlan, hardware: dict[str, object]) -> dict[str, object]:
    """Bind a preparation-only plan to correlated observations without enabling writes."""
    validate_hardware_evidence(hardware)
    checks = {
        "profile_id_matches": plan.profile_id == hardware["profile_id"],
        "device_codename_matches": plan.device_codename.casefold() == str(hardware["adb_codename_reported"]).casefold(),
        "device_model_matches": plan.device_model.casefold() == str(hardware["adb_model_reported"]).casefold(),
        "current_build_fingerprint_matches": plan.expected_current_build == hardware["adb_build_fingerprint_reported"],
        "rollback_still_required": True,
        "owner_confirmation_still_required": True,
    }
    return {
        "schema_version": 1,
        "transaction_id": plan.transaction_id,
        "profile_id": plan.profile_id,
        "plan_sha256": plan.canonical_sha256,
        "hardware_evidence_sha256": hardware["evidence_sha256"],
        "state": "PREPARATION_MATCH_ONLY" if all(checks.values()) else "PREPARATION_MISMATCH",
        "checks": checks,
        "preconditions_match": all(checks.values()),
        "hardware_verified": False,
        "swirphoneos_support": "NOT_VALIDATED",
        "write_allowed": False,
        "flash_allowed": False,
        "root_allowed": False,
    }
