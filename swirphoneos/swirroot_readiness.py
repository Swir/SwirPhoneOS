"""Bind existing read-only safety evidence into a SwirRoot readiness report.

This module performs no device I/O and deliberately cannot authorize a root
transition. It answers a narrower engineering question: which mandatory
SwirRoot policy gates are already evidenced by the current recovery journal and
read-only hardware correlation, and which gates still require stronger proof?
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .hardware_evidence import load_hardware_evidence, validate_hardware_evidence
from .journal_evidence import load_journal, validate_journal
from .swirroot import SwirRootPolicy, load_policy


class SwirRootReadinessError(ValueError):
    """Raised when SwirRoot readiness inputs contradict each other or are unsafe."""


_ACTIONS = {"enable", "unroot"}
_REPORT_KEYS = {
    "schema_version",
    "source",
    "action",
    "policy_id",
    "exact_build",
    "profile_id",
    "transaction_id",
    "hardware_evidence_sha256",
    "journal_evidence_sha256",
    "evidence_bindings",
    "policy_gates",
    "missing_requirements",
    "policy_backend_available",
    "hardware_root_authorized",
    "transition_ready",
    "device_write_allowed",
    "root_operation_executed",
    "status_promotion_performed",
    "warnings",
    "evidence_sha256",
}
_WARNINGS = [
    "This report combines read-only/preparation evidence only and cannot verify physical SwirPhoneOS support.",
    "Owner confirmation, update-state safety and the expected non-root runtime state require independent durable evidence.",
    "No root, unroot, boot-image mutation, unlock, flash, erase, reboot or other device write is authorized or executed.",
]


def _text(value: object, field: str, *, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise SwirRootReadinessError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise SwirRootReadinessError(f"{field} is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise SwirRootReadinessError(f"{field} contains control characters.")
    return value


def _sha256(value: object, field: str) -> str:
    text = _text(value, field, limit=64)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise SwirRootReadinessError(f"{field} must be a lowercase SHA-256 digest.")
    return text


def _canonical_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def collect_swirroot_readiness(
    *,
    action: str,
    exact_build: str,
    policy: SwirRootPolicy,
    journal: dict[str, object],
    hardware: dict[str, object],
) -> dict[str, object]:
    """Create a tamper-evident, always-non-authorizing readiness projection."""
    if action not in _ACTIONS:
        raise SwirRootReadinessError("action must be either 'enable' or 'unroot'.")
    exact_build = _text(exact_build, "exact_build")
    try:
        journal = validate_journal(journal)
        hardware = validate_hardware_evidence(hardware)
    except ValueError as exc:
        raise SwirRootReadinessError("SwirRoot readiness input evidence failed validation.") from exc

    journal_profile = _text(journal.get("profile_id"), "journal profile_id", limit=129)
    hardware_profile = _text(hardware.get("profile_id"), "hardware profile_id", limit=129)
    if journal_profile != hardware_profile:
        raise SwirRootReadinessError("Recovery journal and hardware evidence refer to different profiles.")

    journal_model = _text(journal.get("device_model"), "journal device_model", limit=128)
    hardware_model = _text(hardware.get("adb_model_reported"), "hardware adb_model_reported", limit=128)
    if journal_model.casefold() != hardware_model.casefold():
        raise SwirRootReadinessError("Recovery journal and hardware evidence disagree on the device model.")

    journal_codename = _text(journal.get("device_codename"), "journal device_codename", limit=128)
    hardware_codename = _text(hardware.get("adb_codename_reported"), "hardware adb_codename_reported", limit=128)
    if journal_codename.casefold() != hardware_codename.casefold():
        raise SwirRootReadinessError("Recovery journal and hardware evidence disagree on the device codename.")

    observed_build = _text(hardware.get("adb_build_fingerprint_reported"), "hardware build fingerprint")
    expected_current_build = _text(journal.get("expected_current_build"), "journal expected_current_build")
    target_build = _text(journal.get("target_build"), "journal target_build")
    current_build_match = observed_build == expected_current_build
    target_build_match = target_build == exact_build
    if not current_build_match:
        raise SwirRootReadinessError("Read-only hardware fingerprint does not match the journal's expected current build.")
    if not target_build_match:
        raise SwirRootReadinessError("Requested exact SwirPhoneOS build does not match the journal target build.")

    hardware_evidence_sha = _sha256(hardware.get("evidence_sha256"), "hardware evidence sha256")
    journal_evidence_sha = _sha256(journal.get("evidence_sha256"), "journal evidence sha256")

    # Current hardware evidence is intentionally correlation-only, so it cannot
    # satisfy verified_device_profile or root authorization. Likewise, the
    # recovery journal deliberately records no owner confirmation and contains
    # no authoritative update-state or expected-nonroot-runtime proof.
    gates = {
        "exact_build_match": True,
        "verified_device_profile": hardware.get("hardware_verified") is True
        and hardware.get("swirphoneos_support") == "SUPPORTED",
        "owner_confirmation": journal.get("owner_confirmation_recorded") is True,
        "rollback_material_verified": journal.get("rollback_ready") is True,
        "journal_available": True,
        "update_state_safe": False,
        "expected_nonroot_state_known": False,
    }
    required = policy.enable_gates if action == "enable" else policy.unroot_gates
    missing = sorted(name for name in required if gates.get(name) is not True)
    backend_available = policy.root_available and exact_build in policy.supported_builds
    hardware_root_authorized = hardware.get("root_allowed") is True
    transition_ready = bool(not missing and backend_available and hardware_root_authorized)

    core: dict[str, object] = {
        "schema_version": 1,
        "source": "swirphoneos_swirroot_readiness_projection",
        "action": action,
        "policy_id": policy.policy_id,
        "exact_build": exact_build,
        "profile_id": journal_profile,
        "transaction_id": _text(journal.get("transaction_id"), "transaction_id", limit=128),
        "hardware_evidence_sha256": hardware_evidence_sha,
        "journal_evidence_sha256": journal_evidence_sha,
        "evidence_bindings": {
            "profile_matches": True,
            "device_model_matches": True,
            "device_codename_matches": True,
            "observed_current_build_matches_journal": True,
            "journal_target_matches_exact_build": True,
        },
        "policy_gates": gates,
        "missing_requirements": missing,
        "policy_backend_available": backend_available,
        "hardware_root_authorized": hardware_root_authorized,
        "transition_ready": transition_ready,
        "device_write_allowed": False,
        "root_operation_executed": False,
        "status_promotion_performed": False,
        "warnings": list(_WARNINGS),
    }
    result = dict(core)
    result["evidence_sha256"] = _canonical_sha256(core)
    validate_swirroot_readiness(result)
    return result


def validate_swirroot_readiness(report: object) -> dict[str, object]:
    if not isinstance(report, dict) or set(report) != _REPORT_KEYS:
        raise SwirRootReadinessError("SwirRoot readiness report must match schema v1 exactly.")
    if report["schema_version"] != 1 or report["source"] != "swirphoneos_swirroot_readiness_projection":
        raise SwirRootReadinessError("SwirRoot readiness provenance is invalid.")
    if report["action"] not in _ACTIONS:
        raise SwirRootReadinessError("SwirRoot readiness action is invalid.")
    for key in ("policy_id", "exact_build", "profile_id", "transaction_id"):
        _text(report[key], key, limit=512)
    for key in ("hardware_evidence_sha256", "journal_evidence_sha256", "evidence_sha256"):
        _sha256(report[key], key)

    bindings = report["evidence_bindings"]
    expected_bindings = {
        "profile_matches": True,
        "device_model_matches": True,
        "device_codename_matches": True,
        "observed_current_build_matches_journal": True,
        "journal_target_matches_exact_build": True,
    }
    if bindings != expected_bindings:
        raise SwirRootReadinessError("SwirRoot evidence bindings were modified or are incomplete.")

    gates = report["policy_gates"]
    gate_names = {
        "exact_build_match",
        "verified_device_profile",
        "owner_confirmation",
        "rollback_material_verified",
        "journal_available",
        "update_state_safe",
        "expected_nonroot_state_known",
    }
    if not isinstance(gates, dict) or set(gates) != gate_names or any(type(value) is not bool for value in gates.values()):
        raise SwirRootReadinessError("SwirRoot policy-gate projection is invalid.")
    if gates["exact_build_match"] is not True or gates["rollback_material_verified"] is not True or gates["journal_available"] is not True:
        raise SwirRootReadinessError("SwirRoot readiness lost mandatory preparation evidence.")

    missing = report["missing_requirements"]
    if not isinstance(missing, list) or len(missing) > len(gate_names) or not all(isinstance(item, str) and item in gate_names for item in missing) or len(set(missing)) != len(missing) or missing != sorted(missing):
        raise SwirRootReadinessError("SwirRoot missing-requirements list is invalid.")
    for key in ("policy_backend_available", "hardware_root_authorized", "transition_ready", "device_write_allowed", "root_operation_executed", "status_promotion_performed"):
        if type(report[key]) is not bool:
            raise SwirRootReadinessError(f"{key} must be boolean.")
    if report["device_write_allowed"] is not False or report["root_operation_executed"] is not False or report["status_promotion_performed"] is not False:
        raise SwirRootReadinessError("Readiness evidence must never claim mutation or status promotion.")
    if report["transition_ready"] and (missing or not report["policy_backend_available"] or not report["hardware_root_authorized"]):
        raise SwirRootReadinessError("transition_ready contradicts the required gates.")
    if report["warnings"] != _WARNINGS:
        raise SwirRootReadinessError("SwirRoot readiness warnings were modified.")

    digest = _sha256(report["evidence_sha256"], "evidence_sha256")
    core = {key: value for key, value in report.items() if key != "evidence_sha256"}
    if digest != _canonical_sha256(core):
        raise SwirRootReadinessError("SwirRoot readiness integrity hash mismatch.")
    return report


def collect_swirroot_readiness_from_files(
    *, action: str, exact_build: str, policy_path: Path, journal_path: Path, hardware_path: Path
) -> dict[str, object]:
    return collect_swirroot_readiness(
        action=action,
        exact_build=exact_build,
        policy=load_policy(policy_path),
        journal=load_journal(journal_path),
        hardware=load_hardware_evidence(hardware_path),
    )
