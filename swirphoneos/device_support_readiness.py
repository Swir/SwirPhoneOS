"""Fail-closed projection of what is still missing before a device may be supported.

The current schema intentionally consumes only metadata-only device profiles,
read-only ADB/Fastboot correlation, and a local pre-write recovery journal. It
therefore can never promote a phone to supported, authorize installation, or
perform any device I/O. Its purpose is to bind those preparatory inputs to an
exact profile/build pair and make the remaining physical validation gates
machine-readable instead of relying on prose or operator memory.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .hardware_evidence import load_hardware_evidence, validate_hardware_evidence
from .journal_evidence import load_journal, validate_journal
from .profiles import DeviceProfile, load_profile_snapshot


class DeviceSupportReadinessError(ValueError):
    """Raised when support-readiness evidence is malformed or contradictory."""


SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE = "swirphoneos_device_support_readiness_projection"
STATUS = "NOT_SUPPORTED"
READY_GATE_NAMES = {
    "metadata_profile_valid",
    "cross_transport_identity_correlated",
    "rollback_artifacts_preverified",
    "physical_hardware_verified",
    "verified_partition_map",
    "stock_restore_verified",
    "swirphoneos_boot_verified",
    "install_cycle_verified",
    "rollback_cycle_verified",
    "core_phone_experience_verified",
}
SUPPORT_GATE_NAMES = {
    "physical_hardware_verified",
    "verified_partition_map",
    "stock_restore_verified",
    "swirphoneos_boot_verified",
    "install_cycle_verified",
    "rollback_cycle_verified",
    "core_phone_experience_verified",
}
CAPABILITY_NAMES = (
    "telephony",
    "camera",
    "audio",
    "wifi",
    "bluetooth",
    "sensors",
    "gnss",
    "nfc",
)
REPORT_KEYS = {
    "schema_version",
    "source",
    "profile_id",
    "profile_status",
    "profile_sha256",
    "device_model",
    "device_codename",
    "observed_current_build",
    "target_build",
    "hardware_evidence_sha256",
    "journal_evidence_sha256",
    "evidence_bindings",
    "readiness_gates",
    "missing_requirements",
    "capability_status",
    "support_status",
    "support_claim_allowed",
    "profile_promotion_allowed",
    "install_allowed",
    "device_write_allowed",
    "root_allowed",
    "status_promotion_performed",
    "warnings",
    "evidence_sha256",
}
WARNINGS = [
    "This schema binds preparation-only evidence and cannot establish physical SwirPhoneOS device support.",
    "Read-only ADB/Fastboot correlation is not a verified partition map, stock-restore test, install test, rollback test or boot test.",
    "Telephony, camera, audio, Wi-Fi, Bluetooth, sensors, GNSS and NFC remain unverified until exact-device runtime evidence exists.",
    "No unlock, reboot, erase, flash, install, rollback, root, unroot or other device write is authorized or executed.",
]


def _text(value: object, field: str, *, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise DeviceSupportReadinessError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise DeviceSupportReadinessError(f"{field} is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise DeviceSupportReadinessError(f"{field} contains control characters.")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise DeviceSupportReadinessError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _canonical_sha256(value: dict[str, object]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def collect_device_support_readiness(
    *,
    profile: DeviceProfile,
    profile_sha256: str,
    journal: dict[str, object],
    hardware: dict[str, object],
) -> dict[str, object]:
    """Bind current preparation evidence while keeping device support denied."""
    profile_sha256 = _sha256(profile_sha256, "profile_sha256")
    try:
        journal = validate_journal(journal)
        hardware = validate_hardware_evidence(hardware)
    except ValueError as exc:
        raise DeviceSupportReadinessError("Device support readiness input evidence failed validation.") from exc

    if profile.status not in {"PLANNED_NOT_SUPPORTED", "PROFILED_NOT_VERIFIED"}:
        raise DeviceSupportReadinessError("Metadata-only profile status cannot be promoted by readiness projection.")

    journal_profile = _text(journal.get("profile_id"), "journal profile_id", limit=129)
    hardware_profile = _text(hardware.get("profile_id"), "hardware profile_id", limit=129)
    if profile.profile_id != journal_profile or profile.profile_id != hardware_profile:
        raise DeviceSupportReadinessError("Profile, recovery journal and hardware evidence refer to different device profiles.")

    journal_codename = _text(journal.get("device_codename"), "journal device codename", limit=128)
    hardware_codename = _text(hardware.get("adb_codename_reported"), "hardware device codename", limit=128)
    if profile.codename.casefold() != journal_codename.casefold() or profile.codename.casefold() != hardware_codename.casefold():
        raise DeviceSupportReadinessError("Profile, journal and hardware evidence disagree on device codename.")

    journal_model = _text(journal.get("device_model"), "journal device model", limit=128)
    hardware_model = _text(hardware.get("adb_model_reported"), "hardware device model", limit=128)
    if journal_model.casefold() != hardware_model.casefold():
        raise DeviceSupportReadinessError("Recovery journal and hardware evidence disagree on device model.")
    if not any(journal_model.casefold() == model.casefold() for model in profile.model_allowlist):
        raise DeviceSupportReadinessError("Observed device model is outside the profile allowlist.")

    observed_build = _text(hardware.get("adb_build_fingerprint_reported"), "observed current build")
    journal_current = _text(journal.get("expected_current_build"), "journal expected current build")
    if observed_build != journal_current:
        raise DeviceSupportReadinessError("Observed hardware build does not match the recovery journal current build.")
    target_build = _text(journal.get("target_build"), "target build")

    hardware_sha = _sha256(hardware.get("evidence_sha256"), "hardware evidence sha256")
    journal_sha = _sha256(journal.get("evidence_sha256"), "journal evidence sha256")

    # Schema v1 deliberately has no positive physical-support evidence type.
    # Only preparation facts proven by its three inputs may be true. When real
    # hardware/install/runtime evidence is introduced, it must use a new schema
    # rather than silently changing the semantics of this one.
    gates = {
        "metadata_profile_valid": True,
        "cross_transport_identity_correlated": True,
        "rollback_artifacts_preverified": journal.get("rollback_ready") is True,
        "physical_hardware_verified": False,
        "verified_partition_map": False,
        "stock_restore_verified": False,
        "swirphoneos_boot_verified": False,
        "install_cycle_verified": False,
        "rollback_cycle_verified": False,
        "core_phone_experience_verified": False,
    }
    missing = sorted(name for name in SUPPORT_GATE_NAMES if gates[name] is not True)
    capabilities = {name: "UNVERIFIED" for name in CAPABILITY_NAMES}

    core: dict[str, object] = {
        "schema_version": 1,
        "source": SOURCE,
        "profile_id": profile.profile_id,
        "profile_status": profile.status,
        "profile_sha256": profile_sha256,
        "device_model": journal_model,
        "device_codename": profile.codename,
        "observed_current_build": observed_build,
        "target_build": target_build,
        "hardware_evidence_sha256": hardware_sha,
        "journal_evidence_sha256": journal_sha,
        "evidence_bindings": {
            "profile_matches_hardware": True,
            "profile_matches_journal": True,
            "codename_matches": True,
            "model_matches_allowlist": True,
            "hardware_matches_journal_current_build": True,
            "target_build_recorded": True,
        },
        "readiness_gates": gates,
        "missing_requirements": missing,
        "capability_status": capabilities,
        "support_status": STATUS,
        "support_claim_allowed": False,
        "profile_promotion_allowed": False,
        "install_allowed": False,
        "device_write_allowed": False,
        "root_allowed": False,
        "status_promotion_performed": False,
        "warnings": list(WARNINGS),
    }
    result = dict(core)
    result["evidence_sha256"] = _canonical_sha256(core)
    validate_device_support_readiness(result)
    return result


def validate_device_support_readiness(report: object) -> dict[str, object]:
    if not isinstance(report, dict) or set(report) != REPORT_KEYS:
        raise DeviceSupportReadinessError("Device support readiness report must match schema v1 exactly.")
    if report["schema_version"] != 1 or report["source"] != SOURCE:
        raise DeviceSupportReadinessError("Device support readiness provenance is invalid.")

    for key in (
        "profile_id", "profile_status", "device_model", "device_codename",
        "observed_current_build", "target_build",
    ):
        _text(report[key], key, limit=512)
    for key in ("profile_sha256", "hardware_evidence_sha256", "journal_evidence_sha256", "evidence_sha256"):
        _sha256(report[key], key)
    if report["profile_status"] not in {"PLANNED_NOT_SUPPORTED", "PROFILED_NOT_VERIFIED"}:
        raise DeviceSupportReadinessError("Readiness schema v1 cannot carry a verified profile status.")

    bindings = report["evidence_bindings"]
    expected_bindings = {
        "profile_matches_hardware": True,
        "profile_matches_journal": True,
        "codename_matches": True,
        "model_matches_allowlist": True,
        "hardware_matches_journal_current_build": True,
        "target_build_recorded": True,
    }
    if bindings != expected_bindings:
        raise DeviceSupportReadinessError("Device support evidence bindings were modified or are incomplete.")

    gates = report["readiness_gates"]
    expected_gates = {
        "metadata_profile_valid": True,
        "cross_transport_identity_correlated": True,
        "rollback_artifacts_preverified": True,
        "physical_hardware_verified": False,
        "verified_partition_map": False,
        "stock_restore_verified": False,
        "swirphoneos_boot_verified": False,
        "install_cycle_verified": False,
        "rollback_cycle_verified": False,
        "core_phone_experience_verified": False,
    }
    if not isinstance(gates, dict) or set(gates) != READY_GATE_NAMES or gates != expected_gates:
        raise DeviceSupportReadinessError("Schema-v1 readiness gates were modified or claim unavailable physical evidence.")

    missing = report["missing_requirements"]
    expected_missing = sorted(name for name in SUPPORT_GATE_NAMES if gates[name] is not True)
    if missing != expected_missing:
        raise DeviceSupportReadinessError("Missing support requirements do not match the readiness gates.")

    capabilities = report["capability_status"]
    expected_capabilities = {name: "UNVERIFIED" for name in CAPABILITY_NAMES}
    if capabilities != expected_capabilities:
        raise DeviceSupportReadinessError("Schema-v1 capability status cannot claim exact-device runtime verification.")

    if report["support_status"] != STATUS:
        raise DeviceSupportReadinessError("Preparation-only evidence cannot claim device support.")
    for key in (
        "support_claim_allowed", "profile_promotion_allowed", "install_allowed",
        "device_write_allowed", "root_allowed", "status_promotion_performed",
    ):
        if report[key] is not False:
            raise DeviceSupportReadinessError("Preparation-only readiness evidence cannot authorize support or mutation.")
    if report["warnings"] != WARNINGS:
        raise DeviceSupportReadinessError("Device support readiness warnings were modified.")

    digest = _sha256(report["evidence_sha256"], "evidence_sha256")
    core = {key: value for key, value in report.items() if key != "evidence_sha256"}
    if digest != _canonical_sha256(core):
        raise DeviceSupportReadinessError("Device support readiness integrity hash mismatch.")
    return report


def collect_device_support_readiness_from_files(
    *, profile_path: Path, journal_path: Path, hardware_path: Path
) -> dict[str, object]:
    """Load exact local evidence files and create a non-authorizing report."""
    profile, profile_sha256 = load_profile_snapshot(profile_path)
    return collect_device_support_readiness(
        profile=profile,
        profile_sha256=profile_sha256,
        journal=load_journal(journal_path),
        hardware=load_hardware_evidence(hardware_path),
    )
