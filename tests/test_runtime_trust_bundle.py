from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.runtime_trust_bundle import RuntimeTrustBundleError, create_runtime_trust_bundle
from swirphoneos.runtime_tool_evidence import capture_runtime_tool, verify_runtime_tool


def _write(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    return path.resolve()


@unittest.skipUnless(os.name == "posix", "AOSP Cuttlefish runtime-tool trust fixtures are Linux/POSIX-builder specific")
class RuntimeTrustBundleTests(unittest.TestCase):
    def _fixtures(self, root: Path) -> tuple[Path, Path, Path, Path]:
        adb = root / "adb"
        adb.write_bytes(b"exact-adb")
        adb.chmod(0o755)
        adb = adb.resolve()
        tool = capture_runtime_tool(adb)
        verification = verify_runtime_tool(adb, tool)
        run = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "scope": "BUILD_AND_RUNTIME",
            "build_chain_complete": True,
            "runtime_chain_complete": True,
            "run_evidence_complete": True,
            "run_evidence_sha256": "1" * 64,
            "build_fingerprint_sha256": "2" * 64,
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
        }
        return (
            _write(root / "run.json", run),
            _write(root / "tool.json", tool),
            _write(root / "pre.json", verification),
            _write(root / "post.json", verification),
        )

    def test_binds_complete_runtime_to_same_exact_adb(self) -> None:
        with TemporaryDirectory() as folder:
            paths = self._fixtures(Path(folder).resolve())
            result = create_runtime_trust_bundle(*paths)
            self.assertTrue(result["runtime_trust_chain_complete"])
            self.assertTrue(result["runtime_tool_unchanged_across_evidence_window"])
            self.assertFalse(result["device_write_allowed"])
            self.assertFalse(result["physical_device_support_claimed"])
            canonical = {key: value for key, value in result.items() if key != "runtime_trust_bundle_sha256"}
            expected = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
            self.assertEqual(result["runtime_trust_bundle_sha256"], expected)

    def test_rejects_build_only_run_and_write_claim(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, tool, pre, post = self._fixtures(root)
            value = json.loads(run.read_text())
            value["scope"] = "BUILD_ONLY"
            _write(run, value)
            with self.assertRaises(RuntimeTrustBundleError):
                create_runtime_trust_bundle(run, tool, pre, post)
            value["scope"] = "BUILD_AND_RUNTIME"
            value["device_write_allowed"] = True
            _write(run, value)
            with self.assertRaises(RuntimeTrustBundleError):
                create_runtime_trust_bundle(run, tool, pre, post)

    def test_rejects_changed_or_forged_adb_verification(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, tool, pre, post = self._fixtures(root)
            value = json.loads(post.read_text())
            value["observed_sha256"] = "f" * 64
            _write(post, value)
            with self.assertRaises(RuntimeTrustBundleError):
                create_runtime_trust_bundle(run, tool, pre, post)
            value = json.loads(pre.read_text())
            value["device_write_allowed"] = True
            _write(pre, value)
            with self.assertRaises(RuntimeTrustBundleError):
                create_runtime_trust_bundle(run, tool, pre, post)

    def test_rejects_duplicate_json_and_symlink_inputs(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, tool, pre, post = self._fixtures(root)
            post.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(RuntimeTrustBundleError):
                create_runtime_trust_bundle(run, tool, pre, post)
            link = root / "run-link.json"
            link.symlink_to(run)
            with self.assertRaises(RuntimeTrustBundleError):
                create_runtime_trust_bundle(link, tool, pre, post)


if __name__ == "__main__":
    unittest.main()
