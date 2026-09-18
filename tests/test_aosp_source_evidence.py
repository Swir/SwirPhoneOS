from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from swirphoneos.aosp_source_evidence import (
    AospSourceEvidenceError,
    collect_source_checkout_evidence,
)


@unittest.skipUnless(shutil.which("git"), "Git is required for AOSP source-integrity tests")
class AospSourceEvidenceTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str, capture: bool = False) -> str:
        command = [str(shutil.which("git")), "-C", str(repo), *args]
        if capture:
            return subprocess.check_output(command, text=True).strip()
        subprocess.check_call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ""

    def _create_repo(self, path: Path, file_name: str) -> str:
        path.mkdir(parents=True, exist_ok=True)
        self._git(path, "init", "-q")
        self._git(path, "config", "user.name", "Swir Test")
        self._git(path, "config", "user.email", "swir-test@example.invalid")
        (path / file_name).write_text("verified source\n", encoding="utf-8")
        self._git(path, "add", file_name)
        self._git(path, "commit", "-q", "-m", "fixture")
        return self._git(path, "rev-parse", "HEAD", capture=True)

    def _workspace(self, root: Path, *, nested: bool = False) -> tuple[Path, Path, dict[str, str]]:
        workspace = root / "aosp"
        (workspace / ".repo").mkdir(parents=True)
        parent = workspace / "platform" / "root"
        revisions = {"platform/root": self._create_repo(parent, "root.txt")}
        if nested:
            child = parent / "child"
            revisions["platform/root/child"] = self._create_repo(child, "child.txt")
        projects = "\n".join(
            f'  <project name="fixture-{index}" path="{path}" revision="{revision}" />'
            for index, (path, revision) in enumerate(revisions.items(), start=1)
        )
        manifest = root / "manifest.xml"
        manifest.write_text(f"<manifest>\n{projects}\n</manifest>\n", encoding="utf-8")
        return workspace, manifest, revisions

    def test_accepts_clean_exact_checkout_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, manifest, revisions = self._workspace(root, nested=True)
            first = collect_source_checkout_evidence(workspace, manifest)
            second = collect_source_checkout_evidence(workspace, manifest)
        self.assertEqual(first, second)
        self.assertEqual(first["project_count"], 2)
        self.assertEqual(first["verified_project_count"], 2)
        self.assertTrue(first["source_checkout_verified"])
        self.assertTrue(first["all_project_heads_match"])
        self.assertTrue(first["all_tracked_worktrees_clean"])
        self.assertTrue(first["all_untracked_worktrees_clean"])
        self.assertFalse(first["device_write_allowed"])
        self.assertFalse(first["build_verified"])
        self.assertFalse(first["boot_verified"])
        self.assertFalse(first["status_promotion_performed"])
        self.assertEqual(
            {item["path"]: item["revision"] for item in first["projects"]},
            revisions,
        )
        self.assertEqual(len(first["aggregate_state_sha256"]), 64)
        self.assertEqual(len(first["source_evidence_sha256"]), 64)

    def test_rejects_tracked_source_modification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, manifest, _ = self._workspace(root)
            (workspace / "platform" / "root" / "root.txt").write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(AospSourceEvidenceError):
                collect_source_checkout_evidence(workspace, manifest)

    def test_rejects_nonignored_untracked_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, manifest, _ = self._workspace(root)
            (workspace / "platform" / "root" / "unexpected.txt").write_text("drift\n", encoding="utf-8")
            with self.assertRaises(AospSourceEvidenceError):
                collect_source_checkout_evidence(workspace, manifest)

    def test_nested_repo_root_is_not_misclassified_as_untracked_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, manifest, _ = self._workspace(root, nested=True)
            result = collect_source_checkout_evidence(workspace, manifest)
        self.assertTrue(result["source_checkout_verified"])
        self.assertEqual(result["project_count"], 2)

    def test_rejects_head_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, manifest, _ = self._workspace(root)
            text = manifest.read_text(encoding="utf-8")
            manifest.write_text(text.replace('revision="', 'revision="' + "0" * 40, 1), encoding="utf-8")
            with self.assertRaises(AospSourceEvidenceError):
                collect_source_checkout_evidence(workspace, manifest)

    def test_rejects_unsafe_manifest_project_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, _manifest, revisions = self._workspace(root)
            manifest = root / "unsafe.xml"
            revision = next(iter(revisions.values()))
            manifest.write_text(
                f'<manifest><project name="unsafe" path="../escape" revision="{revision}" /></manifest>',
                encoding="utf-8",
            )
            with self.assertRaises(AospSourceEvidenceError):
                collect_source_checkout_evidence(workspace, manifest)

    @unittest.skipIf(__import__("os").name == "nt", "Windows developer runners may not grant symlink creation privileges")
    def test_rejects_symlinked_project_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, manifest, _ = self._workspace(root)
            project = workspace / "platform" / "root"
            external = root / "external"
            project.rename(external)
            project.symlink_to(external, target_is_directory=True)
            with self.assertRaises(AospSourceEvidenceError):
                collect_source_checkout_evidence(workspace, manifest)

    def test_manifest_digest_binds_exact_xml_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, manifest, _ = self._workspace(root)
            result = collect_source_checkout_evidence(workspace, manifest)
            expected = hashlib.sha256(manifest.read_bytes()).hexdigest()
        self.assertEqual(result["resolved_manifest_sha256"], expected)


if __name__ == "__main__":
    unittest.main()
