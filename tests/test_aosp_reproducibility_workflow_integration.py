from pathlib import Path
import unittest


class AospReproducibilityWorkflowIntegrationTests(unittest.TestCase):
    WORKFLOW = Path(".github/workflows/aosp-reproducibility-pair.yml")

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = cls.WORKFLOW.read_text(encoding="utf-8")

    def test_is_manual_and_read_only(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("actions: read", self.text)
        self.assertIn("contents: read", self.text)
        forbidden = (
            "contents: write",
            "pull-requests: write",
            "fastboot flash",
            "fastboot erase",
            "fastboot format",
            "adb reboot",
            "repo sync",
            "launch_cvd",
            "stop_cvd",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)

    def test_requires_two_distinct_build_and_continuity_run_ids(self) -> None:
        for key in (
            "source_sha:",
            "build_run_a_id:",
            "continuity_run_a_id:",
            "build_run_b_id:",
            "continuity_run_b_id:",
        ):
            self.assertIn(key, self.text)
        self.assertIn('test "$BUILD_A" != "$BUILD_B"', self.text)
        self.assertIn('test "$CONTINUITY_A" != "$CONTINUITY_B"', self.text)
        self.assertIn('[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]', self.text)

    def test_downloads_evidence_from_exact_user_selected_runs(self) -> None:
        self.assertEqual(
            self.text.count("actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"),
            4,
        )
        self.assertIn("run-id: ${{ inputs.build_run_a_id }}", self.text)
        self.assertIn("run-id: ${{ inputs.continuity_run_a_id }}", self.text)
        self.assertIn("run-id: ${{ inputs.build_run_b_id }}", self.text)
        self.assertIn("run-id: ${{ inputs.continuity_run_b_id }}", self.text)
        self.assertIn("swirphoneos-aosp-evidence-${{ inputs.source_sha }}", self.text)
        self.assertIn("swirphoneos-aosp-postrun-continuity-${{ inputs.source_sha }}", self.text)

    def test_comparison_binds_exact_source_and_four_reports(self) -> None:
        self.assertIn("python -m swirphoneos.aosp_reproducibility", self.text)
        self.assertIn('--run-a "$GITHUB_WORKSPACE/evidence/run-a/aosp-run-evidence.json"', self.text)
        self.assertIn('--continuity-a "$GITHUB_WORKSPACE/continuity/run-a/aosp-artifact-continuity.json"', self.text)
        self.assertIn('--run-b "$GITHUB_WORKSPACE/evidence/run-b/aosp-run-evidence.json"', self.text)
        self.assertIn('--continuity-b "$GITHUB_WORKSPACE/continuity/run-b/aosp-artifact-continuity.json"', self.text)
        self.assertIn('--source-commit "${{ inputs.source_sha }}"', self.text)

    def test_uploads_only_bounded_pair_report(self) -> None:
        self.assertIn("swirphoneos-aosp-reproducibility-pair-${{ inputs.source_sha }}", self.text)
        self.assertIn("path: aosp-reproducibility-pair.json", self.text)
        self.assertNotIn("path: evidence", self.text)
        self.assertNotIn("path: continuity", self.text)


if __name__ == "__main__":
    unittest.main()
