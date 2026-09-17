"""Fail-closed binding of exact-device physical validation evidence.

This module is intentionally host-only. It validates files already collected by
an owner/operator and turns them into a tamper-evident review bundle. It never
runs adb/fastboot, never authorizes a write, never promotes a device profile and
never claims support automatically.
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


SCHEMA_VERSION = 1
SOURCE = "swirphoneos_physical_device_validation_bundle"
RECORD_SOURCE = "owner_physical_validation_record"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
TEST_OUTCOMES = {"PASS", "FAIL"}
EVIDENCE_KINDS = {"AUTOMATED_CAPTURE", "MANUAL_OBSERVATION", "HYBRID"}
CAPABILITY_STATES = {"PASS", "FAIL", "NOT_APPLICABLE", "NOT_TESTED"}

# These seven gates are exactly the physical gates that schema-v1 readiness
# intentionally cannot satisfy. A physical-validation record must cover each
# one exactly once; preparation-only gates are inherited from readiness.
PHYSICAL_TEST_IDS = tuple(sorted(SUPPORT_GATE_NAMES))

# For a support-candidate review, core phone basics must actually work. Camera
# and telephony may still be known issues for an early device port, but they
# must at least have been tested and truthfully recorded before review.
CORE_PASS_CAPABILITIES = {"audio", "wifi", "sensors"}
MUST_BE_REVIEWED_CAPABILITIES = set(CAPABILITY_NAMES)

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
TEST_KEYS = {
    "id",
    "outcome",
    "evidence_path",
    "evidence_sha256",
    "evidence_size",
    "evidence_kind",
    "observed_utc",
    "notes",
}
CAPABILITY_KEYS = {
    "name",
    "status",
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
    "physical_test_results",
    "capability_status",
    "verified_evidence_files",
    "physical_validation_evidence_complete",
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
    "A support-candidate review may contain truthfully recorded capability failures; beta/release policy must evaluate known issues separately.",
    "Profile promotion requires a separate reviewed schema/change after exact-device evidence has been audited.",
]


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DevicePhysicalValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path, *, maximum_bytes: int = MAX_JSON_BYTES) -> tuple[dict[str, object], str]:
    if not path.is_file() or path.is_symlink():
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


def _text(value: object, field: str, *, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise DevicePhysicalValidationError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise DevicePhysicalValidationError(f"{field} is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise DevicePhysicalValidationError(f"{field} contains control characters.")
    return value


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise DevicePhysicalValidationError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _timestamp(value: object, field: str) -> str:
    text = _text(value, field, limit=32)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DevicePhysicalValidationError(f"{field} is not a valid UTC timestamp.") from exc
    if not text.endswith("Z") or parsed.tzinfo is None:
        raise DevicePhysicalValidationError(f"{field} must use UTC Z format.")
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
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _record_entry(value: object, *, capability: bool) -> dict[str, object]:
    keys = CAPABILITY_KEYS if capability else TEST_KEYS
    if not isinstance(value, dict) or set(value) != keys:
        raise DevicePhysicalValidationError("Physical validation record entry does not match schema v1 exactly.")
    identity_field = "name" if capability else "id"
    identity = _text(value[identity_field], identity_field, limit=128)
    if not SAFE_TOKEN.fullmatch(identity):
        raise DevicePhysicalValidationError(f"{identity_field} must be a safe token.")
    state_field = "status" if capability else "outcome"
    state = _text(value[state_field], state_field, limit=32)
    allowed_states = CAPABILITY_STATES if capability else TEST_OUTCOMES
    if state not in allowed_states:
        raise DevicePhysicalValidationError(f"{state_field} is not an allowed value.")

    path_value = value["evidence_path"]
    sha_value = value["evidence_sha256"]
    size_value = value["evidence_size"]
    kind_value = value["evidence_kind"]
    if capability and state == "NOT_TESTED":
        if path_value is not None or sha_value is not None or size_value is not None or kind_value is not None:
            raise DevicePhysicalValidationError("NOT_TESTED capability entries cannot pretend to carry evidence.")
        path = None
        digest = None
        size = None
        kind = None
    else:
        path = _relative_path(path_value, "evidence_path")
        digest = _sha256(sha_value, "evidence_sha256")
        if type(size_value) is not int or size_value <= 0 or size_value > MAX_EVIDENCE_BYTES:
            raise DevicePhysicalValidationError("evidence_size must be a positive bounded integer.")
        size = size_value
        kind = _text(kind_value, "evidence_kind", limit=32)
        if kind not in EVIDENCE_KINDS:
            raise DevicePhysicalValidationError("evidence_kind is not allowed.")
    observed = _timestamp(value["observed_utc"], "observed_utc")
    notes = _text(value["notes"], "notes", limit=2048)
    return {
        identity_field: identity,
        state_field: state,
        "evidence_path": path,
        "evidence_sha256": digest,
        "evidence_size": size,
        "evidence_kind": kind,
        "observed_utc": observed,
        "notes": notes,
    }


def validate_physical_validation_record(record: object) -> dict[str, object]:
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise DevicePhysicalValidationError("Physical validation record must match schema v1 exactly.")
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

    tests_raw = record["tests"]
    if not isinstance(tests_raw, list) or len(tests_raw) != len(PHYSICAL_TEST_IDS):
        raise DevicePhysicalValidationError("Physical validation must contain every required physical test exactly once.")
    tests = [_record_entry(item, capability=False) for item in tests_raw]
    test_ids = [str(item["id"]) for item in tests]
    if len(set(test_ids)) != len(test_ids) or set(test_ids) != set(PHYSICAL_TEST_IDS):
        raise DevicePhysicalValidationError("Physical validation test inventory is incomplete, duplicated or unknown.")

    capabilities_raw = record["capabilities"]
    if not isinstance(capabilities_raw, list) or len(capabilities_raw) != len(CAPABILITY_NAMES):
        raise DevicePhysicalValidationError("Capability review must contain every tracked capability exactly once.")
    capabilities = [_record_entry(item, capability=True) for item in capabilities_raw]
    capability_names = [str(item["name"]) for item in capabilities]
    if len(set(capability_names)) != len(capability_names) or set(capability_names) != set(CAPABILITY_NAMES):
        raise DevicePhysicalValidationError("Capability inventory is incomplete, duplicated or unknown.")

    evidence_paths = [
        str(item["evidence_path"])
        for item in (*tests, *capabilities)
        if item["evidence_path"] is not None
    ]
    if len(evidence_paths) != len(set(evidence_paths)):
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
        "notes": _text(record["notes"], "record notes", limit=4096),
    }


def _candidate(root: Path, relative: str) -> Path:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise DevicePhysicalValidationError("Evidence path contains a symlink.")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise DevicePhysicalValidationError("Evidence file escapes the trusted root or does not exist.") from exc
    if not resolved.is_file():
        raise DevicePhysicalValidationError("Evidence path must resolve to a regular file.")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    except OSError as exc:
        raise DevicePhysicalValidationError("Evidence file could not be read.") from exc
    return digest.hexdigest()


def _verify_evidence(root: Path, entry: dict[str, object]) -> dict[str, object] | None:
    relative = entry["evidence_path"]
    if relative is None:
        return None
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
    return {
        "path": relative,
        "size": size,
        "sha256": digest,
        "kind": entry["evidence_kind"],
        "verified": True,
    }


def _derive_report(
    *,
    readiness: dict[str, object],
    readiness_file_sha256: str,
    record: dict[str, object],
    verified_files: list[dict[str, object]],
) -> dict[str, object]:
    if record["profile_id"] != readiness["profile_id"]:
        raise DevicePhysicalValidationError("Physical record and readiness report use different device profiles.")
    for record_key, readiness_key in (
        ("device_model", "device_model"),
        ("device_codename", "device_codename"),
        ("observed_current_build", "observed_current_build"),
        ("target_build", "target_build"),
    ):
        if record[record_key] != readiness[readiness_key]:
            raise DevicePhysicalValidationError(f"Physical record does not match readiness {readiness_key}.")
    if record["readiness_evidence_sha256"] != readiness["evidence_sha256"]:
        raise DevicePhysicalValidationError("Physical record is bound to a different readiness report.")

    test_results = {str(item["id"]): str(item["outcome"]) for item in record["tests"]}
    capability_status = {str(item["name"]): str(item["status"]) for item in record["capabilities"]}
    missing: list[str] = []
    missing.extend(sorted(test_id for test_id, state in test_results.items() if state != "PASS"))
    missing.extend(
        sorted(f"capability_review:{name}" for name, state in capability_status.items() if state == "NOT_TESTED")
    )
    missing.extend(
        sorted(f"core_capability:{name}" for name in CORE_PASS_CAPABILITIES if capability_status[name] != "PASS")
    )
    if record["owner_present"] is not True:
        missing.append("owner_present")
    if record["external_operator_write_activity_recorded"] is not True:
        # A complete install + rollback cycle necessarily involved physical
        # writes. Recording that fact avoids a misleading all-green bundle.
        missing.append("external_operator_write_activity_recorded")

    failures = sorted(name for name, state in capability_status.items() if state == "FAIL")
    candidate_ready = not missing
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
        "physical_test_results": test_results,
        "capability_status": capability_status,
        "verified_evidence_files": sorted(verified_files, key=lambda item: str(item["path"])),
        "physical_validation_evidence_complete": True,
        "support_candidate_review_ready": candidate_ready,
        "known_capability_failures": failures,
        "missing_requirements": sorted(set(missing)),
        "support_status": "NOT_SUPPORTED",
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
    return result


def validate_physical_validation_report(report: object) -> dict[str, object]:
    if not isinstance(report, dict) or set(report) != REPORT_KEYS:
        raise DevicePhysicalValidationError("Physical validation report must match schema v1 exactly.")
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
    if report["tool_write_authorized"] is not False:
        raise DevicePhysicalValidationError("Physical validation tooling cannot authorize writes.")
    if type(report["owner_present"]) is not bool or type(report["external_operator_write_activity_recorded"]) is not bool:
        raise DevicePhysicalValidationError("Physical validation report booleans are malformed.")

    tests = report["physical_test_results"]
    if not isinstance(tests, dict) or set(tests) != set(PHYSICAL_TEST_IDS):
        raise DevicePhysicalValidationError("Physical validation report test inventory is invalid.")
    if any(value not in TEST_OUTCOMES for value in tests.values()):
        raise DevicePhysicalValidationError("Physical validation report contains an invalid test outcome.")
    capabilities = report["capability_status"]
    if not isinstance(capabilities, dict) or set(capabilities) != set(CAPABILITY_NAMES):
        raise DevicePhysicalValidationError("Physical validation report capability inventory is invalid.")
    if any(value not in CAPABILITY_STATES for value in capabilities.values()):
        raise DevicePhysicalValidationError("Physical validation report contains an invalid capability state.")

    files = report["verified_evidence_files"]
    expected_file_count = len(PHYSICAL_TEST_IDS) + sum(1 for value in capabilities.values() if value != "NOT_TESTED")
    if not isinstance(files, list) or len(files) != expected_file_count:
        raise DevicePhysicalValidationError("Verified evidence file inventory is incomplete.")
    seen_paths: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256", "kind", "verified"}:
            raise DevicePhysicalValidationError("Verified evidence file entry is malformed.")
        path = _relative_path(item["path"], "verified evidence path")
        if path in seen_paths:
            raise DevicePhysicalValidationError("Verified evidence file inventory contains duplicates.")
        seen_paths.add(path)
        if type(item["size"]) is not int or item["size"] <= 0 or item["size"] > MAX_EVIDENCE_BYTES:
            raise DevicePhysicalValidationError("Verified evidence file size is invalid.")
        _sha256(item["sha256"], "verified evidence sha256")
        if item["kind"] not in EVIDENCE_KINDS or item["verified"] is not True:
            raise DevicePhysicalValidationError("Verified evidence file metadata is invalid.")

    expected_missing: list[str] = []
    expected_missing.extend(sorted(test_id for test_id, state in tests.items() if state != "PASS"))
    expected_missing.extend(
        sorted(f"capability_review:{name}" for name, state in capabilities.items() if state == "NOT_TESTED")
    )
    expected_missing.extend(
        sorted(f"core_capability:{name}" for name in CORE_PASS_CAPABILITIES if capabilities[name] != "PASS")
    )
    if report["owner_present"] is not True:
        expected_missing.append("owner_present")
    if report["external_operator_write_activity_recorded"] is not True:
        expected_missing.append("external_operator_write_activity_recorded")
    expected_missing = sorted(set(expected_missing))

    if report["physical_validation_evidence_complete"] is not True:
        raise DevicePhysicalValidationError("Physical validation evidence-complete flag is invalid.")
    if report["missing_requirements"] != expected_missing:
        raise DevicePhysicalValidationError("Physical validation missing-requirements projection was modified.")
    if report["support_candidate_review_ready"] is not (not expected_missing):
        raise DevicePhysicalValidationError("Support-candidate review flag is inconsistent with evidence.")
    failures = sorted(name for name, state in capabilities.items() if state == "FAIL")
    if report["known_capability_failures"] != failures:
        raise DevicePhysicalValidationError("Known capability failure list is inconsistent.")
    if report["support_status"] != "NOT_SUPPORTED":
        raise DevicePhysicalValidationError("Physical validation schema v1 cannot claim supported status.")
    for key in (
        "support_claim_allowed", "profile_promotion_allowed", "install_allowed",
        "device_write_allowed", "root_allowed", "status_promotion_performed",
    ):
        if report[key] is not False:
            raise DevicePhysicalValidationError(f"{key} must remain false in physical validation schema v1.")
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
    """Bind a readiness projection to exact, locally verified physical evidence files."""
    readiness_raw, readiness_file_sha = _load_json(readiness_path)
    try:
        readiness = validate_device_support_readiness(readiness_raw)
    except (DeviceSupportReadinessError, ValueError) as exc:
        raise DevicePhysicalValidationError("Readiness evidence failed validation.") from exc
    record_raw, _record_file_sha = _load_json(record_path)
    record = validate_physical_validation_record(record_raw)
    if not evidence_root.is_absolute() or not evidence_root.is_dir() or evidence_root.is_symlink():
        raise DevicePhysicalValidationError("Evidence root must be an existing absolute non-symlink directory.")

    verified_files: list[dict[str, object]] = []
    for entry in (*record["tests"], *record["capabilities"]):
        verified = _verify_evidence(evidence_root, entry)
        if verified is not None:
            verified_files.append(verified)

    result = _derive_report(
        readiness=readiness,
        readiness_file_sha256=readiness_file_sha,
        record=record,
        verified_files=verified_files,
    )
    validate_physical_validation_report(result)
    return result
