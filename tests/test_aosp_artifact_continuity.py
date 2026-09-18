from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_artifact_continuity import (
    AospArtifactContinuityError,
    _canonical_sha,
    collect_artifact_continuity,
    validate_artifact_continuity,
)


class AospArtifactContinuityTests(unittest.TestCase):
    def _workspace(self, root: Path) -> Path:
        workspace = root / "aosp"
        (workspace / ".repo").mkdir(parents=True)
        (workspace / "build").mkdir()
        (workspace / "build" / "envsetup.sh").write_text("# test\n", encoding="utf-8")
        product = workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64"
        product.mkdir(parents=True)
        (product / "boot.img").write_bytes(b"boot-image")
        (product / "system.img").write_bytes(b"system-image")
        (product / "android-info.txt").write_text("board=test\n", encoding="utf-8")
        return workspace

    def _build_report(self, workspace: Path) -> dict[str, object]:
        product = workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64"
        artifacts = []
        for name in ("boot.img", "system.img", "android-info.txt"):
            raw = (product / name).read_bytes()
            artifacts.append({"path": name, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        return {
            "schema_version": 1,
            "source": "local_aosp_build_output",
            "expected_product": "swirphoneos_cf_x86_64",
            "baseline_revision": "android-17.0.0_r1",
            "baseline_identity": {},
            "resolved_manifest": {},
            "build": {"fingerprint": "Swir/test/test:17/ID/1:userdebug/test-keys"},
            "artifacts": artifacts,
            "required_artifacts": ["boot.img", "system.img"],
            "build_evidence_complete": True,
            "device_write_allowed": False,
            "status_promotion_performed": False,
            "warnings": [],
        }

    def _run_report(self, workspace: Path, build_file_sha: str, *, scope: str = "BUILD_AND_RUNTIME") -> dict[str, object]:
        fingerprint = "Swir/test/test:17/ID/1:userdebug/test-keys"
        payload: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "source_commit": "1" * 40,
            "scope": scope,
            "expected_product": "swirphoneos_cf_x86_64",
            "workspace_sha256": hashlib.sha256(str(workspace.resolve()).encode("utf-8")).hexdigest(),
            "staged_content_sha256": "2" * 64,
            "build_fingerprint": fingerprint,
            "build_fingerprint_sha256": hashlib.sha256(fingerprint.encode("ascii")).hexdigest(),
            "app_manifest_sha256": "3" * 64,
            "source_ready_packages": ["org.swir.phoneos.settings"],
            "report_file_sha256": {"build_evidence": build_file_sha},
            "build_chain_complete": True,
            "runtime_chain_complete": scope == "BUILD_AND_RUNTIME",
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
            "warnings": [],
        }
        payload["run_evidence_sha256"] = _canonical_sha(payload)
        payload["run_evidence_complete"] = True
        return payload

    def _write_reports(self, root: Path, workspace: Path, *, scope: str = "BUILD_AND_RUNTIME") -> tuple[Path, Path]:
        build_path = root / "build-evidence.json"
        build_path.write_text(json.dumps(self._build_report(workspace), sort_keys=True), encoding="utf-8")
        build_sha = hashlib.sha256(build_path.read_bytes()).hexdigest()
        run_path = root / "run-evidence.json"
        run_path.write_text(json.dumps(self._run_report(workspace, build_sha, scope=scope), sort_keys=True), encoding="utf-8")
        return run_path.resolve(), build_path.resolve()

    def test_accepts_unchanged_exact_artifact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            result = collect_artifact_continuity(workspace.resolve(), run_path, build_path)
            digest = validate_artifact_continuity(result)
        self.assertTrue(result["artifact_bytes_unchanged_after_run"])
        self.assertTrue(result["core_images_unchanged_after_run"])
        self.assertFalse(result["release_artifact_authorized"])
        self.assertEqual(result["artifact_count"], 3)
        self.assertEqual(result["artifact_continuity_sha256"], digest)

    def test_accepts_build_only_scope_without_claiming_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace, scope="BUILD_ONLY")
            result = collect_artifact_continuity(workspace.resolve(), run_path, build_path)
        self.assertEqual(result["aosp_run_scope"], "BUILD_ONLY")
        self.assertTrue(result["artifact_continuity_complete"])

    def test_rejects_triggering_source_commit_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            with self.assertRaises(AospArtifactContinuityError):
                collect_artifact_continuity(
                    workspace.resolve(), run_path, build_path, expected_source_commit="9" * 40,
                )

    def test_rejects_artifact_tamper_after_build_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            product = workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64"
            (product / "system.img").write_bytes(b"tampered-image")
            with self.assertRaises(AospArtifactContinuityError):
                collect_artifact_continuity(workspace.resolve(), run_path, build_path)

    def test_rejects_build_report_not_bound_to_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            build = json.loads(build_path.read_text(encoding="utf-8"))
            build["warnings"] = ["changed report bytes"]
            build_path.write_text(json.dumps(build, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospArtifactContinuityError):
                collect_artifact_continuity(workspace.resolve(), run_path, build_path)

    def test_rejects_workspace_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            other = root / "other"
            (other / ".repo").mkdir(parents=True)
            (other / "build").mkdir()
            (other / "build" / "envsetup.sh").write_text("# other\n", encoding="utf-8")
            with self.assertRaises(AospArtifactContinuityError):
                collect_artifact_continuity(other.resolve(), run_path, build_path)

    def test_rejects_symlink_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            product = workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64"
            original = product / "boot.img"
            saved = root / "saved-boot.img"
            saved.write_bytes(original.read_bytes())
            original.unlink()
            try:
                original.symlink_to(saved)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are not available on this platform")
            with self.assertRaises(AospArtifactContinuityError):
                collect_artifact_continuity(workspace.resolve(), run_path, build_path)

    def test_rejects_path_traversal_even_with_recomputed_build_file_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            build = json.loads(build_path.read_text(encoding="utf-8"))
            build["artifacts"][0]["path"] = "../boot.img"
            build_path.write_text(json.dumps(build, sort_keys=True), encoding="utf-8")
            build_sha = hashlib.sha256(build_path.read_bytes()).hexdigest()
            run = self._run_report(workspace, build_sha)
            run_path.write_text(json.dumps(run, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospArtifactContinuityError):
                collect_artifact_continuity(workspace.resolve(), run_path, build_path)

    def test_rejects_forged_release_authorization_even_with_recomputed_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            run_path, build_path = self._write_reports(root, workspace)
            result = collect_artifact_continuity(workspace.resolve(), run_path, build_path)
            result["release_artifact_authorized"] = True
            result.pop("artifact_continuity_sha256")
            result["artifact_continuity_sha256"] = _canonical_sha(result)
            with self.assertRaises(AospArtifactContinuityError):
                validate_artifact_continuity(result)

    def test_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self._workspace(root)
            _, build_path = self._write_reports(root, workspace)
            run_path = root / "duplicate.json"
            run_path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(AospArtifactContinuityError):
                collect_artifact_continuity(workspace.resolve(), run_path.resolve(), build_path)


if __name__ == "__main__":
    unittest.main()
