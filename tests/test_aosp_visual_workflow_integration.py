from pathlib import Path
import unittest


class AospVisualWorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path(".github/workflows/aosp-postrun-visual-evidence.yml").read_text(encoding="utf-8")

    def test_workflow_is_postrun_and_exact_sha_scoped(self):
        self.assertIn('workflows: ["AOSP build evidence"]', self.text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.text)
        self.assertIn("runs-on: [self-hosted, linux, x64, swir-aosp-builder]", self.text)
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha }}", self.text)
        self.assertIn("run-id: ${{ github.event.workflow_run.id }}", self.text)
        self.assertIn("swirphoneos-aosp-evidence-${{ github.event.workflow_run.head_sha }}", self.text)

    def test_visual_capture_is_runtime_gated_and_byte_bound(self):
        self.assertIn("has_runtime", self.text)
        self.assertIn("swirphoneos.aosp_artifact_continuity", self.text)
        self.assertIn("swirphoneos.runtime_tool_evidence verify", self.text)
        self.assertIn("swirphoneos.cuttlefish_visual_evidence", self.text)
        self.assertIn("swirphoneos.runtime_visual_trust_bundle", self.text)
        self.assertIn("runtime-visual/*.png", self.text)
        self.assertIn("stop_cvd", self.text)

    def test_workflow_does_not_add_physical_write_primitives(self):
        lowered = self.text.lower()
        for forbidden in ("fastboot flash", "fastboot erase", "fastboot format", "adb install", "adb uninstall", "adb reboot", "su -c"):
            self.assertNotIn(forbidden, lowered)


if __name__ == "__main__":
    unittest.main()
