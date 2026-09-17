from __future__ import annotations

import json
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


def check_map(result: dict[str, object]) -> dict[str, bool]:
    checks = result["checks"]
    assert isinstance(checks, list)
    return {
        str(item["id"]): bool(item["passed"])
        for item in checks
        if isinstance(item, dict)
    }


class BuildPreflightTests(unittest.TestCase):
    def test_ready_host_passes_sync_and_full_build(self) -> None:
        result = evaluate_preflight(ready_snapshot())
        self.assertTrue(result["ready_for_source_sync"])
        self.assertTrue(result["ready_for_full_build"])
        self.assertTrue(result["cuttlefish_kvm_available"])
        self.assertEqual(result["operation"], "READ_ONLY_HOST_PREFLIGHT")
        self.assertTrue(all(check_map(result).values()))

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

    def test_workspace_hygiene_flags_are_fail_closed(self) -> None:
        cases = {
            "workspace_writable": (False, "workspace_writable"),
            "dangerous_workspace_root": (True, "workspace_not_dangerous_root"),
            "repo_local_manifests_present": (True, "no_repo_local_manifests"),
            "repo_legacy_local_manifest_present": (True, "no_legacy_repo_local_manifest"),
            "out_tree_nonempty": (True, "fresh_out_tree"),
            "vendor_swir_is_symlink": (True, "vendor_swir_not_symlink"),
        }
        for field, (value, check_id) in cases.items():
            with self.subTest(field=field):
                result = evaluate_preflight(ready_snapshot(**{field: value}))
                self.assertFalse(result["ready_for_source_sync"])
                self.assertFalse(result["ready_for_full_build"])
                self.assertFalse(check_map(result)[check_id])

    def test_relative_workspace_is_rejected_without_host_mutation(self) -> None:
        with self.assertRaises(BuildPreflightError):
            capture_host(Path("relative"))

    def test_missing_absolute_workspace_is_rejected(self) -> None:
        with self.assertRaises(BuildPreflightError):
            capture_host(Path("/definitely-not-a-real-swirphoneos-path"))

    def test_existing_absolute_workspace_can_be_inspected_without_leaking_path(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder).resolve()
            snapshot = capture_host(path)
            result = evaluate_preflight(snapshot)
            self.assertGreaterEqual(snapshot.free_bytes, 0)
            self.assertIsInstance(snapshot.commands, dict)
            self.assertEqual(len(snapshot.workspace_identity_sha256), 64)
            self.assertNotIn(str(path), json.dumps(result, sort_keys=True))
            workspace = result["workspace"]
            self.assertIsInstance(workspace, dict)
            assert isinstance(workspace, dict)
            self.assertFalse(workspace["cleanup_performed"])

    def test_repo_local_manifest_is_detected_before_sync(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            local = root / ".repo" / "local_manifests"
            local.mkdir(parents=True)
            (local / "unreviewed.xml").write_text("<manifest />", encoding="utf-8")
            snapshot = capture_host(root)
            self.assertTrue(snapshot.repo_local_manifests_present)
            result = evaluate_preflight(snapshot)
            self.assertFalse(result["ready_for_source_sync"])
            self.assertFalse(check_map(result)["no_repo_local_manifests"])

    def test_legacy_local_manifest_is_detected_before_sync(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            repo = root / ".repo"
            repo.mkdir()
            (repo / "local_manifest.xml").write_text("<manifest />", encoding="utf-8")
            snapshot = capture_host(root)
            self.assertTrue(snapshot.repo_legacy_local_manifest_present)
            self.assertFalse(evaluate_preflight(snapshot)["ready_for_full_build"])

    def test_stale_out_tree_is_detected_without_deleting_it(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            out = root / "out" / "target" / "product" / "old"
            out.mkdir(parents=True)
            artifact = out / "system.img"
            artifact.write_bytes(b"stale")
            snapshot = capture_host(root)
            self.assertTrue(snapshot.out_tree_nonempty)
            self.assertTrue(artifact.is_file())
            result = evaluate_preflight(snapshot)
            self.assertFalse(result["ready_for_source_sync"])
            self.assertFalse(check_map(result)["fresh_out_tree"])
            self.assertTrue(artifact.is_file())

    def test_empty_local_manifest_directory_and_empty_out_are_allowed(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / ".repo" / "local_manifests").mkdir(parents=True)
            (root / "out").mkdir()
            snapshot = capture_host(root)
            self.assertFalse(snapshot.repo_local_manifests_present)
            self.assertFalse(snapshot.out_tree_nonempty)


if __name__ == "__main__":
    unittest.main()
