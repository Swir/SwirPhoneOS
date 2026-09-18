from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.rollback_material_evidence import (
    RollbackMaterialEvidenceError,
    collect_rollback_material_evidence,
    load_rollback_material_evidence,
    validate_rollback_material_evidence,
)

ROLLBACK = b"stock-boot-image-v1"


def _journal() -> dict[str, object]:
    core = {
        "schema_version": 1,
        "transaction_id": "rollback-recheck-001",
        "profile_id": "oneplus/avicii",
        "device_codename": "avicii",
        "device_model": "AC2003",
        "expected_current_build": "stock/fingerprint",
        "target_build": "swir/target/build",
        "plan_sha256": "3" * 64,
        "state": "ARTIFACTS_VERIFIED_READ_ONLY",
        "rollback_ready": True,
        "owner_confirmation_recorded": False,
        "write_allowed": False,
        "install_artifacts": [{
            "name": "target_boot",
            "path": "target/boot.img",
            "kind": "install",
            "size": 1,
            "sha256": "1" * 64,
            "verified": True,
        }],
        "rollback_artifacts": [{
            "name": "stock_boot",
            "path": "rollback/boot.img",
            "kind": "rollback",
            "size": len(ROLLBACK),
            "sha256": hashlib.sha256(ROLLBACK).hexdigest(),
            "verified": True,
        }],
    }
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return {**core, "evidence_sha256": digest, "created_utc": "2026-09-18T00:00:00Z"}


def _root(folder: str) -> Path:
    root = Path(folder).resolve()
    (root / "rollback").mkdir()
    (root / "rollback" / "boot.img").write_bytes(ROLLBACK)
    return root


class RollbackMaterialEvidenceTests(unittest.TestCase):
    def test_rechecks_exact_bytes_and_does_not_expose_root_path(self):
        with TemporaryDirectory() as folder:
            root = _root(folder)
            report = collect_rollback_material_evidence(_journal(), root)
            self.assertTrue(report["rollback_material_verified"])
            self.assertTrue(report["all_rollback_artifacts_reverified"])
            self.assertFalse(report["device_write_allowed"])
            self.assertFalse(report["root_operation_executed"])
            encoded = json.dumps(report)
            self.assertNotIn(str(root), encoded)
            validate_rollback_material_evidence(report)

    def test_modified_bytes_rejected(self):
        with TemporaryDirectory() as folder:
            root = _root(folder)
            (root / "rollback" / "boot.img").write_bytes(b"tampered")
            with self.assertRaises(RollbackMaterialEvidenceError):
                collect_rollback_material_evidence(_journal(), root)

    def test_missing_file_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            with self.assertRaises(RollbackMaterialEvidenceError):
                collect_rollback_material_evidence(_journal(), root)

    def test_relative_artifact_root_rejected(self):
        with self.assertRaises(RollbackMaterialEvidenceError):
            collect_rollback_material_evidence(_journal(), Path("artifacts"))

    def test_symlinked_artifact_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "rollback").mkdir()
            target = root / "real.img"
            target.write_bytes(ROLLBACK)
            link = root / "rollback" / "boot.img"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Host does not permit creating symlinks.")
            with self.assertRaises(RollbackMaterialEvidenceError):
                collect_rollback_material_evidence(_journal(), root)

    def test_forged_authorization_rejected_even_after_rehash(self):
        with TemporaryDirectory() as folder:
            report = collect_rollback_material_evidence(_journal(), _root(folder))
            tampered = copy.deepcopy(report)
            tampered["device_write_allowed"] = True
            core = {key: value for key, value in tampered.items() if key != "evidence_sha256"}
            tampered["evidence_sha256"] = hashlib.sha256(
                json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
            ).hexdigest()
            with self.assertRaises(RollbackMaterialEvidenceError):
                validate_rollback_material_evidence(tampered)

    def test_duplicate_json_key_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "rollback.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(RollbackMaterialEvidenceError):
                load_rollback_material_evidence(path)

    def test_absolute_json_roundtrip(self):
        with TemporaryDirectory() as folder:
            root = _root(folder)
            report = collect_rollback_material_evidence(_journal(), root)
            path = root / "evidence.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            loaded = load_rollback_material_evidence(path)
            self.assertEqual(loaded["evidence_sha256"], report["evidence_sha256"])


if __name__ == "__main__":
    unittest.main()
