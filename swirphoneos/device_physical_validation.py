"""Fail-closed exact-device physical validation evidence binding.

This module is intentionally host-only. It validates local evidence that an
owner/operator has already collected and packages the result for human support
review. It never runs adb/fastboot, never authorizes a device write, never
promotes a device profile and never claims hardware support automatically.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .device_support_readiness import (
    CAPABILITY_NAMES,
    DeviceSupportReadinessError,
    SUPPORT_GATE_NAMES,
    validate_device_support_readiness,
)


class DevicePhysicalValidationError(ValueError):
    """Raised when physical validation evidence is malformed, mixed or unsafe."""


SCHEMA_VERSION = 2
SOURCE = "swirphoneos_physical_device_validation_bundle"
RECORD_SOURCE = "owner_physical_validation_record"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
TEST_OUTCOMES = {"PASS", "FAIL"}
CAPABILITY_STATES = {"PASS", "FAIL", "NOT_APPLICABLE", "NOT_TESTED"}
EVIDENCE_KINDS = {"AUTOMATED_CAPTURE", "MANUAL_OBSERVATION", "HYBRID"}
PHYSICAL_TEST_IDS = tuple(sorted(SUPPORT_GATE_NAMES))
CORE_PASS_CAPABILITIES = {"audio", "wifi", "sensors"}

RECORD_KEYS = {
    "schema_version",
    "source",
    "validation_session_id",
    "profile_id",
    "device_model",
    "device_codename",
    "observed_current_build",
    "target_build",
    "readiness_evidence_sha256",
    "owner_present",
    "external_operator_write_activity_recorded",
    "tool_write_authorized",
    "tests",
    "capabilities",
    "notes",
}
ENTRY_KEYS = {
    "name",
    "state",
    "evidence_path",
    "evidence_sha256",
    "evidence_size",
    "evidence_kind",
    "observed_utc",
    "notes",
}
REPORT_KEYS = {
    "schema_version",
    "source",
    "validation_session_id",
    "profile_id",
    "device_model",
    "device_codename",
    "observed_current_build",
    "target_build",
    "profile_sha256",
    "readiness_file_sha256",
    "readiness_evidence_sha256",
    "hardware_evidence_sha256",
    "journal_evidence_sha256",
    "owner_present",
    "external_operator_write_activity_recorded",
    "tool_write_authorized",
    "physical_test_bindings",
    "capability_bindings",
    "evidence_inventory_verified",
    "support_candidate_review_ready",
    "known_capability_failures",
    "missing_requirements",
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
    "A complete physical-validation bundle is evidence for human support review, not an automatic support claim.",
    "This host-only module performs no ADB/Fastboot/device command and cannot authorize installation, flashing, root or profile promotion.",
    "Known capability failures remain visible; beta/release policy must separately decide whether a tested limitation is acceptable.",
    "Profile promotion requires a separate reviewed policy/schema change after exact-device evidence has been audited.",
]


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DevicePhysicalValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path, *, maximum_bytes: int = MAX_JSON_BYTES) -> tuple[dict[str, object], str]:
    if path.is_symlink() or not path.is_file():
        raise DevicePhysicalValidationError("Expected an existing regular JSON file, not a symlink.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DevicePhysicalValidationError("JSON evidence could not be read.") from exc
    if not raw or len(raw) > maximum_bytes:
        raise DevicePhysicalValidationError("JSON evidence has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DevicePhysicalValidationError("JSON evidence must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise DevicePhysicalValidationError("JSON evidence root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _text(value: object, field: str, *, limit: int = 512, ascii_only: bool = True) -> str:
    if not isinstance(value, str):
        raise DevicePhysicalValidationError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit:
        raise DevicePhysicalValidationError(f"{field} is invalid.")
    if ascii_only and not value.isascii():
        raise DevicePhysicalValidationError(f"{field} must be ASCII.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise DevicePhysicalValidationError(f"{field} contains control characters.")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise DevicePhysicalValidationError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _timestamp(value: object, field: str) -> str:
    text = _text(value, field, limit=32)
    if not text.endswith("Z"):
        raise DevicePhysicalValidationError(f"{field} must use UTC Z format.")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise DevicePhysicalValidationError(f"{field} is not a valid UTC timestamp.") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise DevicePhysicalValidationError(f"{field} must use UTC.")
    return text


def _relative_path(value: object, field: str) -> str:
    text = _text(value, field, limit=240)
    if text.startswith("/") or "\\" in text:
        raise DevicePhysicalValidationError(f"{field} must be a portable relative POSIX path.")
    path = PurePosixPath(text)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise DevicePhysicalValidationError(f"{field} contains an unsafe path component.")
    return path.as_posix()


def _canonical_sha256(value: dict[str, object]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _entry(value: object, *, allowed_names: set[str], allowed_states: set[str], capability: bool) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != ENTRY_KEYS:
        raise DevicePhysicalValidationError("Physical validation entry does not match schema v2 exactly.")
    name = _text(value["name"], "entry name", limit=128)
    if name not in allowed_names:
        raise DevicePhysicalValidationError("Physical validation entry name is unknown.")
    state = _text(value["state"], "entry state", limit=32)
    if state not in allowed_states:
        raise DevicePhysicalValidationError("Physical validation entry state is invalid.")

    without_evidence = capability and state == "NOT_TESTED"
    if without_evidence:
        if any(value[key] is not None for key in ("evidence_path", "evidence_sha256", "evidence_size", "evidence_kind")):
            raise DevicePhysicalValidationError("NOT_TESTED capability entries cannot carry evidence.")
        evidence_path = None
        evidence_sha256 = None
        evidence_size = None
        evidence_kind = None
    else:
        evidence_path = _relative_path(value["evidence_path"], "evidence_path")
        evidence_sha256 = _sha256(value["evidence_sha256"], "evidence_sha256")
        evidence_size = value["evidence_size"]
        if type(evidence_size) is not int or evidence_size <= 0 or evidence_size > MAX_EVIDENCE_BYTES:
            raise DevicePhysicalValidationError("evidence_size must be a positive bounded integer.")
        evidence_kind = _text(value["evidence_kind"], "evidence_kind", limit=32)
        if evidence_kind not in EVIDENCE_KINDS:
            raise DevicePhysicalValidationError("evidence_kind is invalid.")

    return {
        "name": name,
        "state": state,
        "evidence_path": evidence_path,
        "evidence_sha256": evidence_sha256,
        "evidence_size": evidence_size,
        "evidence_kind": evidence_kind,
        "observed_utc": _timestamp(value["observed_utc"], "observed_utc"),
        "notes": _text(value["notes"], "notes", limit=2048, ascii_only=False),
    }


def validate_physical_validation_record(record: object) -> dict[str, object]:
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise DevicePhysicalValidationError("Physical validation record must match schema v2 exactly.")
    if record["schema_version"] != SCHEMA_VERSION or record["source"] != RECORD_SOURCE:
        raise DevicePhysicalValidationError("Physical validation record provenance is invalid.")

    session_id = _text(record["validation_session_id"], "validation_session_id", limit=128)
    if not SAFE_TOKEN.fullmatch(session_id):
        raise DevicePhysicalValidationError("validation_session_id must be a safe token.")
    profile_id = _text(record["profile_id"], "profile_id", limit=129)
    model = _text(record["device_model"], "device_model", limit=128)
    codename = _text(record["device_codename"], "device_codename", limit=128)
    current_build = _text(record["observed_current_build"], "observed_current_build")
    target_build = _text(record["target_build"], "target_build")
    readiness_sha = _sha256(record["readiness_evidence_sha256"], "readiness_evidence_sha256")
    if type(record["owner_present"]) is not bool or type(record["external_operator_write_activity_recorded"]) is not bool:
        raise DevicePhysicalValidationError("Owner/operator record flags must be booleans.")
    if record["tool_write_authorized"] is not False:
        raise DevicePhysicalValidationError("Physical validation tooling never authorizes device writes.")

    raw_tests = record["tests"]
    if not isinstance(raw_tests, list) or len(raw_tests) != len(PHYSICAL_TEST_IDS):
        raise DevicePhysicalValidationError("Physical validation must contain every required physical test exactly once.")
    tests = [_entry(item, allowed_names=set(PHYSICAL_TEST_IDS), allowed_states=TEST_OUTCOMES, capability=False) for item in raw_tests]
    if {str(item["name"]) for item in tests} != set(PHYSICAL_TEST_IDS) or len({str(item["name"]) for item in tests}) != len(tests):
        raise DevicePhysicalValidationError("Physical validation test inventory is incomplete or duplicated.")

    raw_capabilities = record["capabilities"]
    if not isinstance(raw_capabilities, list) or len(raw_capabilities) != len(CAPABILITY_NAMES):
        raise DevicePhysicalValidationError("Capability review must contain every tracked capability exactly once.")
    capabilities = [_entry(item, allowed_names=set(CAPABILITY_NAMES), allowed_states=CAPABILITY_STATES, capability=True) for item in raw_capabilities]
    if {str(item["name"]) for item in capabilities} != set(CAPABILITY_NAMES) or len({str(item["name"]) for item in capabilities}) != len(capabilities):
        raise DevicePhysicalValidationError("Capability inventory is incomplete or duplicated.")

    paths = [str(item["evidence_path"]) for item in (*tests, *capabilities) if item["evidence_path"] is not None]
    if len(paths) != len(set(paths)):
        raise DevicePhysicalValidationError("Each test/capability must bind a distinct evidence file.")

    return {
        "schema_version": SCHEMA_VERSION,
        "source": RECORD_SOURCE,
        "validation_session_id": session_id,
        "profile_id": profile_id,
        "device_model": model,
        "device_codename": codename,
        "observed_current_build": current_build,
        "target_build": target_build,
        "readiness_evidence_sha256": readiness_sha,
        "owner_present": record["owner_present"],
        "external_operator_write_activity_recorded": record["external_operator_write_activity_recorded"],
        "tool_write_authorized": False,
        "tests": tests,
        "capabilities": capabilities,
        "notes": _text(record["notes"], "record notes", limit=4096, ascii_only=False),
    }


def _candidate(root: Path, relative: str) -> Path:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise DevicePhysicalValidationError("Evidence path contains a symlink.")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = current.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise DevicePhysicalValidationError("Evidence file escapes the trusted root or does not exist.") from exc
    if not resolved.is_file():
        raise DevicePhysicalValidationError("Evidence path must resolve to a regular file.")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except OSError as exc:
        raise DevicePhysicalValidationError("Evidence file could not be read.") from exc
    return digest.hexdigest()


def _verified_binding(root: Path, entry: dict[str, object]) -> dict[str, object]:
    relative = entry["evidence_path"]
    binding = dict(entry)
    if relative is None:
        binding["evidence_verified"] = False
        return binding
    path = _candidate(root, str(relative))
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise DevicePhysicalValidationError("Evidence file metadata could not be read.") from exc
    if size != entry["evidence_size"]:
        raise DevicePhysicalValidationError("Physical validation evidence size mismatch.")
    digest = _sha256_file(path)
    if digest != entry["evidence_sha256"]:
        raise DevicePhysicalValidationError("Physical validation evidence SHA-256 mismatch.")
    binding["evidence_verified"] = True
    return binding


def _binding_map(entries: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(entry["name"]): {key: value for key, value in entry.items() if key != "name"} for entry in entries}


def _derive_missing(
    tests: dict[str, dict[str, object]],
    capabilities: dict[str, dict[str, object]],
    *,
    owner_present: bool,
    external_write_recorded: bool,
) -> list[str]:
    missing = [name for name, binding in tests.items() if binding["state"] != "PASS"]
    missing.extend(f"capability_review:{name}" for name, binding in capabilities.items() if binding["state"] == "NOT_TESTED")
    missing.extend(f"core_capability:{name}" for name in CORE_PASS_CAPABILITIES if capabilities[name]["state"] != "PASS")
    if not owner_present:
        missing.append("owner_present")
    if not external_write_recorded:
        missing.append("external_operator_write_activity_recorded")
    return sorted(set(missing))


def _derive_report(
    *,
    readiness: dict[str, object],
    readiness_file_sha256: str,
    record: dict[str, object],
    test_bindings: dict[str, dict[str, object]],
    capability_bindings: dict[str, dict[str, object]],
) -> dict[str, object]:
    if record["profile_id"] != readiness["profile_id"]:
        raise DevicePhysicalValidationError("Physical record and readiness report use different device profiles.")
    for key in ("device_model", "device_codename", "observed_current_build", "target_build"):
        if record[key] != readiness[key]:
            raise DevicePhysicalValidationError(f"Physical record does not match readiness {key}.")
    if record["readiness_evidence_sha256"] != readiness["evidence_sha256"]:
        raise DevicePhysicalValidationError("Physical record is bound to a different readiness report.")

    missing = _derive_missing(
        test_bindings,
        capability_bindings,
        owner_present=record["owner_present"] is True,
        external_write_recorded=record["external_operator_write_activity_recorded"] is True,
    )
    failures = sorted(name for name, binding in capability_bindings.items() if binding["state"] == "FAIL")
    evidence_inventory_verified = all(binding["evidence_verified"] is True for binding in test_bindings.values()) and all(
        binding["evidence_verified"] is True or binding["state"] == "NOT_TESTED"
        for binding in capability_bindings.values()
    )

    core: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "validation_session_id": record["validation_session_id"],
        "profile_id": readiness["profile_id"],
        "device_model": readiness["device_model"],
        "device_codename": readiness["device_codename"],
        "observed_current_build": readiness["observed_current_build"],
        "target_build": readiness["target_build"],
        "profile_sha256": readiness["profile_sha256"],
        "readiness_file_sha256": readiness_file_sha256,
        "readiness_evidence_sha256": readiness["evidence_sha256"],
        "hardware_evidence_sha256": readiness["hardware_evidence_sha256"],
        "journal_evidence_sha256": readiness["journal_evidence_sha256"],
        "owner_present": record["owner_present"],
        "external_operator_write_activity_recorded": record["external_operator_write_activity_recorded"],
        "tool_write_authorized": False,
        "physical_test_bindings": test_bindings,
        "capability_bindings": capability_bindings,
        "evidence_inventory_verified": evidence_inventory_verified,
        "support_candidate_review_ready": evidence_inventory_verified and not missing,
        "known_capability_failures": failures,
        "missing_requirements": missing,
        "support_status": "NOT_SUPPORTED",
        "support_claim_allowed": False,
        "profile_promotion_allowed": False,
        "install_allowed": False,
        "device_write_allowed": False,
        "root_allowed": False,
        "status_promotion_performed": False,
        "warnings": list(WARNINGS),
    }
    report = dict(core)
    report["evidence_sha256"] = _canonical_sha256(core)
    return validate_physical_validation_report(report)


def _validate_binding_map(value: object, *, names: set[str], states: set[str], capability: bool) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict) or set(value) != names:
        raise DevicePhysicalValidationError("Physical validation binding inventory is incomplete or unknown.")
    normalized: dict[str, dict[str, object]] = {}
    seen_paths: set[str] = set()
    expected_keys = ENTRY_KEYS - {"name"} | {"evidence_verified"}
    for name in sorted(names):
        binding = value[name]
        if not isinstance(binding, dict) or set(binding) != expected_keys:
            raise DevicePhysicalValidationError("Physical validation binding does not match schema v2 exactly.")
        state = _text(binding["state"], "binding state", limit=32)
        if state not in states:
            raise DevicePhysicalValidationError("Physical validation binding state is invalid.")
        no_evidence = capability and state == "NOT_TESTED"
        if no_evidence:
            if any(binding[key] is not None for key in ("evidence_path", "evidence_sha256", "evidence_size", "evidence_kind")):
                raise DevicePhysicalValidationError("NOT_TESTED binding cannot carry evidence metadata.")
            if binding["evidence_verified"] is not False:
                raise DevicePhysicalValidationError("NOT_TESTED binding cannot claim verified evidence.")
        else:
            path = _relative_path(binding["evidence_path"], "binding evidence path")
            if path in seen_paths:
                raise DevicePhysicalValidationError("Physical validation evidence paths must remain unique.")
            seen_paths.add(path)
            _sha256(binding["evidence_sha256"], "binding evidence sha256")
            size = binding["evidence_size"]
            if type(size) is not int or size <= 0 or size > MAX_EVIDENCE_BYTES:
                raise DevicePhysicalValidationError("Binding evidence size is invalid.")
            if binding["evidence_kind"] not in EVIDENCE_KINDS or binding["evidence_verified"] is not True:
                raise DevicePhysicalValidationError("Bound evidence must remain verified and use a known evidence kind.")
        _timestamp(binding["observed_utc"], "binding observed_utc")
        _text(binding["notes"], "binding notes", limit=2048, ascii_only=False)
        normalized[name] = binding
    return normalized


def validate_physical_validation_report(report: object) -> dict[str, object]:
    if not isinstance(report, dict) or set(report) != REPORT_KEYS:
        raise DevicePhysicalValidationError("Physical validation report must match schema v2 exactly.")
    if report["schema_version"] != SCHEMA_VERSION or report["source"] != SOURCE:
        raise DevicePhysicalValidationError("Physical validation report provenance is invalid.")
    for key in (
        "validation_session_id", "profile_id", "device_model", "device_codename",
        "observed_current_build", "target_build", "support_status",
    ):
        _text(report[key], key, limit=512)
    for key in (
        "profile_sha256", "readiness_file_sha256", "readiness_evidence_sha256",
        "hardware_evidence_sha256", "journal_evidence_sha256", "evidence_sha256",
    ):
        _sha256(report[key], key)
    if type(report["owner_present"]) is not bool or type(report["external_operator_write_activity_recorded"]) is not bool:
        raise DevicePhysicalValidationError("Physical validation report owner flags are malformed.")
    if report["tool_write_authorized"] is not False:
        raise DevicePhysicalValidationError("Physical validation tooling cannot authorize writes.")

    tests = _validate_binding_map(report["physical_test_bindings"], names=set(PHYSICAL_TEST_IDS), states=TEST_OUTCOMES, capability=False)
    capabilities = _validate_binding_map(report["capability_bindings"], names=set(CAPABILITY_NAMES), states=CAPABILITY_STATES, capability=True)
    all_paths = [
        str(binding["evidence_path"])
        for binding in (*tests.values(), *capabilities.values())
        if binding["evidence_path"] is not None
    ]
    if len(all_paths) != len(set(all_paths)):
        raise DevicePhysicalValidationError("Evidence files cannot be reused across tests/capabilities.")

    expected_inventory_verified = all(binding["evidence_verified"] is True for binding in tests.values()) and all(
        binding["evidence_verified"] is True or binding["state"] == "NOT_TESTED"
        for binding in capabilities.values()
    )
    if report["evidence_inventory_verified"] is not expected_inventory_verified:
        raise DevicePhysicalValidationError("Evidence-inventory verification projection was modified.")
    expected_missing = _derive_missing(
        tests,
        capabilities,
        owner_present=report["owner_present"] is True,
        external_write_recorded=report["external_operator_write_activity_recorded"] is True,
    )
    if report["missing_requirements"] != expected_missing:
        raise DevicePhysicalValidationError("Missing-requirements projection was modified.")
    expected_candidate = expected_inventory_verified and not expected_missing
    if report["support_candidate_review_ready"] is not expected_candidate:
        raise DevicePhysicalValidationError("Support-candidate review projection is inconsistent with evidence.")
    failures = sorted(name for name, binding in capabilities.items() if binding["state"] == "FAIL")
    if report["known_capability_failures"] != failures:
        raise DevicePhysicalValidationError("Known capability failure projection was modified.")
    if report["support_status"] != "NOT_SUPPORTED":
        raise DevicePhysicalValidationError("Physical validation schema v2 cannot claim supported status.")
    for key in (
        "support_claim_allowed", "profile_promotion_allowed", "install_allowed",
        "device_write_allowed", "root_allowed", "status_promotion_performed",
    ):
        if report[key] is not False:
            raise DevicePhysicalValidationError(f"{key} must remain false in physical validation schema v2.")
    if report["warnings"] != WARNINGS:
        raise DevicePhysicalValidationError("Physical validation warnings were modified.")

    core = {key: value for key, value in report.items() if key != "evidence_sha256"}
    if _canonical_sha256(core) != report["evidence_sha256"]:
        raise DevicePhysicalValidationError("Physical validation evidence SHA-256 does not match the canonical payload.")
    return report


def collect_physical_validation_from_files(
    *,
    readiness_path: Path,
    record_path: Path,
    evidence_root: Path,
) -> dict[str, object]:
    """Bind exact readiness to exact local physical evidence without device access."""
    readiness_raw, readiness_file_sha = _load_json(readiness_path)
    try:
        readiness = validate_device_support_readiness(readiness_raw)
    except (DeviceSupportReadinessError, ValueError) as exc:
        raise DevicePhysicalValidationError("Readiness evidence failed validation.") from exc
    record_raw, _ = _load_json(record_path)
    record = validate_physical_validation_record(record_raw)
    if not evidence_root.is_absolute() or evidence_root.is_symlink() or not evidence_root.is_dir():
        raise DevicePhysicalValidationError("Evidence root must be an existing absolute non-symlink directory.")

    tests = [_verified_binding(evidence_root, item) for item in record["tests"]]
    capabilities = [_verified_binding(evidence_root, item) for item in record["capabilities"]]
    return _derive_report(
        readiness=readiness,
        readiness_file_sha256=readiness_file_sha,
        record=record,
        test_bindings=_binding_map(tests),
        capability_bindings=_binding_map(capabilities),
    )
