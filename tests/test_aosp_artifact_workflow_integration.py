from pathlib import Path
import unittest


class AospArtifactWorkflowIntegrationTests(unittest.TestCase):
    WORKFLOW = Path(".github/workflows/aosp-postrun-artifact-continuity.yml")

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = cls.WORKFLOW.read_text(encoding="utf-8")

    def test_runs_only_after_successful_aosp_build_evidence_workflow(self) -> None:
        self.assertIn('workflows: ["AOSP build evidence"]', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.text)
        self.assertIn("group: swir-aosp-builder", self.text)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_downloads_exact_triggering_run_evidence_with_read_only_permissions(self) -> None:
        self.assertIn("actions: read", self.text)
        self.assertIn("contents: read", self.text)
        self.assertIn("actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c", self.text)
        self.assertIn("run-id: ${{ github.event.workflow_run.id }}", self.text)
        self.assertIn("swirphoneos-aosp-evidence-${{ github.event.workflow_run.head_sha }}", self.text)
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha }}", self.text)

    def test_artifact_recheck_binds_exact_workspace_run_build_and_commit(self) -> None:
        self.assertIn("python -m swirphoneos.aosp_artifact_continuity", self.text)
        self.assertIn('--workspace "$SWIR_AOSP_WORKSPACE"', self.text)
        self.assertIn('--run-evidence "$GITHUB_WORKSPACE/evidence/aosp-run-evidence.json"', self.text)
        self.assertIn('--build-evidence "$GITHUB_WORKSPACE/evidence/build-evidence.json"', self.text)
        self.assertIn('--source-commit "${{ github.event.workflow_run.head_sha }}"', self.text)
        self.assertIn('> "$GITHUB_WORKSPACE/aosp-artifact-continuity.json"', self.text)

    def test_uploads_only_bounded_continuity_report(self) -> None:
        self.assertIn("swirphoneos-aosp-postrun-continuity-${{ github.event.workflow_run.head_sha }}", self.text)
        self.assertIn("path: aosp-artifact-continuity.json", self.text)
        forbidden = ("fastboot flash", "fastboot erase", "fastboot format", "adb reboot", "repo sync", "launch_cvd", "stop_cvd")
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)


if __name__ == "__main__":
    unittest.main()
