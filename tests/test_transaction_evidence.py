from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.transaction_evidence import (
    TransactionEvidenceError,
    create_journal,
    load_plan,
    public_plan_summary,
    validate_plan,
    verify_artifacts,
)


def artifact(name: str, path: str, payload: bytes, kind: str) -> dict[str, object]:
    return {
        "name": name,
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
        "kind": kind,
    }


def valid_plan(install: bytes = b"new-image", rollback: bytes = b"stock-image") -> dict[str, object]:
    return {
        "schema_version": 1,
        "transaction_id": "avicii-review-001",
        "profile_id": "oneplus/avicii",
        "device_codename": "avicii",
        "device_model": "AC2003",
        "expected_current_build": "stock/fingerprint/example",
        "target_build": "swir/fingerprint/example",
        "write_enabled": False,
        "owner_confirmation_required": True,
        "rollback_required": True,
        "install_artifacts": [artifact("target_image", "install/target.img", install, "install")],
        "rollback_artifacts": [artifact("stock_image", "rollback/stock.img", rollback, "rollback")],
        "notes": "Preparation evidence only; no device write is authorized.",
    }


class TransactionPlanValidationTests(unittest.TestCase):
    def test_valid_plan_is_always_read_only(self) -> None:
        plan = validate_plan(valid_plan())
        summary = public_plan_summary(plan)
        self.assertFalse(plan.write_allowed)
        self.assertFalse(summary["write_allowed"])
        self.assertTrue(summary["rollback_required"])
        self.assertEqual(summary["state"], "PLAN_ONLY")

    def test_plan_hash_is_canonical(self) -> None:
        first = valid_plan()
        second = dict(reversed(list(first.items())))
        self.assertEqual(validate_plan(first).canonical_sha256, validate_plan(second).canonical_sha256)

    def test_rejects_write_enable(self) -> None:
        data = valid_plan()
        data["write_enabled"] = True
        with self.assertRaises(TransactionEvidenceError):
            validate_plan(data)

    def test_rejects_missing_owner_confirmation_requirement(self) -> None:
        data = valid_plan()
        data["owner_confirmation_required"] = False
        with self.assertRaises(TransactionEvidenceError):
            validate_plan(data)

    def test_rejects_missing_rollback_requirement(self) -> None:
        data = valid_plan()
        data["rollback_required"] = False
        with self.assertRaises(TransactionEvidenceError):
            validate_plan(data)

    def test_rejects_path_traversal(self) -> None:
        data = valid_plan()
        data["install_artifacts"][0]["path"] = "../target.img"
        with self.assertRaises(TransactionEvidenceError):
            validate_plan(data)

    def test_rejects_absolute_path(self) -> None:
        data = valid_plan()
        data["rollback_artifacts"][0]["path"] = "/tmp/stock.img"
        with self.assertRaises(TransactionEvidenceError):
            validate_plan(data)

    def test_rejects_duplicate_global_paths(self) -> None:
        data = valid_plan()
        data["rollback_artifacts"][0]["path"] = data["install_artifacts"][0]["path"]
        with self.assertRaises(TransactionEvidenceError):
            validate_plan(data)

    def test_rejects_unknown_fields(self) -> None:
        data = valid_plan()
        data["commands"] = []
        with self.assertRaises(TransactionEvidenceError):
            validate_plan(data)

    def test_load_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(TransactionEvidenceError):
                load_plan(path)


class ArtifactVerificationTests(unittest.TestCase):
    def _workspace(self, root: Path, install: bytes, rollback: bytes) -> None:
        (root / "install").mkdir()
        (root / "rollback").mkdir()
        (root / "install" / "target.img").write_bytes(install)
        (root / "rollback" / "stock.img").write_bytes(rollback)

    def test_verifies_exact_install_and_rollback_bytes(self) -> None:
        install, rollback = b"new-image", b"stock-image"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._workspace(root, install, rollback)
            evidence = verify_artifacts(validate_plan(valid_plan(install, rollback)), root)
            self.assertTrue(evidence["all_artifacts_verified"])
            self.assertTrue(evidence["rollback_ready"])
            self.assertFalse(evidence["write_allowed"])
            self.assertFalse(evidence["owner_confirmation_recorded"])

    def test_rejects_tampered_artifact(self) -> None:
        install, rollback = b"new-image", b"stock-image"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._workspace(root, install, rollback)
            (root / "install" / "target.img").write_bytes(b"bad-image")
            with self.assertRaises(TransactionEvidenceError):
                verify_artifacts(validate_plan(valid_plan(install, rollback)), root)

    def test_rejects_size_mismatch_before_hash_acceptance(self) -> None:
        install, rollback = b"new-image", b"stock-image"
        data = valid_plan(install, rollback)
        data["install_artifacts"][0]["size"] = len(install) + 1
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._workspace(root, install, rollback)
            with self.assertRaises(TransactionEvidenceError):
                verify_artifacts(validate_plan(data), root)

    def test_requires_absolute_artifact_root(self) -> None:
        with self.assertRaises(TransactionEvidenceError):
            verify_artifacts(validate_plan(valid_plan()), Path("relative"))

    def test_rejects_symlink_artifact_when_supported(self) -> None:
        install, rollback = b"new-image", b"stock-image"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._workspace(root, install, rollback)
            target = root / "install" / "target.img"
            real = root / "install" / "real.img"
            target.rename(real)
            try:
                target.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation is not available on this host")
            with self.assertRaises(TransactionEvidenceError):
                verify_artifacts(validate_plan(valid_plan(install, rollback)), root)


class JournalTests(unittest.TestCase):
    def test_create_only_journal_binds_plan_and_verified_artifacts(self) -> None:
        install, rollback = b"new-image", b"stock-image"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            ArtifactVerificationTests()._workspace(root, install, rollback)
            plan = validate_plan(valid_plan(install, rollback))
            evidence = verify_artifacts(plan, root)
            destination = root / "journal.json"
            payload = create_journal(destination, plan, evidence)
            on_disk = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(on_disk, payload)
            self.assertEqual(payload["plan_sha256"], plan.canonical_sha256)
            self.assertEqual(payload["state"], "ARTIFACTS_VERIFIED_READ_ONLY")
            self.assertFalse(payload["write_allowed"])
            self.assertFalse(payload["owner_confirmation_recorded"])
            self.assertRegex(payload["evidence_sha256"], r"^[0-9a-f]{64}$")
            with self.assertRaises(TransactionEvidenceError):
                create_journal(destination, plan, evidence)

    def test_journal_rejects_evidence_from_another_plan(self) -> None:
        install, rollback = b"new-image", b"stock-image"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            ArtifactVerificationTests()._workspace(root, install, rollback)
            plan = validate_plan(valid_plan(install, rollback))
            evidence = verify_artifacts(plan, root)
            other_data = valid_plan(install, rollback)
            other_data["transaction_id"] = "different-review"
            other = validate_plan(other_data)
            with self.assertRaises(TransactionEvidenceError):
                create_journal(root / "journal.json", other, evidence)


if __name__ == "__main__":
    unittest.main()
