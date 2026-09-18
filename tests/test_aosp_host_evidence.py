from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from swirphoneos import aosp_host_evidence as host


class AospHostEvidenceTests(unittest.TestCase):
    def _tool_map(self, root: Path) -> dict[str, str]:
        result = {}
        for index, name in enumerate(host.REQUIRED_COMMANDS):
            path = root / f"tool-{index}"
            path.write_bytes((name + "\n").encode("utf-8") * 3)
            path.chmod(0o755)
            result[name] = str(path)
        return result

    def _collect(self, workspace: Path, tools: dict[str, str], phase: str = "PRE_BUILD") -> dict[str, object]:
        with mock.patch.object(host.shutil, "which", side_effect=lambda name: tools.get(name)), \
             mock.patch.object(host.platform, "system", return_value="Linux"), \
             mock.patch.object(host.platform, "machine", return_value="x86_64"), \
             mock.patch.object(host.platform, "libc_ver", return_value=("glibc", "2.39")), \
             mock.patch.object(host.platform, "release", return_value="6.8.0-test"), \
             mock.patch.object(host, "_bounded_file_sha", return_value="a" * 64), \
             mock.patch.object(host, "_resource_snapshot", return_value={
                 "ram_bytes": 96 * 1024**3,
                 "free_bytes": 500 * 1024**3,
                 "free_inodes": 123456,
             }), \
             mock.patch.object(host.os.path, "exists", return_value=True), \
             mock.patch.object(host.os, "access", return_value=True):
            return host.collect_host_evidence(workspace, phase)

    def test_collects_exact_required_tool_identity_without_raw_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            report = self._collect(workspace, tools)
            identity = host.validate_host_evidence(report, expected_phase="PRE_BUILD")

        self.assertEqual(report["tool_count"], len(host.REQUIRED_COMMANDS))
        self.assertEqual(sorted(item["name"] for item in report["tools"]), sorted(host.REQUIRED_COMMANDS))
        serialized = json.dumps(report, sort_keys=True)
        for path in tools.values():
            self.assertNotIn(path, serialized)
        self.assertFalse(report["device_write_allowed"])
        self.assertFalse(report["build_verified"])
        self.assertFalse(report["boot_verified"])
        self.assertEqual(identity[0], report["host_evidence_sha256"])
        self.assertEqual(len(report["environment_identity_sha256"]), 64)

    def test_resource_drift_changes_report_but_not_environment_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            first = self._collect(workspace, tools)
            with mock.patch.object(host.shutil, "which", side_effect=lambda name: tools.get(name)), \
                 mock.patch.object(host.platform, "system", return_value="Linux"), \
                 mock.patch.object(host.platform, "machine", return_value="x86_64"), \
                 mock.patch.object(host.platform, "libc_ver", return_value=("glibc", "2.39")), \
                 mock.patch.object(host.platform, "release", return_value="6.8.0-test"), \
                 mock.patch.object(host, "_bounded_file_sha", return_value="a" * 64), \
                 mock.patch.object(host, "_resource_snapshot", return_value={
                     "ram_bytes": 96 * 1024**3,
                     "free_bytes": 450 * 1024**3,
                     "free_inodes": 120000,
                 }), \
                 mock.patch.object(host.os.path, "exists", return_value=True), \
                 mock.patch.object(host.os, "access", return_value=True):
                second = host.collect_host_evidence(workspace, "POST_BUILD")

        self.assertEqual(first["environment_identity_sha256"], second["environment_identity_sha256"])
        self.assertNotEqual(first["host_evidence_sha256"], second["host_evidence_sha256"])

    def test_rejects_missing_required_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            tools.pop(host.REQUIRED_COMMANDS[0])
            with mock.patch.object(host.shutil, "which", side_effect=lambda name: tools.get(name)):
                with self.assertRaises(host.AospHostEvidenceError):
                    host.collect_host_evidence(workspace, "PRE_BUILD")

    def test_rejects_tampered_tool_digest_even_when_report_digest_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            report = self._collect(workspace, self._tool_map(root))
            forged = copy.deepcopy(report)
            forged["tools"][0]["sha256"] = "f" * 64
            forged["host_evidence_sha256"] = host._canonical_sha({
                key: value for key, value in forged.items() if key != "host_evidence_sha256"
            })
        with self.assertRaises(host.AospHostEvidenceError):
            host.validate_host_evidence(forged, expected_phase="PRE_BUILD")

    def test_rejects_recomputed_digest_with_write_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            report = self._collect(workspace, self._tool_map(root))
            forged = copy.deepcopy(report)
            forged["device_write_allowed"] = True
            forged["host_evidence_sha256"] = host._canonical_sha({
                key: value for key, value in forged.items() if key != "host_evidence_sha256"
            })
        with self.assertRaises(host.AospHostEvidenceError):
            host.validate_host_evidence(forged, expected_phase="PRE_BUILD")

    def test_loader_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(host.AospHostEvidenceError):
                host.load_host_evidence(path.resolve())


if __name__ == "__main__":
    unittest.main()
