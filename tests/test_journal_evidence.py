from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from swirphoneos.journal_evidence import public_journal_summary, swirroot_gate_projection, validate_journal
from swirphoneos.transaction_evidence import TransactionEvidenceError, create_journal, validate_plan, verify_artifacts


def _plan(target: bytes, rollback: bytes) -> dict[str, object]:
    return {
        "schema_version": 1,
        "transaction_id": "journal-review-001",
        "profile_id": "oneplus/avicii",
        "device_codename": "avicii",
        "device_model": "AC2003",
        "expected_current_build": "stock/example",
        "target_build": "swir/example",
        "write_enabled": False,
        "owner_confirmation_required": True,
        "rollback_required": True,
        "install_artifacts": [{"name": "target", "path": "install.img", "sha256": hashlib.sha256(target).hexdigest(), "size": len(target), "kind": "install"}],
        "rollback_artifacts": [{"name": "stock", "path": "stock.img", "sha256": hashlib.sha256(rollback).hexdigest(), "size": len(rollback), "kind": "rollback"}],
        "notes": "Journal validation test.",
    }


class JournalEvidenceTests(unittest.TestCase):
    def _journal(self) -> dict[str, object]:
        target, rollback = b"target", b"rollback"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "install.img").write_bytes(target)
            (root / "stock.img").write_bytes(rollback)
            plan = validate_plan(_plan(target, rollback))
            evidence = verify_artifacts(plan, root)
            return create_journal(root / "journal.json", plan, evidence)

    def test_valid_journal_roundtrip_summary_stays_fail_closed(self) -> None:
        journal = self._journal()
        summary = public_journal_summary(journal)
        self.assertTrue(summary["rollback_ready"])
        self.assertFalse(summary["owner_confirmation_recorded"])
        self.assertFalse(summary["write_allowed"])

    def test_tampered_build_breaks_evidence_hash(self) -> None:
        journal = self._journal()
        journal["target_build"] = "tampered/build"
        with self.assertRaises(TransactionEvidenceError):
            validate_journal(journal)

    def test_safety_boolean_cannot_be_promoted(self) -> None:
        journal = self._journal()
        journal["write_allowed"] = True
        with self.assertRaises(TransactionEvidenceError):
            validate_journal(journal)

    def test_swirroot_projection_requires_a_fresh_rollback_recheck(self) -> None:
        journal = self._journal()
        projection = swirroot_gate_projection(journal, profile_id="oneplus/avicii", exact_build="swir/example")
        self.assertTrue(projection["exact_build_match"])
        self.assertFalse(projection["rollback_material_verified"])
        self.assertTrue(projection["journal_available"])
        self.assertFalse(projection["verified_device_profile"])
        self.assertFalse(projection["owner_confirmation"])
        self.assertFalse(projection["update_state_safe"])
        self.assertFalse(projection["transition_allowed"])

    def test_wrong_build_does_not_match(self) -> None:
        projection = swirroot_gate_projection(self._journal(), profile_id="oneplus/avicii", exact_build="other/build")
        self.assertFalse(projection["exact_build_match"])
        self.assertFalse(projection["transition_allowed"])


if __name__ == "__main__":
    unittest.main()
