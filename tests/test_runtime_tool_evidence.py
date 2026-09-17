from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.runtime_tool_evidence import (
    MAX_TOOL_BYTES,
    RuntimeToolEvidenceError,
    capture_runtime_tool,
    load_runtime_tool_evidence,
    verify_runtime_tool,
)


class RuntimeToolEvidenceTests(unittest.TestCase):
    def _adb(self, root: Path, data: bytes = b"trusted-adb-binary") -> Path:
        path = root / "adb"
        path.write_bytes(data)
        path.chmod(0o755)
        return path.resolve()

    def test_capture_hashes_exact_tool_without_leaking_absolute_path(self) -> None:
        with TemporaryDirectory() as folder:
            adb = self._adb(Path(folder))
            report = capture_runtime_tool(adb)
            self.assertEqual(report["schema_version"], 1)
            self.assertEqual(report["operation"], "READ_ONLY_LOCAL_TOOL_HASH")
            self.assertEqual(report["tool_name"], "adb")
            self.assertEqual(report["sha256"], hashlib.sha256(b"trusted-adb-binary").hexdigest())
            self.assertEqual(report["path_identity_sha256"], hashlib.sha256(str(adb).encode()).hexdigest())
            self.assertFalse(report["tool_executed"])
            self.assertFalse(report["device_write_allowed"])
            self.assertNotIn(str(adb), json.dumps(report, sort_keys=True))

    def test_verify_accepts_unchanged_tool_and_rejects_changed_bytes(self) -> None:
        with TemporaryDirectory() as folder:
            adb = self._adb(Path(folder))
            evidence = capture_runtime_tool(adb)
            verified = verify_runtime_tool(adb, evidence)
            self.assertTrue(verified["runtime_tool_unchanged"])
            self.assertFalse(verified["tool_executed"])
            adb.write_bytes(b"changed-adb-binary")
            adb.chmod(0o755)
            with self.assertRaises(RuntimeToolEvidenceError):
                verify_runtime_tool(adb, evidence)

    def test_rejects_relative_wrong_name_symlink_non_executable_and_writable(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            adb = self._adb(root)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(Path("adb"))
            wrong = root / "platform-tool"
            wrong.write_bytes(b"x")
            wrong.chmod(0o755)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(wrong)
            alias = root / "alias-adb"
            alias.symlink_to(adb)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(alias)
            adb.chmod(0o644)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(adb)
            adb.chmod(0o775)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(adb)

    def test_rejects_noncanonical_parent_alias_and_oversized_tool(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            real = root / "real"
            real.mkdir()
            adb = self._adb(real)
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(alias / "adb")
            adb.write_bytes(b"")
            adb.chmod(0o755)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(adb)
            with adb.open("wb") as handle:
                handle.truncate(MAX_TOOL_BYTES + 1)
            adb.chmod(0o755)
            with self.assertRaises(RuntimeToolEvidenceError):
                capture_runtime_tool(adb)

    def test_loader_rejects_duplicate_keys_symlink_and_forged_write_state(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            evidence_file = root / "evidence.json"
            evidence_file.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(RuntimeToolEvidenceError):
                load_runtime_tool_evidence(evidence_file)
            alias = root / "evidence-link.json"
            alias.symlink_to(evidence_file)
            with self.assertRaises(RuntimeToolEvidenceError):
                load_runtime_tool_evidence(alias)

            adb = self._adb(root)
            report = capture_runtime_tool(adb)
            report["device_write_allowed"] = True
            with self.assertRaises(RuntimeToolEvidenceError):
                verify_runtime_tool(adb, report)
            report = capture_runtime_tool(adb)
            report["tool_executed"] = True
            with self.assertRaises(RuntimeToolEvidenceError):
                verify_runtime_tool(adb, report)

    def test_loader_and_verifier_round_trip_strict_json(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            adb = self._adb(root)
            report = capture_runtime_tool(adb)
            evidence_file = root / "runtime-tool.json"
            evidence_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
            loaded = load_runtime_tool_evidence(evidence_file)
            result = verify_runtime_tool(adb, loaded)
            self.assertTrue(result["runtime_tool_unchanged"])
            self.assertEqual(result["recorded_sha256"], result["observed_sha256"])


if __name__ == "__main__":
    unittest.main()
