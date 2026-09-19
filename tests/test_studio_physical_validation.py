from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.device_physical_validation import (
    PHYSICAL_TEST_IDS,
    SOURCE,
    WARNINGS,
)
from swirphoneos.device_support_readiness import CAPABILITY_NAMES
from swirphoneos.i18n import CATALOGS, translate
from swirphoneos.studio_evidence import (
    StudioEvidenceError,
    load_public_device_physical_validation_summary,
    public_device_physical_validation_summary,
)
from swirphoneos.studio_physical_validation import (
    load_and_render_physical_validation,
    render_physical_validation_summary,
)


def _canonical_sha256(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _binding(name: str, *, state: str, index: int, capability: bool) -> dict[str, object]:
    if capability and state == "NOT_TESTED":
        return {
            "state": state,
            "evidence_path": None,
            "evidence_sha256": None,
            "evidence_size": None,
            "evidence_kind": None,
            "observed_utc": "2026-09-19T20:00:00Z",
            "notes": f"{name} has not been tested.",
            "evidence_verified": False,
        }
    prefix = "capabilities" if capability else "tests"
    return {
        "state": state,
        "evidence_path": f"{prefix}/{name}.json",
        "evidence_sha256": f"{index + 1:064x}",
        "evidence_size": index + 1,
        "evidence_kind": "MANUAL_OBSERVATION" if capability else "HYBRID",
        "observed_utc": "2026-09-19T20:00:00Z",
        "notes": f"Reviewed {name}.",
        "evidence_verified": True,
    }


def _report(*, camera: str = "PASS") -> dict[str, object]:
    tests = {
        name: _binding(name, state="PASS", index=index, capability=False)
        for index, name in enumerate(PHYSICAL_TEST_IDS)
    }
    capabilities = {
        name: _binding(
            name,
            state=(camera if name == "camera" else "PASS"),
            index=index + 64,
            capability=True,
        )
        for index, name in enumerate(CAPABILITY_NAMES)
    }
    failures = ["camera"] if camera == "FAIL" else []
    missing = ["capability_review:camera"] if camera == "NOT_TESTED" else []
    core: dict[str, object] = {
        "schema_version": 2,
        "source": SOURCE,
        "validation_session_id": "avicii-physical-studio-002",
        "profile_id": "oneplus/avicii",
        "device_model": "AC2003",
        "device_codename": "avicii",
        "observed_current_build": "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys",
        "target_build": "Swir/swirphoneos_gsi_arm64/generic_arm64:17/CP2A.260605.016/test:userdebug/test-keys",
        "profile_sha256": "a" * 64,
        "readiness_file_sha256": "b" * 64,
        "readiness_evidence_sha256": "c" * 64,
        "hardware_evidence_sha256": "d" * 64,
        "journal_evidence_sha256": "e" * 64,
        "owner_present": True,
        "external_operator_write_activity_recorded": True,
        "tool_write_authorized": False,
        "physical_test_bindings": tests,
        "capability_bindings": capabilities,
        "evidence_inventory_verified": True,
        "support_candidate_review_ready": camera != "NOT_TESTED",
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
    result = dict(core)
    result["evidence_sha256"] = _canonical_sha256(core)
    return result


class StudioPhysicalValidationTests(unittest.TestCase):
    def test_summary_is_bounded_and_non_authorizing(self):
        summary = public_device_physical_validation_summary(_report(camera="FAIL"))
        self.assertEqual(summary["source"], "swirphoneos_studio_physical_validation_summary")
        self.assertEqual(summary["profile_id"], "oneplus/avicii")
        self.assertTrue(summary["support_candidate_review_ready"])
        self.assertEqual(summary["known_capability_failures"], ["camera"])
        self.assertEqual(summary["support_status"], "NOT_SUPPORTED")
        self.assertFalse(summary["support_claim_allowed"])
        self.assertFalse(summary["profile_promotion_allowed"])
        self.assertFalse(summary["install_allowed"])
        self.assertFalse(summary["device_write_allowed"])
        self.assertFalse(summary["root_allowed"])
        self.assertEqual(len(summary["evidence_sha256"]), 64)
        self.assertNotIn("hardware_evidence_sha256", summary)
        self.assertNotIn("physical_test_bindings", summary)
        self.assertNotIn("capability_bindings", summary)

    def test_absolute_json_roundtrip_and_localized_render(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "physical-validation.json"
            path.write_text(json.dumps(_report(camera="FAIL")), encoding="utf-8")
            summary, text = load_and_render_physical_validation(path, "pl")
            self.assertEqual(summary["validation_session_id"], "avicii-physical-studio-002")
            self.assertIn(translate("pl", "device_capability_camera"), text)
            self.assertNotIn("{session}", text)
            self.assertFalse(summary["device_write_allowed"])

    def test_every_checked_in_host_locale_renders_same_safe_projection(self):
        summary = public_device_physical_validation_summary(_report(camera="FAIL"))
        for language in CATALOGS:
            with self.subTest(language=language):
                text = render_physical_validation_summary(summary, language)
                self.assertIn("oneplus/avicii", text)
                self.assertIn(translate(language, "device_capability_camera"), text)
                self.assertNotIn("{candidate}", text)
                self.assertNotIn("{writes}", text)

    def test_relative_path_rejected(self):
        with self.assertRaises(StudioEvidenceError):
            load_public_device_physical_validation_summary(Path("physical-validation.json"))

    def test_duplicate_key_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "physical-validation.json"
            path.write_text('{"schema_version":2,"schema_version":2}', encoding="utf-8")
            with self.assertRaises(StudioEvidenceError):
                load_public_device_physical_validation_summary(path)

    def test_empty_and_oversized_reports_are_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            empty = root / "empty.json"
            empty.write_bytes(b"")
            with self.assertRaises(StudioEvidenceError):
                load_public_device_physical_validation_summary(empty)
            large = root / "large.json"
            large.write_bytes(b"{" + b" " * (2 * 1024 * 1024) + b"}")
            with self.assertRaises(StudioEvidenceError):
                load_public_device_physical_validation_summary(large)

    def test_symlink_rejected(self):
        with TemporaryDirectory() as folder:
            target = Path(folder).resolve() / "target.json"
            target.write_text(json.dumps(_report()), encoding="utf-8")
            link = Path(folder).resolve() / "physical-validation.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Host does not permit creating symlinks.")
            with self.assertRaises(StudioEvidenceError):
                load_public_device_physical_validation_summary(link)

    def test_recomputed_hash_cannot_forge_support_or_write_claims(self):
        for field in ("support_claim_allowed", "profile_promotion_allowed", "install_allowed", "device_write_allowed", "root_allowed"):
            with self.subTest(field=field):
                tampered = copy.deepcopy(_report())
                tampered[field] = True
                core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
                tampered["evidence_sha256"] = _canonical_sha256(core)
                with self.assertRaises(StudioEvidenceError):
                    public_device_physical_validation_summary(tampered)


if __name__ == "__main__":
    unittest.main()
