from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from swirphoneos.stage_evidence import StageEvidenceError, verify_post_build_stage


class StageEvidenceTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        workspace = root / "aosp"
        (workspace / ".repo").mkdir(parents=True)
        (workspace / "build").mkdir()
        (workspace / "build/envsetup.sh").write_text("# test\n", encoding="utf-8")
        first = workspace / "vendor/swir/products/AndroidProducts.mk"
        second = workspace / "vendor/swir/apps/SwirSettings/Android.bp"
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first.write_bytes(b"products\n")
        second.write_bytes(b"settings\n")
        records = []
        for path in (first, second):
            relative = path.relative_to(workspace).as_posix()
            data = path.read_bytes()
            records.append(
                {
                    "source": "ignored",
                    "source_relative": "ignored",
                    "destination": str(path),
                    "destination_relative": relative,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "copy_verified": True,
                }
            )
        report = {
            "schema_version": 4,
            "workspace": str(workspace.resolve()),
            "destination_root": str((workspace / "vendor/swir").resolve()),
            "file_count": 2,
            "files": records,
            "staged_content_sha256": "a" * 64,
            "copy_verified": True,
            "executed": True,
            "device_write_allowed": False,
        }
        report_path = root / "stage-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return workspace, report_path

    def test_exact_post_build_bytes_are_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, report = self._fixture(root)
            result = verify_post_build_stage(report, workspace)
            self.assertTrue(result["post_build_verified"])
            self.assertFalse(result["device_write_allowed"])
            self.assertEqual(result["file_count"], 2)
            self.assertEqual(result["staged_content_sha256"], "a" * 64)
            self.assertEqual(len(result["verification_sha256"]), 64)

    def test_modified_staged_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, report = self._fixture(root)
            target = workspace / "vendor/swir/products/AndroidProducts.mk"
            target.write_bytes(b"tampered\n")
            with self.assertRaises(StageEvidenceError):
                verify_post_build_stage(report, workspace)

    def test_workspace_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, report = self._fixture(root)
            other = root / "other"
            (other / ".repo").mkdir(parents=True)
            (other / "build").mkdir()
            (other / "build/envsetup.sh").write_text("# test\n", encoding="utf-8")
            with self.assertRaises(StageEvidenceError):
                verify_post_build_stage(report, other)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, report = self._fixture(root)
            report.write_text('{"schema_version":4,"schema_version":4}', encoding="utf-8")
            with self.assertRaises(StageEvidenceError):
                verify_post_build_stage(report, workspace)

    def test_write_boundary_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, report = self._fixture(root)
            value = json.loads(report.read_text(encoding="utf-8"))
            value["device_write_allowed"] = True
            report.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(StageEvidenceError):
                verify_post_build_stage(report, workspace)

    @unittest.skipIf(os.name == "nt", "symlink creation is not reliably available on Windows CI")
    def test_symlinked_staged_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, report = self._fixture(root)
            target = workspace / "vendor/swir/products/AndroidProducts.mk"
            target.unlink()
            outside = root / "outside.mk"
            outside.write_bytes(b"products\n")
            target.symlink_to(outside)
            with self.assertRaises(StageEvidenceError):
                verify_post_build_stage(report, workspace)


if __name__ == "__main__":
    unittest.main()
