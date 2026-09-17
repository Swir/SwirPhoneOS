from __future__ import annotations

from pathlib import Path
import unittest


class AospWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")

    def test_builder_preflight_is_persisted_and_enforced_before_sync(self):
        preflight = self.text.index("builder-preflight.json")
        ready_gate = self.text.index('report.get("ready_for_full_build") is not True')
        sync = self.text.index("repo init -u https://android.googlesource.com/platform/manifest")
        self.assertLess(preflight, ready_gate)
        self.assertLess(ready_gate, sync)
        self.assertIn('report.get("cuttlefish_kvm_available") is not True', self.text)

    def test_builder_preflight_uses_actual_report_check_keys(self):
        self.assertIn('item.get("id", "unknown")', self.text)
        self.assertIn('item.get("passed") is not True', self.text)
        self.assertNotIn('item.get("ok") is not True', self.text)
        self.assertNotIn('item.get("name", "unknown")', self.text)
        self.assertIn("preflight report has no checks", self.text)
        self.assertIn("preflight is internally inconsistent", self.text)

    def test_staged_source_copy_verification_is_required_before_build(self):
        stage = self.text.index("stage-report.json")
        verified = self.text.index('report.get("copy_verified") is not True')
        build = self.text.index("m -j")
        self.assertLess(stage, verified)
        self.assertLess(verified, build)
        self.assertIn('report.get("schema_version") != 4', self.text)
        self.assertIn("staged_content_sha256", self.text)

    def test_post_build_stage_reverification_precedes_build_provenance(self):
        build = self.text.index("m -j")
        reverify = self.text.index("python -m swirphoneos.stage_evidence")
        build_evidence = self.text.index("python -m swirphoneos build-evidence")
        self.assertLess(build, reverify)
        self.assertLess(reverify, build_evidence)
        self.assertIn("post-build-stage-evidence.json", self.text)

    def test_complete_run_chain_is_bound_after_build_and_optional_runtime(self):
        build_evidence = self.text.index("python -m swirphoneos build-evidence")
        run_evidence = self.text.index("python -m swirphoneos aosp-run-evidence")
        upload = self.text.index("Upload immutable evidence files")
        self.assertLess(build_evidence, run_evidence)
        self.assertLess(run_evidence, upload)
        self.assertIn('--source-commit "$GITHUB_SHA"', self.text)
        self.assertIn("--post-stage", self.text)
        self.assertIn("--runtime", self.text)
        self.assertIn("--smoke", self.text)
        self.assertIn("--bundle", self.text)
        self.assertIn("aosp-run-evidence.json", self.text)

    def test_preflight_and_stage_reports_are_uploaded_even_on_failure(self):
        self.assertIn("if: ${{ always() }}", self.text)
        self.assertIn("builder-preflight.json", self.text)
        self.assertIn("stage-report.json", self.text)
        self.assertIn("post-build-stage-evidence.json", self.text)
        self.assertIn("aosp-run-evidence.json", self.text)
        self.assertIn("if-no-files-found: error", self.text)


if __name__ == "__main__":
    unittest.main()
