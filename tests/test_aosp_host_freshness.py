from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from swirphoneos import aosp_host_evidence as host
from swirphoneos import aosp_host_freshness as freshness


class AospHostFreshnessTests(unittest.TestCase):
    def _tool_map(self, root: Path, suffix: bytes = b"") -> dict[str, str]:
        result: dict[str, str] = {}
        for index, name in enumerate(host.REQUIRED_COMMANDS):
            path = root / f"tool-{index}"
            path.write_bytes((name + "\n").encode("utf-8") * 3 + suffix)
            path.chmod(0o755)
            result[name] = str(path)
        return result

    def _collect(
        self,
        workspace: Path,
        tools: dict[str, str],
        *,
        free_gib: int = 500,
        ram_gib: int = 96,
        free_inodes: int = 123456,
        kvm: bool = True,
    ) -> dict[str, object]:
        with mock.patch.object(host.shutil, "which", side_effect=lambda name: tools.get(name)), \
             mock.patch.object(host.platform, "system", return_value="Linux"), \
             mock.patch.object(host.platform, "machine", return_value="x86_64"), \
             mock.patch.object(host.platform, "libc_ver", return_value=("glibc", "2.39")), \
             mock.patch.object(host.platform, "release", return_value="6.8.0-test"), \
             mock.patch.object(host, "_bounded_file_sha", return_value="a" * 64), \
             mock.patch.object(host, "_resource_snapshot", return_value={
                 "ram_bytes": ram_gib * 1024**3,
                 "free_bytes": free_gib * 1024**3,
                 "free_inodes": free_inodes,
             }), \
             mock.patch.object(host.os.path, "exists", return_value=kvm), \
             mock.patch.object(host.os, "access", return_value=kvm):
            return host.collect_host_evidence(workspace, "PRE_BUILD")

    @staticmethod
    def _raw_sha(report: dict[str, object]) -> str:
        raw = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def test_accepts_resource_drift_when_static_identity_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            admitted = self._collect(workspace, tools, free_gib=500)
            current = self._collect(workspace, tools, free_gib=420)

            result = freshness.verify_host_freshness(
                admitted,
                current,
                admitted_file_sha256=self._raw_sha(admitted),
                current_file_sha256=self._raw_sha(current),
                require_kvm=True,
                min_ram_bytes=64 * 1024**3,
                min_free_bytes=300 * 1024**3,
                min_free_inodes=100000,
            )

        self.assertTrue(result["fresh"])
        self.assertTrue(all(result["identity_continuity"].values()))
        self.assertFalse(result["device_write_allowed"])
        self.assertFalse(result["build_verified"])
        self.assertFalse(result["boot_verified"])
        self.assertFalse(result["physical_device_support_claimed"])
        self.assertFalse(result["status_promotion_performed"])
        self.assertEqual(len(result["freshness_sha256"]), 64)

    def test_rejects_exact_toolchain_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            admitted = self._collect(workspace, tools)
            first_tool = Path(next(iter(tools.values())))
            first_tool.write_bytes(first_tool.read_bytes() + b"changed")
            current = self._collect(workspace, tools)

            with self.assertRaisesRegex(freshness.AospHostFreshnessError, "toolchain_sha256"):
                freshness.verify_host_freshness(
                    admitted,
                    current,
                    admitted_file_sha256=self._raw_sha(admitted),
                    current_file_sha256=self._raw_sha(current),
                )

    def test_rejects_workspace_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_workspace = root / "aosp-a"
            second_workspace = root / "aosp-b"
            first_workspace.mkdir()
            second_workspace.mkdir()
            tools = self._tool_map(root)
            admitted = self._collect(first_workspace, tools)
            current = self._collect(second_workspace, tools)

            with self.assertRaisesRegex(freshness.AospHostFreshnessError, "workspace_identity_sha256"):
                freshness.verify_host_freshness(
                    admitted,
                    current,
                    admitted_file_sha256=self._raw_sha(admitted),
                    current_file_sha256=self._raw_sha(current),
                )

    def test_rejects_runtime_when_kvm_is_not_currently_available(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            admitted = self._collect(workspace, tools, kvm=True)
            current = self._collect(workspace, tools, kvm=False)

            with self.assertRaisesRegex(freshness.AospHostFreshnessError, "kvm"):
                freshness.verify_host_freshness(
                    admitted,
                    current,
                    admitted_file_sha256=self._raw_sha(admitted),
                    current_file_sha256=self._raw_sha(current),
                    require_kvm=True,
                )

    def test_rejects_current_capacity_below_requested_floors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            admitted = self._collect(workspace, tools, free_gib=500, ram_gib=96, free_inodes=123456)
            current = self._collect(workspace, tools, free_gib=250, ram_gib=48, free_inodes=90000)

            with self.assertRaisesRegex(freshness.AospHostFreshnessError, "ram, free_bytes, free_inodes"):
                freshness.verify_host_freshness(
                    admitted,
                    current,
                    admitted_file_sha256=self._raw_sha(admitted),
                    current_file_sha256=self._raw_sha(current),
                    min_ram_bytes=64 * 1024**3,
                    min_free_bytes=300 * 1024**3,
                    min_free_inodes=100000,
                )

    def test_rejects_forged_write_boundary_even_with_recomputed_report_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            admitted = self._collect(workspace, tools)
            current = copy.deepcopy(admitted)
            current["device_write_allowed"] = True
            current["host_evidence_sha256"] = host._canonical_sha({
                key: value for key, value in current.items() if key != "host_evidence_sha256"
            })

            with self.assertRaises(freshness.AospHostFreshnessError):
                freshness.verify_host_freshness(
                    admitted,
                    current,
                    admitted_file_sha256=self._raw_sha(admitted),
                    current_file_sha256=self._raw_sha(current),
                )

    def test_verify_files_binds_exact_json_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "aosp"
            workspace.mkdir()
            tools = self._tool_map(root)
            admitted = self._collect(workspace, tools, free_gib=500)
            current = self._collect(workspace, tools, free_gib=450)
            admitted_path = (root / "admitted.json").resolve()
            current_path = (root / "current.json").resolve()
            admitted_raw = (json.dumps(admitted, sort_keys=True, separators=(",", ":")) + "\n").encode()
            current_raw = (json.dumps(current, sort_keys=True, separators=(",", ":")) + "\n").encode()
            admitted_path.write_bytes(admitted_raw)
            current_path.write_bytes(current_raw)

            result = freshness.verify_files(admitted_path, current_path)

        self.assertEqual(result["admitted_evidence_file_sha256"], hashlib.sha256(admitted_raw).hexdigest())
        self.assertEqual(result["current_evidence_file_sha256"], hashlib.sha256(current_raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
