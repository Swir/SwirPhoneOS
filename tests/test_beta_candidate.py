from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest

from swirphoneos.beta_candidate import (
    BetaCandidateError,
    REQUIRED_GATES,
    load_candidate_manifest,
    validate_candidate_manifest,
    verify_candidate_bundle,
    verify_candidate_bundle_from_files,
)
from swirphoneos.beta_candidate_cli import main as cli_main


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: str, data: bytes, kind: str) -> dict[str, object]:
    return {"path": path, "sha256": digest(data), "size": len(data), "kind": kind}


class BetaCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.commit = "a" * 40
        self.version = "0.0.2.dev0"
        self.gate_files = {}
        self.ledger = {
            "schema_version": 1,
            "version": self.version,
            "candidate_commit": self.commit,
            "milestones": [],
            "beta_gates": [],
        }
        for index, gate_id in enumerate(sorted(REQUIRED_GATES)):
            path = f"evidence/{index:02d}-{gate_id}.json"
            data = (f'{{"gate":"{gate_id}","verified_fixture":true}}\n').encode()
            self._write(path, data)
            self.gate_files[path] = data
            self.ledger["beta_gates"].append({"id": gate_id, "passed": True, "evidence": [path]})

        self.artifact_files = {
            "release/system.img": (b"os-image-fixture", "os_image"),
            "release/SwirPhoneStudio.exe": (b"windows-package-fixture", "windows_package"),
            "release/release-manifest.json": (b'{"fixture":true}\n', "release_manifest"),
            "release/SHA256SUMS": (b"fixture sums\n", "checksums"),
        }
        for path, (data, _) in self.artifact_files.items():
            self._write(path, data)

        self.manifest_data = {
            "schema_version": 1,
            "candidate_commit": self.commit,
            "version": self.version,
            "evidence": [
                record(path, data, "gate_evidence")
                for path, data in sorted(self.gate_files.items())
            ],
            "release_artifacts": [
                record(path, data, kind)
                for path, (data, kind) in sorted(self.artifact_files.items())
            ],
        }
        self.manifest = validate_candidate_manifest(self.manifest_data)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, relative: str, data: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def _write_json(self, relative: str, value: object) -> Path:
        path = self.root / relative
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def test_exact_bundle_is_bound_but_release_remains_blocked(self):
        result = verify_candidate_bundle(self.ledger, self.manifest, self.root)
        self.assertTrue(result["candidate_binding_verified"])
        self.assertEqual(result["beta_gate_count"], 9)
        self.assertEqual(result["gate_reference_count"], 9)
        self.assertEqual(result["verified_gate_evidence_files"], 9)
        self.assertEqual(result["verified_release_artifacts"], 4)
        self.assertFalse(result["semantic_gate_validation_complete"])
        self.assertFalse(result["beta_release_allowed"])
        self.assertFalse(result["device_write_allowed"])
        self.assertFalse(result["status_promotion_performed"])

    def test_unpassed_gate_is_rejected(self):
        ledger = deepcopy(self.ledger)
        ledger["beta_gates"][0]["passed"] = False
        with self.assertRaises(BetaCandidateError):
            verify_candidate_bundle(ledger, self.manifest, self.root)

    def test_candidate_commit_mismatch_is_rejected(self):
        data = deepcopy(self.manifest_data)
        data["candidate_commit"] = "b" * 40
        with self.assertRaises(BetaCandidateError):
            verify_candidate_bundle(self.ledger, validate_candidate_manifest(data), self.root)

    def test_evidence_reference_must_match_manifest_exactly(self):
        ledger = deepcopy(self.ledger)
        ledger["beta_gates"][0]["evidence"] = ["evidence/unbound.json"]
        with self.assertRaises(BetaCandidateError):
            verify_candidate_bundle(ledger, self.manifest, self.root)

    def test_hash_tamper_is_rejected(self):
        path = self.root / sorted(self.gate_files)[0]
        path.write_bytes(b"tampered")
        with self.assertRaises(BetaCandidateError):
            verify_candidate_bundle(self.ledger, self.manifest, self.root)

    def test_size_tamper_is_rejected(self):
        data = deepcopy(self.manifest_data)
        data["release_artifacts"][0]["size"] += 1
        with self.assertRaises(BetaCandidateError):
            verify_candidate_bundle(self.ledger, validate_candidate_manifest(data), self.root)

    def test_missing_release_kind_is_rejected(self):
        data = deepcopy(self.manifest_data)
        data["release_artifacts"] = [
            item for item in data["release_artifacts"] if item["kind"] != "checksums"
        ]
        with self.assertRaises(BetaCandidateError):
            validate_candidate_manifest(data)

    def test_duplicate_path_across_sets_is_rejected(self):
        data = deepcopy(self.manifest_data)
        data["release_artifacts"][0]["path"] = data["evidence"][0]["path"]
        with self.assertRaises(BetaCandidateError):
            validate_candidate_manifest(data)

    def test_path_traversal_is_rejected(self):
        data = deepcopy(self.manifest_data)
        data["evidence"][0]["path"] = "../escape.json"
        with self.assertRaises(BetaCandidateError):
            validate_candidate_manifest(data)

    @unittest.skipIf(os.name == "nt", "Symlink creation is not reliably available to unprivileged Windows CI.")
    def test_symlink_evidence_is_rejected(self):
        target = self._write("outside.json", b"outside")
        link = self.root / "evidence/link.json"
        link.symlink_to(target)
        ledger = deepcopy(self.ledger)
        old = ledger["beta_gates"][0]["evidence"][0]
        ledger["beta_gates"][0]["evidence"] = ["evidence/link.json"]
        data = deepcopy(self.manifest_data)
        for item in data["evidence"]:
            if item["path"] == old:
                item.update(path="evidence/link.json", sha256=digest(b"outside"), size=len(b"outside"))
                break
        with self.assertRaises(BetaCandidateError):
            verify_candidate_bundle(ledger, validate_candidate_manifest(data), self.root)

    def test_duplicate_json_key_is_rejected(self):
        path = self.root / "duplicate.json"
        path.write_text(
            '{"schema_version":1,"schema_version":1,"candidate_commit":"' + self.commit
            + '","version":"' + self.version + '","evidence":[],"release_artifacts":[]}',
            encoding="utf-8",
        )
        with self.assertRaises(BetaCandidateError):
            load_candidate_manifest(path)

    def test_file_loader_and_cli_remain_fail_closed(self):
        ledger_path = self._write_json("ledger.json", self.ledger)
        manifest_path = self._write_json("candidate.json", self.manifest_data)
        result = verify_candidate_bundle_from_files(ledger_path, manifest_path, self.root)
        self.assertTrue(result["candidate_binding_verified"])
        self.assertFalse(result["beta_release_allowed"])
        with redirect_stdout(StringIO()):
            code = cli_main([
                "--ledger", str(ledger_path),
                "--manifest", str(manifest_path),
                "--root", str(self.root),
            ])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
