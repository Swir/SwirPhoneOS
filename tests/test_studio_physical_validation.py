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
from swirphoneos.studio_evidence import (
    StudioEvidenceError,
    load_public_device_physical_validation_summary,
    public_device_physical_validation_summary,
)


def _canonical_sha256(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _report(*, camera: str = "PASS") -> dict[str, object]:
    capabilities = {name: "PASS" for name in CAPABILITY_NAMES}
    capabilities["camera"] = camera
    files = []
    for index, test_id in enumerate(PHYSICAL_TEST_IDS):
        files.append({
            "path": f"tests/{test_id}.json",
            "size": index + 1,
            "sha256": f"{index + 1:064x}",
            "kind": "HYBRID",
            "verified": True,
        })
    for index, name in enumerate(CAPABILITY_NAMES, start=32):
        files.append({
            "path": f"capabilities/{name}.json",
            "size": index + 1,
            "sha256": f"{index + 1:064x}",
            "kind": "MANUAL_OBSERVATION",
            "verified": True,
        })
    failures = ["camera"] if camera == "FAIL" else []
    core: dict[str, object] = {
        "schema_version": 1,
        "source": SOURCE,
        "validation_session_id": "avicii-physical-studio-001",
        "profile_id": "oneplus/avicii",
        "device_model": "AC2003",
        "device_codename": "avicii",
        "observed_current_build": "OnePlus/avicii_EEA/avicii:12/RKQ1.211119.001/220624:user/release-keys",
        "target_build": "Swir/swirphoneos_gsi_arm64/generic_arm64:17/CP2A.260605.016/test:userdebug/test-keys",
        "profile_sha256": "c" * 64,
        "readiness_file_sha256": "d" * 64,
        "readiness_evidence_sha256": "e" * 64,
        "hardware_evidence_sha256": "a" * 64,
        "journal_evidence_sha256": "b" * 64,
        "owner_present": True,
        "external_operator_write_activity_recorded": True,
        "tool_write_authorized": False,
        "physical_test_results": {test_id: "PASS" for test_id in PHYSICAL_TEST_IDS},
        "capability_status": capabilities,
        "verified_evidence_files": sorted(files, key=lambda item: item["path"]),
        "physical_validation_evidence_complete": True,
        "support_candidate_review_ready": True,
        "known_capability_failures": failures,
        "missing_requirements": [],
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
        self.assertFalse(summary["device_write_allowed"])
        self.assertFalse(summary["root_allowed"])
        self.assertNotIn("hardware_evidence_sha256", summary)
        self.assertNotIn("verified_evidence_files", summary)

    def test_absolute_json_roundtrip(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "physical-validation.json"
            path.write_text(json.dumps(_report()), encoding="utf-8")
            summary = load_public_device_physical_validation_summary(path)
            self.assertEqual(summary["validation_session_id"], "avicii-physical-studio-001")
            self.assertFalse(summary["device_write_allowed"])

    def test_relative_path_rejected(self):
        with self.assertRaises(StudioEvidenceError):
            load_public_device_physical_validation_summary(Path("physical-validation.json"))

    def test_duplicate_key_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "physical-validation.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(StudioEvidenceError):
                load_public_device_physical_validation_summary(path)

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

    def test_recomputed_hash_cannot_forge_support_claim(self):
        tampered = copy.deepcopy(_report())
        tampered["support_claim_allowed"] = True
        core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
        tampered["evidence_sha256"] = _canonical_sha256(core)
        with self.assertRaises(StudioEvidenceError):
            public_device_physical_validation_summary(tampered)


if __name__ == "__main__":
    unittest.main()
