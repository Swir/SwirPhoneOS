from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_source_trust_bundle import (
    AospSourceTrustBundleError,
    create_source_trust_bundle,
)


class AospSourceTrustBundleTests(unittest.TestCase):
    WORKSPACE = "/srv/swir/aosp"
    WORKSPACE_SHA = hashlib.sha256(WORKSPACE.encode("utf-8")).hexdigest()
    MANIFEST_SHA = "a" * 64
    REVISION = "b" * 40

    def _source_report(self) -> dict[str, object]:
        projects = [{
            "path": "build/make",
            "revision": self.REVISION,
            "head": self.REVISION,
            "head_matches_manifest": True,
            "tracked_clean": True,
            "untracked_clean": True,
        }]
        payload: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_source_checkout_integrity",
            "operation": "READ_ONLY_GIT_WORKTREE_VERIFICATION",
            "workspace_identity_sha256": self.WORKSPACE_SHA,
            "resolved_manifest_sha256": self.MANIFEST_SHA,
            "project_count": 1,
            "verified_project_count": 1,
            "git_tool": {
                "size": 12345,
                "sha256": "c" * 64,
                "path_identity_sha256": "d" * 64,
            },
            "projects": projects,
            "aggregate_state_sha256": hashlib.sha256(
                json.dumps(
                    [{"path": "build/make", "revision": self.REVISION, "head": self.REVISION}],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ).encode("utf-8")
            ).hexdigest(),
            "all_project_heads_match": True,
            "all_tracked_worktrees_clean": True,
            "all_untracked_worktrees_clean": True,
            "source_checkout_verified": True,
            "git_tool_executed_read_only": True,
            "device_write_allowed": False,
            "build_verified": False,
            "boot_verified": False,
            "status_promotion_performed": False,
            "warnings": ["one", "two", "three"],
        }
        payload["source_evidence_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        return payload

    def _resolved_report(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "project_count": 1,
            "unique_path_count": 1,
            "sha256": self.MANIFEST_SHA,
            "all_projects_pinned": True,
            "build_verified": False,
            "boot_verified": False,
        }

    def _run_report(self, resolved_file_sha: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "source_commit": "1" * 40,
            "scope": "BUILD_ONLY",
            "expected_product": "swirphoneos_cf_x86_64",
            "workspace_sha256": self.WORKSPACE_SHA,
            "staged_content_sha256": "e" * 64,
            "build_fingerprint": "Swir/test/test:17/ID/1:userdebug/test-keys",
            "build_fingerprint_sha256": "f" * 64,
            "app_manifest_sha256": "0" * 64,
            "source_ready_packages": ["org.swir.phoneos.settings"],
            "report_file_sha256": {"resolved_manifest": resolved_file_sha},
            "build_chain_complete": True,
            "runtime_chain_complete": False,
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
            "warnings": ["one"],
        }
        payload["run_evidence_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        payload["run_evidence_complete"] = True
        return payload

    def _write_fixture(self, root: Path) -> dict[str, Path]:
        resolved = self._resolved_report()
        resolved_path = root / "resolved-manifest.json"
        resolved_path.write_text(json.dumps(resolved, sort_keys=True), encoding="utf-8")
        source = self._source_report()
        pre = root / "source-pre.json"
        post = root / "source-post.json"
        pre.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
        post.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
        run = self._run_report(hashlib.sha256(resolved_path.read_bytes()).hexdigest())
        run_path = root / "run.json"
        run_path.write_text(json.dumps(run, sort_keys=True), encoding="utf-8")
        return {"run": run_path, "resolved": resolved_path, "pre": pre, "post": post}

    def _create(self, paths: dict[str, Path]) -> dict[str, object]:
        return create_source_trust_bundle(
            paths["run"].resolve(),
            paths["resolved"].resolve(),
            paths["pre"].resolve(),
            paths["post"].resolve(),
        )

    def test_accepts_exact_clean_source_continuity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write_fixture(Path(temporary))
            result = self._create(paths)
        self.assertTrue(result["source_checkout_unchanged_across_build_window"])
        self.assertTrue(result["source_trust_chain_complete"])
        self.assertEqual(result["project_count"], 1)
        self.assertEqual(result["resolved_manifest_sha256"], self.MANIFEST_SHA)
        self.assertFalse(result["device_write_allowed"])
        self.assertFalse(result["physical_device_support_claimed"])
        self.assertFalse(result["status_promotion_performed"])
        self.assertEqual(len(result["source_trust_bundle_sha256"]), 64)

    def test_rejects_source_state_change_across_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_fixture(root)
            post = json.loads(paths["post"].read_text(encoding="utf-8"))
            post["projects"][0]["revision"] = "9" * 40
            post["projects"][0]["head"] = "9" * 40
            canonical_projects = [{"path": "build/make", "revision": "9" * 40, "head": "9" * 40}]
            post["aggregate_state_sha256"] = hashlib.sha256(
                json.dumps(canonical_projects, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            post.pop("source_evidence_sha256")
            post["source_evidence_sha256"] = hashlib.sha256(
                json.dumps(post, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            paths["post"].write_text(json.dumps(post, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospSourceTrustBundleError):
                self._create(paths)

    def test_rejects_git_tool_identity_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_fixture(root)
            post = json.loads(paths["post"].read_text(encoding="utf-8"))
            post["git_tool"]["sha256"] = "8" * 64
            post.pop("source_evidence_sha256")
            post["source_evidence_sha256"] = hashlib.sha256(
                json.dumps(post, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            paths["post"].write_text(json.dumps(post, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospSourceTrustBundleError):
                self._create(paths)

    def test_rejects_resolved_manifest_file_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_fixture(root)
            resolved = json.loads(paths["resolved"].read_text(encoding="utf-8"))
            resolved["extra"] = "tamper"
            paths["resolved"].write_text(json.dumps(resolved, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospSourceTrustBundleError):
                self._create(paths)

    def test_rejects_recomputed_digest_when_safety_flag_is_forged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write_fixture(root)
            pre = json.loads(paths["pre"].read_text(encoding="utf-8"))
            pre["device_write_allowed"] = True
            pre.pop("source_evidence_sha256")
            pre["source_evidence_sha256"] = hashlib.sha256(
                json.dumps(pre, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            paths["pre"].write_text(json.dumps(pre, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospSourceTrustBundleError):
                self._create(paths)

    def test_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write_fixture(Path(temporary))
            paths["pre"].write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(AospSourceTrustBundleError):
                self._create(paths)


if __name__ == "__main__":
    unittest.main()
