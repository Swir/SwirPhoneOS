from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from swirphoneos.aosp_source_tool_evidence import capture_source_tools, verify_source_tools
from swirphoneos.aosp_source_tool_trust_bundle import (
    AospSourceToolTrustBundleError,
    create_source_tool_trust_bundle,
)


@unittest.skipUnless(os.name == "posix", "AOSP source-tool evidence is Linux/POSIX-builder specific")
class AospSourceToolTrustBundleTests(unittest.TestCase):
    def _bin(self, root: Path) -> Path:
        bin_dir = (root / "bin").resolve()
        bin_dir.mkdir()
        for name in ("repo", "git"):
            path = bin_dir / name
            path.write_bytes(("exact-" + name).encode("ascii"))
            path.chmod(0o755)
        return bin_dir

    def _run(self, scope: str = "BUILD_ONLY") -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "source_commit": "1" * 40,
            "scope": scope,
            "expected_product": "swirphoneos_cf_x86_64",
            "workspace_sha256": "2" * 64,
            "staged_content_sha256": "3" * 64,
            "build_fingerprint": "Swir/test/test:17/ID/1:userdebug/test-keys",
            "build_fingerprint_sha256": "4" * 64,
            "app_manifest_sha256": "5" * 64,
            "source_ready_packages": ["org.swir.phoneos.settings"],
            "report_file_sha256": {"build": "6" * 64},
            "build_chain_complete": True,
            "runtime_chain_complete": scope == "BUILD_AND_RUNTIME",
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
            "warnings": ["synthetic test fixture"],
        }
        payload["run_evidence_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        payload["run_evidence_complete"] = True
        return payload

    def _write(self, root: Path, bin_dir: Path, scope: str = "BUILD_ONLY") -> dict[str, Path]:
        with patch.dict(os.environ, {"PATH": str(bin_dir)}):
            capture = capture_source_tools()
            post_sync = verify_source_tools(capture)
            post_build = verify_source_tools(capture)
        reports = {
            "run": self._run(scope),
            "capture": capture,
            "post_sync": post_sync,
            "post_build": post_build,
        }
        paths: dict[str, Path] = {}
        for name, report in reports.items():
            path = (root / f"{name}.json").resolve()
            path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
            paths[name] = path
        return paths

    def _create(self, paths: dict[str, Path]) -> dict[str, object]:
        return create_source_tool_trust_bundle(
            paths["run"], paths["capture"], paths["post_sync"], paths["post_build"]
        )

    def test_accepts_exact_repo_git_continuity_for_build_only(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            paths = self._write(root, self._bin(root))
            result = self._create(paths)
        self.assertTrue(result["source_tools_unchanged_across_sync_and_build"])
        self.assertTrue(result["source_tool_trust_chain_complete"])
        self.assertEqual(set(result["tool_sha256"]), {"repo", "git"})
        self.assertFalse(result["device_write_allowed"])
        self.assertFalse(result["physical_device_support_claimed"])
        self.assertFalse(result["status_promotion_performed"])
        self.assertEqual(len(result["source_tool_trust_bundle_sha256"]), 64)

    def test_accepts_build_and_runtime_scope_without_claiming_runtime_gate(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            paths = self._write(root, self._bin(root), scope="BUILD_AND_RUNTIME")
            result = self._create(paths)
        self.assertEqual(result["aosp_run_scope"], "BUILD_AND_RUNTIME")
        self.assertFalse(result["status_promotion_performed"])

    def test_rejects_post_build_tool_drift_even_if_report_is_rehashed(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            paths = self._write(root, self._bin(root))
            post = json.loads(paths["post_build"].read_text(encoding="utf-8"))
            post["tools"][0]["sha256"] = "f" * 64
            paths["post_build"].write_text(json.dumps(post, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospSourceToolTrustBundleError):
                self._create(paths)

    def test_rejects_overclaim_and_invalid_run_digest(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            paths = self._write(root, self._bin(root))
            run = json.loads(paths["run"].read_text(encoding="utf-8"))
            run["device_write_allowed"] = True
            canonical = {k: v for k, v in run.items() if k not in {"run_evidence_sha256", "run_evidence_complete"}}
            run["run_evidence_sha256"] = hashlib.sha256(
                json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            paths["run"].write_text(json.dumps(run, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospSourceToolTrustBundleError):
                self._create(paths)

    def test_rejects_duplicate_json_keys(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            paths = self._write(root, self._bin(root))
            paths["capture"].write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(AospSourceToolTrustBundleError):
                self._create(paths)


if __name__ == "__main__":
    unittest.main()
