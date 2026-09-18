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

    def test_staged_source_copy_and_tree_closure_are_required_before_build(self):
        stage = self.text.index("stage-report.json")
        verified = self.text.index('report.get("copy_verified") is not True')
        closed = self.text.index('report.get("destination_tree_closed") is not True')
        build = self.text.index("m -j")
        self.assertLess(stage, verified)
        self.assertLess(verified, build)
        self.assertLess(closed, build)
        self.assertIn('report.get("schema_version") != 5', self.text)
        self.assertIn("staged_content_sha256", self.text)
        self.assertIn('report.get("destination_file_count") != len(files)', self.text)
        self.assertIn('report.get("file_count") != len(files)', self.text)
        self.assertIn("preexisting_destination_file_count", self.text)

    def test_post_build_stage_reverification_precedes_build_provenance(self):
        build = self.text.index("m -j")
        reverify = self.text.index("python -m swirphoneos.stage_evidence")
        build_evidence = self.text.index("python -m swirphoneos build-evidence")
        self.assertLess(build, reverify)
        self.assertLess(reverify, build_evidence)
        self.assertIn("post-build-stage-evidence.json", self.text)

    def test_runtime_localization_review_is_in_exact_runtime_window(self):
        prelaunch = self.text.index("runtime-tool-prelaunch-verification.json")
        smoke = self.text.index("python -m swirphoneos.cuttlefish_smoke")
        i18n = self.text.index("python -m swirphoneos.cuttlefish_i18n")
        review = self.text.index("python -m swirphoneos.runtime_review_evidence")
        post = self.text.index("runtime-tool-post-verification.json")
        self.assertLess(prelaunch, smoke)
        self.assertLess(smoke, i18n)
        self.assertLess(i18n, review)
        self.assertLess(review, post)
        self.assertIn("runtime-i18n-evidence.json", self.text)
        self.assertIn("runtime-review-evidence.json", self.text)

    def test_complete_run_chain_is_bound_after_build_and_optional_runtime(self):
        build_evidence = self.text.index("python -m swirphoneos build-evidence")
        run_evidence = self.text.index("python -m swirphoneos aosp-run-evidence")
        runtime_trust = self.text.index("python -m swirphoneos.runtime_trust_bundle")
        review_trust = self.text.index("python -m swirphoneos.runtime_review_trust_bundle")
        upload = self.text.index("Upload immutable evidence files")
        self.assertLess(build_evidence, run_evidence)
        self.assertLess(run_evidence, runtime_trust)
        self.assertLess(runtime_trust, review_trust)
        self.assertLess(review_trust, upload)
        self.assertIn('--source-commit "$GITHUB_SHA"', self.text)
        self.assertIn('--app-manifest "$GITHUB_WORKSPACE/tools/system_apps/manifest.json"', self.text)
        self.assertIn("--post-stage", self.text)
        self.assertIn("--runtime", self.text)
        self.assertIn("--smoke", self.text)
        self.assertIn("--bundle", self.text)
        self.assertIn("aosp-run-evidence.json", self.text)
        self.assertIn("runtime-review-trust-bundle.json", self.text)

    def test_failure_diagnostics_exist_before_checkout_and_track_bounded_phases(self):
        initialize = self.text.index("Initialize bounded run diagnostics")
        checkout = self.text.index("actions/checkout@")
        self.assertLess(initialize, checkout)
        self.assertIn("aosp-run-context.txt", self.text)
        self.assertIn("aosp-phase.txt", self.text)
        for phase in (
            "BOOTSTRAP", "TOOLCHAIN", "PREFLIGHT", "SOURCE_SYNC", "SOURCE_STAGE", "BUILD",
            "POST_BUILD_STAGE", "BUILD_EVIDENCE", "RUNTIME_LAUNCH", "RUNTIME_WAIT",
            "APP_SMOKE", "APP_I18N", "RUNTIME_REVIEW", "RUNTIME_BIND", "RUN_BIND", "TRUST_BIND",
        ):
            self.assertIn('"' + phase + '"', self.text)

    def test_build_failure_keeps_only_a_bounded_diagnostic_tail(self):
        self.assertIn('tee "$BUILD_LOG"', self.text)
        self.assertIn('tail -c 262144 "$BUILD_LOG"', self.text)
        self.assertIn('rm -f "$BUILD_LOG"', self.text)
        upload_block = self.text[self.text.index("Upload immutable evidence files"):]
        self.assertIn("aosp-build-tail.log", upload_block)
        self.assertNotIn("aosp-build-full.log", upload_block)

    def test_failed_run_generates_read_only_failure_evidence_before_upload(self):
        collector = self.text.index("Collect bounded failure evidence")
        upload = self.text.index("Upload immutable evidence files")
        self.assertLess(collector, upload)
        collector_block = self.text[collector:upload]
        self.assertIn("if: ${{ failure() }}", collector_block)
        self.assertIn("python -m swirphoneos.aosp_failure_cli", collector_block)
        self.assertIn('--phase "$phase"', collector_block)
        self.assertIn('--i18n "$GITHUB_WORKSPACE/runtime-i18n-evidence.json"', collector_block)
        self.assertIn('--runtime-review "$GITHUB_WORKSPACE/runtime-review-evidence.json"', collector_block)
        self.assertIn('--runtime-trust "$GITHUB_WORKSPACE/runtime-trust-bundle.json"', collector_block)
        self.assertIn('--runtime-review-trust "$GITHUB_WORKSPACE/runtime-review-trust-bundle.json"', collector_block)
        self.assertIn("aosp-failure-evidence.json", collector_block)
        self.assertIn("aosp-failure-evidence-error.txt", collector_block)

    def test_evidence_artifact_survives_early_and_late_failures(self):
        self.assertIn("if: ${{ always() }}", self.text)
        upload_block = self.text[self.text.index("Upload immutable evidence files"):]
        for name in (
            "aosp-run-context.txt",
            "aosp-phase.txt",
            "builder-preflight.json",
            "stage-report.json",
            "post-build-stage-evidence.json",
            "runtime-i18n-evidence.json",
            "runtime-review-evidence.json",
            "runtime-trust-bundle.json",
            "runtime-review-trust-bundle.json",
            "aosp-run-evidence.json",
            "aosp-failure-evidence.json",
        ):
            self.assertIn(name, upload_block)
        self.assertIn("if-no-files-found: error", upload_block)


if __name__ == "__main__":
    unittest.main()
