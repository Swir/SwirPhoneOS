"""Create-only read-only device capture sessions for physical support evidence.

A capture session helps an owner collect one ADB observation and one
Fastboot/FastbootD observation across a manual mode transition. It reuses the
strict read-only transport inspectors and existing cross-transport correlator.

The session only writes local JSON evidence. It never reboots, unlocks, erases,
flashes, roots, installs, restores or otherwise mutates a connected phone.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from .diagnostics import DiagnosticError, validate_adb_report
from .fastboot import FastbootDiagnosticError, validate_fastboot_report
from .hardware_evidence import HardwareEvidenceError, create_hardware_evidence, validate_hardware_evidence
from .identity import IdentityAssessmentError, validate_unified_report
from .profiles import DeviceProfile, discover_profiles, load_profile_snapshot

SCHEMA_VERSION = 1
SESSION_SOURCE = "swirphoneos_read_only_device_capture_session"
BUNDLE_SOURCE = "swirphoneos_read_only_device_capture_bundle"
REGISTRY_SOURCE = "swirphoneos_device_profile_registry_snapshot"
MAX_JSON_BYTES = 2 * 1024 * 1024
SAFE_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
TRANSPORTS = ("adb", "fastboot")
SESSION_FILENAME = "session.json"
REPORT_FILENAMES = {"adb": "adb-report.json", "fastboot": "fastboot-report.json"}
HARDWARE_FILENAME = "hardware-evidence.json"
BUNDLE_FILENAME = "capture-bundle.json"
WARNINGS = [
    "This session stores read-only evidence only and never authorizes or executes a device write.",
    "ADB/Fastboot values and matching serial digests remain observations, not cryptographic hardware identity proof.",
    "A complete capture bundle is still NOT hardware verification and cannot promote a device profile or beta gate.",
]


class DeviceCaptureSessionError(ValueError):
    """Raised when a capture session is incomplete, mutable or contradictory."""


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DeviceCaptureSessionError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _timestamp(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) > 32 or not value.endswith("Z"):
        raise DeviceCaptureSessionError(f"{field} must be a UTC Z timestamp.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DeviceCaptureSessionError(f"{field} is invalid.") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise DeviceCaptureSessionError(f"{field} must be UTC.")
    return value


def _safe_session_id(value: object) -> str:
    if not isinstance(value, str) or not SAFE_SESSION_ID.fullmatch(value):
        raise DeviceCaptureSessionError("session_id must be a bounded safe token.")
    return value


def _safe_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise DeviceCaptureSessionError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _load_json_file(path: Path) -> tuple[dict[str, object], str]:
    if path.is_symlink() or not path.is_file():
        raise DeviceCaptureSessionError("Evidence input must be an existing regular file, not a symlink.")
    try:
        size = path.stat().st_size
        if size <= 0 or size > MAX_JSON_BYTES:
            raise DeviceCaptureSessionError("Evidence input has an invalid size.")
        raw = path.read_bytes()
        if len(raw) != size:
            raise DeviceCaptureSessionError("Evidence input changed while it was being read.")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except DeviceCaptureSessionError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DeviceCaptureSessionError("Evidence input could not be read as strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise DeviceCaptureSessionError("Evidence input root must be an object.")
    return value, _sha256_bytes(raw)


def _write_create_only(path: Path, value: object) -> str:
    raw = _canonical_bytes(value)
    if len(raw) > MAX_JSON_BYTES:
        raise DeviceCaptureSessionError("Evidence output is oversized.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise DeviceCaptureSessionError("Evidence output already exists; capture files are create-only.") from exc
    except OSError as exc:
        raise DeviceCaptureSessionError("Evidence output could not be created.") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise DeviceCaptureSessionError("Evidence output could not be persisted safely.") from exc
    return _sha256_bytes(raw)


def _session_directory(path: Path, *, must_exist: bool) -> Path:
    if not path.is_absolute():
        raise DeviceCaptureSessionError("Session directory must be an absolute path.")
    if path.name in {"", ".", ".."}:
        raise DeviceCaptureSessionError("Session directory name is invalid.")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise DeviceCaptureSessionError("Session parent must be an existing regular directory, not a symlink.")
    if must_exist:
        if path.is_symlink() or not path.is_dir():
            raise DeviceCaptureSessionError("Session directory must be an existing regular directory, not a symlink.")
    else:
        if path.exists() or path.is_symlink():
            raise DeviceCaptureSessionError("Session directory must not already exist.")
    return path


def registry_snapshot(profiles_root: Path) -> tuple[dict[str, object], list[DeviceProfile]]:
    """Return exact profile-file digests for the currently reviewed registry."""
    profiles = discover_profiles(profiles_root)
    entries: list[dict[str, str]] = []
    for profile in sorted(profiles, key=lambda item: item.profile_id):
        profile_path = profiles_root.joinpath(*profile.profile_id.split("/"), "profile.json")
        loaded, digest = load_profile_snapshot(profile_path)
        if loaded != profile:
            raise DeviceCaptureSessionError("Device profile changed during registry snapshot.")
        entries.append({"profile_id": profile.profile_id, "profile_sha256": digest})
    core: dict[str, object] = {
        "schema_version": 1,
        "source": REGISTRY_SOURCE,
        "profiles": entries,
    }
    snapshot = dict(core)
    snapshot["registry_sha256"] = _canonical_sha256(core)
    validate_registry_snapshot(snapshot)
    return snapshot, profiles


def validate_registry_snapshot(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "source", "profiles", "registry_sha256"}:
        raise DeviceCaptureSessionError("Registry snapshot schema is invalid.")
    if value["schema_version"] != 1 or value["source"] != REGISTRY_SOURCE:
        raise DeviceCaptureSessionError("Registry snapshot provenance is invalid.")
    profiles = value["profiles"]
    if not isinstance(profiles, list) or not profiles or len(profiles) > 256:
        raise DeviceCaptureSessionError("Registry snapshot profile inventory is invalid.")
    seen: set[str] = set()
    previous = ""
    for item in profiles:
        if not isinstance(item, dict) or set(item) != {"profile_id", "profile_sha256"}:
            raise DeviceCaptureSessionError("Registry snapshot entry schema is invalid.")
        profile_id = item["profile_id"]
        if not isinstance(profile_id, str) or not profile_id or len(profile_id) > 129 or not profile_id.isascii():
            raise DeviceCaptureSessionError("Registry snapshot profile id is invalid.")
        if profile_id in seen or profile_id <= previous:
            raise DeviceCaptureSessionError("Registry snapshot entries must be unique and sorted.")
        seen.add(profile_id)
        previous = profile_id
        _safe_sha256(item["profile_sha256"], "profile_sha256")
    digest = _safe_sha256(value["registry_sha256"], "registry_sha256")
    core = {key: value[key] for key in ("schema_version", "source", "profiles")}
    if digest != _canonical_sha256(core):
        raise DeviceCaptureSessionError("Registry snapshot integrity hash mismatch.")
    return value


def _validate_session(value: object) -> dict[str, object]:
    expected = {
        "schema_version", "source", "session_id", "created_utc", "registry_snapshot",
        "device_write_allowed", "support_claim_allowed", "profile_promotion_allowed", "warnings",
        "evidence_sha256",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise DeviceCaptureSessionError("Capture session schema is invalid.")
    if value["schema_version"] != SCHEMA_VERSION or value["source"] != SESSION_SOURCE:
        raise DeviceCaptureSessionError("Capture session provenance is invalid.")
    _safe_session_id(value["session_id"])
    _timestamp(value["created_utc"], "created_utc")
    validate_registry_snapshot(value["registry_snapshot"])
    for key in ("device_write_allowed", "support_claim_allowed", "profile_promotion_allowed"):
        if value[key] is not False:
            raise DeviceCaptureSessionError("Capture session cannot authorize support or device mutation.")
    if value["warnings"] != WARNINGS:
        raise DeviceCaptureSessionError("Capture session warnings were modified.")
    digest = _safe_sha256(value["evidence_sha256"], "evidence_sha256")
    core = {key: val for key, val in value.items() if key != "evidence_sha256"}
    if digest != _canonical_sha256(core):
        raise DeviceCaptureSessionError("Capture session integrity hash mismatch.")
    return value


def create_capture_session(
    session_dir: Path,
    profiles_root: Path,
    *,
    session_id: str | None = None,
    created_utc: str | None = None,
) -> dict[str, object]:
    """Create a local evidence directory and immutable session descriptor."""
    session_dir = _session_directory(session_dir, must_exist=False)
    snapshot, _ = registry_snapshot(profiles_root)
    session_id = _safe_session_id(session_id or f"capture-{uuid.uuid4().hex}")
    created_utc = created_utc or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    _timestamp(created_utc, "created_utc")
    try:
        session_dir.mkdir(mode=0o700)
    except OSError as exc:
        raise DeviceCaptureSessionError("Session directory could not be created.") from exc
    core: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source": SESSION_SOURCE,
        "session_id": session_id,
        "created_utc": created_utc,
        "registry_snapshot": snapshot,
        "device_write_allowed": False,
        "support_claim_allowed": False,
        "profile_promotion_allowed": False,
        "warnings": list(WARNINGS),
    }
    session = dict(core)
    session["evidence_sha256"] = _canonical_sha256(core)
    _validate_session(session)
    try:
        _write_create_only(session_dir / SESSION_FILENAME, session)
    except Exception:
        try:
            session_dir.rmdir()
        except OSError:
            pass
        raise
    return public_capture_status(session_dir, session=session)


def _load_session(session_dir: Path) -> tuple[dict[str, object], str]:
    session_dir = _session_directory(session_dir, must_exist=True)
    session, file_digest = _load_json_file(session_dir / SESSION_FILENAME)
    return _validate_session(session), file_digest


def _require_registry_match(session: dict[str, object], profiles_root: Path) -> list[DeviceProfile]:
    current, profiles = registry_snapshot(profiles_root)
    if current != session["registry_snapshot"]:
        raise DeviceCaptureSessionError("Device profile registry changed after this capture session was created.")
    return profiles


def _validate_transport_report(transport: str, report: object) -> dict[str, object]:
    if transport not in TRANSPORTS:
        raise DeviceCaptureSessionError("Unknown transport.")
    try:
        validate_unified_report(report)
    except IdentityAssessmentError as exc:
        raise DeviceCaptureSessionError("Unified transport report failed validation.") from exc
    assert isinstance(report, dict)
    if report["transport"] != transport:
        raise DeviceCaptureSessionError("Unified report transport does not match requested capture phase.")
    assessment = report["profile_assessment"]
    if not isinstance(assessment, dict) or assessment.get("result") != "PROFILE_HINT_ONLY":
        raise DeviceCaptureSessionError("Capture session requires one unique local metadata profile hint.")
    nested = report["transport_report"]
    try:
        if transport == "adb":
            validate_adb_report(nested, require_provenance=True)
        else:
            validate_fastboot_report(nested, require_provenance=True)
    except (DiagnosticError, FastbootDiagnosticError) as exc:
        raise DeviceCaptureSessionError("Transport report lacks exact tool/transport provenance.") from exc
    return report


def record_transport_report(
    session_dir: Path,
    profiles_root: Path,
    *,
    transport: str,
    report: dict[str, object],
) -> dict[str, object]:
    """Persist one exact read-only transport observation, once."""
    session, _ = _load_session(session_dir)
    profiles = _require_registry_match(session, profiles_root)
    report = _validate_transport_report(transport, report)
    assessment = report["profile_assessment"]
    assert isinstance(assessment, dict)
    profile_id = assessment["candidate_profile_id"]
    known_ids = {profile.profile_id for profile in profiles}
    if profile_id not in known_ids:
        raise DeviceCaptureSessionError("Capture report points to a profile outside the snapshotted registry.")
    _write_create_only(session_dir / REPORT_FILENAMES[transport], report)
    return public_capture_status(session_dir, session=session)


def _load_transport(session_dir: Path, transport: str) -> tuple[dict[str, object], str]:
    report, file_digest = _load_json_file(session_dir / REPORT_FILENAMES[transport])
    return _validate_transport_report(transport, report), file_digest


def _bundle_core(
    *,
    session: dict[str, object],
    session_file_sha256: str,
    adb_file_sha256: str,
    fastboot_file_sha256: str,
    hardware_file_sha256: str,
    hardware: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": BUNDLE_SOURCE,
        "session_id": session["session_id"],
        "session_evidence_sha256": session["evidence_sha256"],
        "session_file_sha256": session_file_sha256,
        "registry_sha256": session["registry_snapshot"]["registry_sha256"],
        "adb_report_file_sha256": adb_file_sha256,
        "fastboot_report_file_sha256": fastboot_file_sha256,
        "hardware_evidence_file_sha256": hardware_file_sha256,
        "hardware_evidence_sha256": hardware["evidence_sha256"],
        "profile_id": hardware["profile_id"],
        "state": "CORRELATED_READ_ONLY_CAPTURE_COMPLETE_NOT_VERIFIED",
        "hardware_verified": False,
        "support_claim_allowed": False,
        "profile_promotion_allowed": False,
        "install_allowed": False,
        "device_write_allowed": False,
        "root_allowed": False,
        "status_promotion_performed": False,
        "warnings": list(WARNINGS),
    }


def validate_capture_bundle(bundle: object) -> dict[str, object]:
    expected = {
        "schema_version", "source", "session_id", "session_evidence_sha256", "session_file_sha256",
        "registry_sha256", "adb_report_file_sha256", "fastboot_report_file_sha256",
        "hardware_evidence_file_sha256", "hardware_evidence_sha256", "profile_id", "state",
        "hardware_verified", "support_claim_allowed", "profile_promotion_allowed", "install_allowed",
        "device_write_allowed", "root_allowed", "status_promotion_performed", "warnings", "evidence_sha256",
    }
    if not isinstance(bundle, dict) or set(bundle) != expected:
        raise DeviceCaptureSessionError("Capture bundle schema is invalid.")
    if bundle["schema_version"] != SCHEMA_VERSION or bundle["source"] != BUNDLE_SOURCE:
        raise DeviceCaptureSessionError("Capture bundle provenance is invalid.")
    _safe_session_id(bundle["session_id"])
    for key in (
        "session_evidence_sha256", "session_file_sha256", "registry_sha256",
        "adb_report_file_sha256", "fastboot_report_file_sha256",
        "hardware_evidence_file_sha256", "hardware_evidence_sha256", "evidence_sha256",
    ):
        _safe_sha256(bundle[key], key)
    if not isinstance(bundle["profile_id"], str) or not bundle["profile_id"] or len(bundle["profile_id"]) > 129:
        raise DeviceCaptureSessionError("Capture bundle profile id is invalid.")
    if bundle["state"] != "CORRELATED_READ_ONLY_CAPTURE_COMPLETE_NOT_VERIFIED":
        raise DeviceCaptureSessionError("Capture bundle state is invalid.")
    for key in (
        "hardware_verified", "support_claim_allowed", "profile_promotion_allowed", "install_allowed",
        "device_write_allowed", "root_allowed", "status_promotion_performed",
    ):
        if bundle[key] is not False:
            raise DeviceCaptureSessionError("Capture bundle cannot authorize support or device mutation.")
    if bundle["warnings"] != WARNINGS:
        raise DeviceCaptureSessionError("Capture bundle warnings were modified.")
    core = {key: value for key, value in bundle.items() if key != "evidence_sha256"}
    if bundle["evidence_sha256"] != _canonical_sha256(core):
        raise DeviceCaptureSessionError("Capture bundle integrity hash mismatch.")
    return bundle


def finalize_capture_session(session_dir: Path, profiles_root: Path) -> dict[str, object]:
    """Correlate both create-only captures and persist non-authorizing evidence."""
    session, session_file_sha = _load_session(session_dir)
    profiles = _require_registry_match(session, profiles_root)
    adb, adb_file_sha = _load_transport(session_dir, "adb")
    fastboot, fastboot_file_sha = _load_transport(session_dir, "fastboot")
    try:
        hardware = create_hardware_evidence(adb, fastboot, profiles)
    except HardwareEvidenceError as exc:
        raise DeviceCaptureSessionError("ADB/Fastboot captures could not be safely correlated.") from exc
    hardware_file_sha = _write_create_only(session_dir / HARDWARE_FILENAME, hardware)
    core = _bundle_core(
        session=session,
        session_file_sha256=session_file_sha,
        adb_file_sha256=adb_file_sha,
        fastboot_file_sha256=fastboot_file_sha,
        hardware_file_sha256=hardware_file_sha,
        hardware=hardware,
    )
    bundle = dict(core)
    bundle["evidence_sha256"] = _canonical_sha256(core)
    validate_capture_bundle(bundle)
    _write_create_only(session_dir / BUNDLE_FILENAME, bundle)
    return public_capture_status(session_dir, session=session, bundle=bundle)


def verify_capture_session(session_dir: Path, profiles_root: Path) -> dict[str, object]:
    """Re-read every persisted byte and rebuild the hardware correlation."""
    session, session_file_sha = _load_session(session_dir)
    profiles = _require_registry_match(session, profiles_root)
    adb, adb_file_sha = _load_transport(session_dir, "adb")
    fastboot, fastboot_file_sha = _load_transport(session_dir, "fastboot")
    hardware, hardware_file_sha = _load_json_file(session_dir / HARDWARE_FILENAME)
    try:
        validate_hardware_evidence(hardware)
        expected_hardware = create_hardware_evidence(adb, fastboot, profiles)
    except HardwareEvidenceError as exc:
        raise DeviceCaptureSessionError("Persisted hardware evidence failed validation.") from exc
    if hardware != expected_hardware:
        raise DeviceCaptureSessionError("Persisted hardware evidence does not match the exact transport captures.")
    bundle, _ = _load_json_file(session_dir / BUNDLE_FILENAME)
    validate_capture_bundle(bundle)
    expected_core = _bundle_core(
        session=session,
        session_file_sha256=session_file_sha,
        adb_file_sha256=adb_file_sha,
        fastboot_file_sha256=fastboot_file_sha,
        hardware_file_sha256=hardware_file_sha,
        hardware=hardware,
    )
    expected_bundle = dict(expected_core)
    expected_bundle["evidence_sha256"] = _canonical_sha256(expected_core)
    if bundle != expected_bundle:
        raise DeviceCaptureSessionError("Capture bundle does not match the exact persisted evidence bytes.")
    return public_capture_status(session_dir, session=session, bundle=bundle)


def public_capture_status(
    session_dir: Path,
    *,
    session: dict[str, object] | None = None,
    bundle: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return a path-free status suitable for CLI/Studio display."""
    if session is None:
        session, _ = _load_session(session_dir)
    captured = [
        transport
        for transport in TRANSPORTS
        if (session_dir / REPORT_FILENAMES[transport]).is_file()
        and not (session_dir / REPORT_FILENAMES[transport]).is_symlink()
    ]
    finalized = bundle is not None or (
        (session_dir / HARDWARE_FILENAME).is_file()
        and not (session_dir / HARDWARE_FILENAME).is_symlink()
        and (session_dir / BUNDLE_FILENAME).is_file()
        and not (session_dir / BUNDLE_FILENAME).is_symlink()
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "swirphoneos_read_only_capture_status",
        "session_id": session["session_id"],
        "registry_sha256": session["registry_snapshot"]["registry_sha256"],
        "captured_transports": captured,
        "finalized": finalized,
        "state": "CORRELATED_READ_ONLY_CAPTURE_COMPLETE_NOT_VERIFIED" if finalized else "READ_ONLY_CAPTURE_IN_PROGRESS",
        "hardware_evidence_sha256": bundle["hardware_evidence_sha256"] if bundle is not None else None,
        "hardware_verified": False,
        "support_claim_allowed": False,
        "profile_promotion_allowed": False,
        "install_allowed": False,
        "device_write_allowed": False,
        "root_allowed": False,
    }
