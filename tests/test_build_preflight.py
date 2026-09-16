from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.build_preflight import (
    BuildPreflightError,
    HostSnapshot,
    MIN_FREE_BYTES,
    MIN_RAM_BYTES,
    capture_host,
    evaluate_preflight,
)


def ready_snapshot(**overrides: object) -> HostSnapshot:
    values: dict[str, object] = {
        "system": "linux",
        "machine": "x86_64",
        "glibc_version": "2.39",
        "ram_bytes": MIN_RAM_BYTES,
        "free_bytes": MIN_FREE_BYTES,
        "commands": {
            "git": True,
            "repo": True,
            "bash": True,
            "python3": True,
            "curl": True,
            "zip": True,
            "unzip": True,
        },
        "kvm_available": True,
    }
    values.update(overrides)
    return HostSnapshot(**values)  # type: ignore[arg-type]


class BuildPreflightTests(unittest.TestCase):
    def test_ready_host_passes_sync_and_full_build(self) -> None:
        result = evaluate_preflight(ready_snapshot())
        self.assertTrue(result["ready_for_source_sync"])
        self.assertTrue(result["ready_for_full_build"])
        self.assertTrue(result["cuttlefish_kvm_available"])
        self.assertEqual(result["operation"], "READ_ONLY_HOST_PREFLIGHT")

    def test_low_ram_blocks_full_build_but_not_source_sync(self) -> None:
        result = evaluate_preflight(ready_snapshot(ram_bytes=MIN_RAM_BYTES - 1))
        self.assertTrue(result["ready_for_source_sync"])
        self.assertFalse(result["ready_for_full_build"])

    def test_unknown_ram_blocks_full_build(self) -> None:
        result = evaluate_preflight(ready_snapshot(ram_bytes=None))
        self.assertTrue(result["ready_for_source_sync"])
        self.assertFalse(result["ready_for_full_build"])

    def test_low_disk_blocks_sync_and_build(self) -> None:
        result = evaluate_preflight(ready_snapshot(free_bytes=MIN_FREE_BYTES - 1))
        self.assertFalse(result["ready_for_source_sync"])
        self.assertFalse(result["ready_for_full_build"])

    def test_non_linux_or_wrong_arch_blocks(self) -> None:
        for changes in ({"system": "windows"}, {"machine": "aarch64"}):
            with self.subTest(changes=changes):
                result = evaluate_preflight(ready_snapshot(**changes))
                self.assertFalse(result["ready_for_source_sync"])
                self.assertFalse(result["ready_for_full_build"])

    def test_old_or_unknown_glibc_blocks(self) -> None:
        for value in ("2.16", None, "unknown"):
            with self.subTest(value=value):
                result = evaluate_preflight(ready_snapshot(glibc_version=value))
                self.assertFalse(result["ready_for_source_sync"])

    def test_missing_repo_or_git_blocks(self) -> None:
        for command in ("repo", "git"):
            commands = dict(ready_snapshot().commands)
            commands[command] = False
            with self.subTest(command=command):
                result = evaluate_preflight(ready_snapshot(commands=commands))
                self.assertFalse(result["ready_for_source_sync"])

    def test_kvm_is_reported_but_not_a_source_sync_gate(self) -> None:
        result = evaluate_preflight(ready_snapshot(kvm_available=False))
        self.assertTrue(result["ready_for_source_sync"])
        self.assertTrue(result["ready_for_full_build"])
        self.assertFalse(result["cuttlefish_kvm_available"])

    def test_relative_workspace_is_rejected_without_host_mutation(self) -> None:
        with self.assertRaises(BuildPreflightError):
            capture_host(Path("relative"))

    def test_missing_absolute_workspace_is_rejected(self) -> None:
        with self.assertRaises(BuildPreflightError):
            capture_host(Path("/definitely-not-a-real-swirphoneos-path"))

    def test_existing_absolute_workspace_can_be_inspected(self) -> None:
        with TemporaryDirectory() as folder:
            snapshot = capture_host(Path(folder).resolve())
            self.assertGreaterEqual(snapshot.free_bytes, 0)
            self.assertIsInstance(snapshot.commands, dict)


if __name__ == "__main__":
    unittest.main()
