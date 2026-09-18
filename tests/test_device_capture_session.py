from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.device_capture_session import (
    BUNDLE_FILENAME,
    HARDWARE_FILENAME,
    DeviceCaptureSessionError,
    create_capture_session,
    finalize_capture_session,
    record_transport_report,
    validate_capture_bundle,
    verify_capture_session,
)
from swirphoneos.diagnostics import summarize
from swirphoneos.fastboot import summarize_fastboot
from swirphoneos.identity import build_unified_report
from swirphoneos.profiles import discover_profiles


FINGERPRINT = "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys"
SERIAL = "ABC123"
SERIAL_DIGEST = hashlib.sha256(SERIAL.encode()).hexdigest()
ADB_TOOL_DIGEST = "a" * 64
FASTBOOT_TOOL_DIGEST = "b" * 64


def profile_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "oneplus/avicii",
        "display_name": "OnePlus Nord AC2003",
        "codename": "avicii",
        "model_allowlist": ["AC2003"],
        "status": "PLANNED_NOT_SUPPORTED",
        "flash_enabled": False,
        "firmware_baseline": None,
        "verified_partition_map": None,
        "validated_builds": [],
        "flash_operations": [],
        "recovery_evidence": [],
        "notes": "test metadata only",
        "sources": ["https://example.invalid/avicii"],
    }


def write_registry(root: Path) -> Path:
    registry = root / "device_packs"
    profile = registry / "oneplus" / "avicii" / "profile.json"
    profile.parent.mkdir(parents=True)
    profile.write_text(json.dumps(profile_payload(), indent=2) + "\n", encoding="utf-8")
    return registry


def unified_reports(registry: Path) -> tuple[dict[str, object], dict[str, object]]:
    profiles = discover_profiles(registry)
    adb = summarize(
        {
            "ro.product.manufacturer": "OnePlus",
            "ro.product.model": "AC2003",
            "ro.product.device": "avicii",
            "ro.build.fingerprint": FINGERPRINT,
            "ro.boot.slot": "a",
            "ro.boot.slot_suffix": "_a",
            "ro.boot.flash.locked": "0",
            "ro.boot.verifiedbootstate": "orange",
            "ro.boot.vbmeta.device_state": "unlocked",
        },
        transport_serial_sha256=SERIAL_DIGEST,
        tool_sha256=ADB_TOOL_DIGEST,
    )
    fastboot = summarize_fastboot(
        {
            "product": "avicii",
            "current-slot": "a",
            "slot-count": "2",
            "unlocked": "yes",
            "is-userspace": "no",
            "secure": "yes",
            "has-slot:boot": "yes",
            "partition-size:boot": "0x06000000",
        },
        transport_serial_sha256=SERIAL_DIGEST,
        tool_sha256=FASTBOOT_TOOL_DIGEST,
    )
    return (
        build_unified_report("adb", adb, profiles),
        build_unified_report("fastboot", fastboot, profiles),
    )


class DeviceCaptureSessionTests(unittest.TestCase):
    def test_complete_capture_is_create_only_and_non_authorizing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            created = create_capture_session(
                session,
                registry,
                session_id="capture-test-001",
                created_utc="2026-09-18T12:00:00Z",
            )
            self.assertEqual(created["captured_transports"], [])
            self.assertFalse(created["finalized"])

            adb, fastboot = unified_reports(registry)
            after_adb = record_transport_report(session, registry, transport="adb", report=adb)
            self.assertEqual(after_adb["captured_transports"], ["adb"])
            after_fastboot = record_transport_report(session, registry, transport="fastboot", report=fastboot)
            self.assertEqual(after_fastboot["captured_transports"], ["adb", "fastboot"])

            finalized = finalize_capture_session(session, registry)
            self.assertTrue(finalized["finalized"])
            self.assertEqual(finalized["state"], "CORRELATED_READ_ONLY_CAPTURE_COMPLETE_NOT_VERIFIED")
            for key in (
                "hardware_verified",
                "support_claim_allowed",
                "profile_promotion_allowed",
                "install_allowed",
                "device_write_allowed",
                "root_allowed",
            ):
                self.assertFalse(finalized[key])

            verified = verify_capture_session(session, registry)
            self.assertEqual(verified["hardware_evidence_sha256"], finalized["hardware_evidence_sha256"])
            self.assertTrue((session / HARDWARE_FILENAME).is_file())
            self.assertTrue((session / BUNDLE_FILENAME).is_file())

    def test_raw_transport_serial_is_never_persisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-002", created_utc="2026-09-18T12:00:00Z")
            adb, fastboot = unified_reports(registry)
            record_transport_report(session, registry, transport="adb", report=adb)
            record_transport_report(session, registry, transport="fastboot", report=fastboot)
            finalize_capture_session(session, registry)
            for path in session.iterdir():
                if path.is_file():
                    self.assertNotIn(SERIAL, path.read_text(encoding="utf-8"))

    def test_duplicate_transport_capture_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-003", created_utc="2026-09-18T12:00:00Z")
            adb, _ = unified_reports(registry)
            record_transport_report(session, registry, transport="adb", report=adb)
            before = (session / "adb-report.json").read_bytes()
            with self.assertRaises(DeviceCaptureSessionError):
                record_transport_report(session, registry, transport="adb", report=adb)
            self.assertEqual((session / "adb-report.json").read_bytes(), before)

    def test_registry_change_between_phases_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-004", created_utc="2026-09-18T12:00:00Z")
            adb, _ = unified_reports(registry)
            record_transport_report(session, registry, transport="adb", report=adb)

            profile_path = registry / "oneplus" / "avicii" / "profile.json"
            changed = profile_payload()
            changed["notes"] = "changed after capture"
            profile_path.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")

            _, fastboot = unified_reports(registry)
            with self.assertRaises(DeviceCaptureSessionError):
                record_transport_report(session, registry, transport="fastboot", report=fastboot)

    def test_cross_transport_serial_mismatch_does_not_create_final_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-005", created_utc="2026-09-18T12:00:00Z")
            adb, fastboot = unified_reports(registry)
            fastboot = copy.deepcopy(fastboot)
            fastboot["transport_report"]["transport_serial_sha256"] = hashlib.sha256(b"OTHER").hexdigest()
            record_transport_report(session, registry, transport="adb", report=adb)
            record_transport_report(session, registry, transport="fastboot", report=fastboot)
            with self.assertRaises(DeviceCaptureSessionError):
                finalize_capture_session(session, registry)
            self.assertFalse((session / HARDWARE_FILENAME).exists())
            self.assertFalse((session / BUNDLE_FILENAME).exists())

    def test_missing_tool_provenance_is_rejected_before_persist(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-006", created_utc="2026-09-18T12:00:00Z")
            adb, _ = unified_reports(registry)
            adb = copy.deepcopy(adb)
            adb["transport_report"]["tool_sha256"] = None
            with self.assertRaises(DeviceCaptureSessionError):
                record_transport_report(session, registry, transport="adb", report=adb)
            self.assertFalse((session / "adb-report.json").exists())

    def test_tampered_transport_bytes_break_final_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-007", created_utc="2026-09-18T12:00:00Z")
            adb, fastboot = unified_reports(registry)
            record_transport_report(session, registry, transport="adb", report=adb)
            record_transport_report(session, registry, transport="fastboot", report=fastboot)
            finalize_capture_session(session, registry)

            path = session / "adb-report.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["transport_report"]["model"] = "OTHER"
            path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(DeviceCaptureSessionError):
                verify_capture_session(session, registry)

    def test_bundle_safety_flag_tampering_is_rejected_even_with_recomputed_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-008", created_utc="2026-09-18T12:00:00Z")
            adb, fastboot = unified_reports(registry)
            record_transport_report(session, registry, transport="adb", report=adb)
            record_transport_report(session, registry, transport="fastboot", report=fastboot)
            finalize_capture_session(session, registry)

            bundle = json.loads((session / BUNDLE_FILENAME).read_text(encoding="utf-8"))
            bundle["device_write_allowed"] = True
            core = {key: value for key, value in bundle.items() if key != "evidence_sha256"}
            raw = (json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
            bundle["evidence_sha256"] = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(DeviceCaptureSessionError):
                validate_capture_bundle(bundle)

    def test_non_unique_profile_hint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = write_registry(root)
            other = profile_payload()
            other["id"] = "vendor/other"
            other["display_name"] = "Other"
            other["model_allowlist"] = ["AC2003"]
            other["codename"] = "other"
            other_path = registry / "vendor" / "other" / "profile.json"
            other_path.parent.mkdir(parents=True)
            other_path.write_text(json.dumps(other, indent=2) + "\n", encoding="utf-8")

            session = root / "capture"
            create_capture_session(session, registry, session_id="capture-test-009", created_utc="2026-09-18T12:00:00Z")
            profiles = discover_profiles(registry)
            adb = summarize(
                {
                    "ro.product.model": "AC2003",
                    "ro.product.device": "avicii",
                    "ro.build.fingerprint": FINGERPRINT,
                },
                transport_serial_sha256=SERIAL_DIGEST,
                tool_sha256=ADB_TOOL_DIGEST,
            )
            ambiguous = build_unified_report("adb", adb, profiles)
            self.assertEqual(ambiguous["profile_assessment"]["result"], "AMBIGUOUS_PROFILE_HINT")
            with self.assertRaises(DeviceCaptureSessionError):
                record_transport_report(session, registry, transport="adb", report=ambiguous)


if __name__ == "__main__":
    unittest.main()
