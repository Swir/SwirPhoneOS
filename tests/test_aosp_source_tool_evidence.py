from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from swirphoneos.aosp_source_tool_evidence import (
    AospSourceToolEvidenceError,
    EXPECTED_TOOLS,
    MAX_TOOL_BYTES,
    capture_source_tools,
    load_source_tool_evidence,
    verify_source_tools,
)


@unittest.skipUnless(os.name == "posix", "AOSP source-tool evidence is Linux/POSIX-builder specific")
class AospSourceToolEvidenceTests(unittest.TestCase):
    def _bin(self, root: Path) -> Path:
        bin_dir = (root / "bin").resolve()
        bin_dir.mkdir(parents=True)
        for name in EXPECTED_TOOLS:
            path = bin_dir / name
            path.write_bytes(("exact-" + name).encode("ascii"))
            path.chmod(0o755)
        return bin_dir

    def test_capture_hashes_path_selected_tools_without_raw_paths(self) -> None:
        with TemporaryDirectory() as folder:
            bin_dir = self._bin(Path(folder))
            with patch.dict(os.environ, {"PATH": str(bin_dir)}):
                report = capture_source_tools()
            self.assertEqual(report["tool_count"], 2)
            self.assertEqual([item["name"] for item in report["tools"]], list(EXPECTED_TOOLS))
            expected = hashlib.sha256(json.dumps(report["tools"], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
            self.assertEqual(report["toolset_sha256"], expected)
            self.assertFalse(report["tools_executed"])
            self.assertFalse(report["device_write_allowed"])
            self.assertNotIn(str(bin_dir), json.dumps(report, sort_keys=True))

    def test_verify_accepts_unchanged_tools_and_rejects_byte_drift(self) -> None:
        with TemporaryDirectory() as folder:
            bin_dir = self._bin(Path(folder))
            with patch.dict(os.environ, {"PATH": str(bin_dir)}):
                evidence = capture_source_tools()
                verified = verify_source_tools(evidence)
                self.assertTrue(verified["tools_unchanged"])
                repo = bin_dir / "repo"
                repo.write_bytes(b"changed")
                repo.chmod(0o755)
                with self.assertRaises(AospSourceToolEvidenceError):
                    verify_source_tools(evidence)

    def test_accepts_stable_lookup_symlink_but_binds_alias_and_target(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            real_bin = root / "real"
            lookup_bin = root / "lookup"
            real_bin.mkdir()
            lookup_bin.mkdir()
            for name in EXPECTED_TOOLS:
                target = real_bin / name
                target.write_bytes(("real-" + name).encode("ascii"))
                target.chmod(0o755)
                (lookup_bin / name).symlink_to(target)
            with patch.dict(os.environ, {"PATH": str(lookup_bin)}):
                report = capture_source_tools()
                self.assertTrue(all(item["lookup_is_symlink"] for item in report["tools"]))
                verified = verify_source_tools(report)
            self.assertTrue(verified["tools_unchanged"])

    def test_rejects_wrong_permissions_and_oversize(self) -> None:
        with TemporaryDirectory() as folder:
            bin_dir = self._bin(Path(folder))
            git = bin_dir / "git"
            git.chmod(0o775)
            with patch.dict(os.environ, {"PATH": str(bin_dir)}):
                with self.assertRaises(AospSourceToolEvidenceError):
                    capture_source_tools()
            git.chmod(0o755)
            with git.open("wb") as handle:
                handle.truncate(MAX_TOOL_BYTES + 1)
            with patch.dict(os.environ, {"PATH": str(bin_dir)}):
                with self.assertRaises(AospSourceToolEvidenceError):
                    capture_source_tools()

    def test_loader_rejects_duplicate_keys_symlink_and_unknown_fields(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            bin_dir = self._bin(root)
            evidence_path = root / "source-tools.json"
            evidence_path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(AospSourceToolEvidenceError):
                load_source_tool_evidence(evidence_path)
            alias = root / "source-tools-link.json"
            alias.symlink_to(evidence_path)
            with self.assertRaises(AospSourceToolEvidenceError):
                load_source_tool_evidence(alias)

            with patch.dict(os.environ, {"PATH": str(bin_dir)}):
                report = capture_source_tools()
                report["unexpected"] = False
                with self.assertRaises(AospSourceToolEvidenceError):
                    verify_source_tools(report)

    def test_round_trip_strict_json(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            bin_dir = self._bin(root)
            with patch.dict(os.environ, {"PATH": str(bin_dir)}):
                report = capture_source_tools()
                evidence_path = root / "source-tools.json"
                evidence_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                loaded = load_source_tool_evidence(evidence_path)
                verified = verify_source_tools(loaded)
            self.assertEqual(verified["toolset_sha256"], report["toolset_sha256"])
            self.assertEqual(verified["tools"], report["tools"])


if __name__ == "__main__":
    unittest.main()
