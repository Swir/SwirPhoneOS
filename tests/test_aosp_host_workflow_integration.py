from pathlib import Path
import unittest


class AospHostWorkflowIntegrationTests(unittest.TestCase):
    WORKFLOW = Path(".github/workflows/aosp-build-evidence.yml")

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = cls.WORKFLOW.read_text(encoding="utf-8")

    def test_host_freshness_gate_runs_immediately_before_source_sync(self) -> None:
        initial_pre_capture = self.text.index("--phase PRE_BUILD")
        marker = "- name: Re-verify exact admitted host immediately before source synchronization"
        presync_step = self.text.index(marker)
        presync_capture = self.text.index("--phase PRE_BUILD", initial_pre_capture + 1)
        freshness_gate = self.text.index("python -m swirphoneos.aosp_host_freshness", presync_step)
        source_init = self.text.index("repo init -u https://android.googlesource.com/platform/manifest")
        source_sync = self.text.index("repo sync -c --no-tags --optimized-fetch --prune")
        build_step = self.text.index("- name: Build SwirPhoneOS Cuttlefish product")
        post_capture = self.text.index("--phase POST_BUILD")
        run_binding = self.text.index("python -m swirphoneos aosp-run-evidence")
        host_binding = self.text.index("python -m swirphoneos.aosp_host_trust_bundle")

        self.assertLess(initial_pre_capture, presync_step)
        self.assertLess(presync_step, presync_capture)
        self.assertLess(presync_capture, freshness_gate)
        self.assertLess(freshness_gate, source_init)
        self.assertLess(source_init, source_sync)
        self.assertLess(source_sync, build_step)
        self.assertLess(build_step, post_capture)
        self.assertLess(post_capture, run_binding)
        self.assertLess(run_binding, host_binding)

    def test_workflow_has_exact_host_capture_and_freshness_counts(self) -> None:
        self.assertEqual(self.text.count("python -m swirphoneos.aosp_host_evidence"), 3)
        self.assertEqual(self.text.count("--phase PRE_BUILD"), 2)
        self.assertEqual(self.text.count("--phase POST_BUILD"), 1)
        self.assertEqual(self.text.count("python -m swirphoneos.aosp_host_freshness"), 1)
        self.assertEqual(self.text.count("python -m swirphoneos.aosp_host_trust_bundle"), 1)

    def test_presync_freshness_uses_exact_admission_and_current_evidence(self) -> None:
        marker = "- name: Re-verify exact admitted host immediately before source synchronization"
        start = self.text.index(marker)
        end = self.text.index("- name: Initialize and synchronize exact Android 17 tag", start)
        block = self.text[start:end]

        self.assertIn('> "$GITHUB_WORKSPACE/aosp-host-presync.json"', block)
        self.assertIn('--admitted "$GITHUB_WORKSPACE/admission/aosp-host-admission.json"', block)
        self.assertIn('--current "$GITHUB_WORKSPACE/aosp-host-presync.json"', block)
        self.assertIn('if [[ "$SWIR_COLLECT_RUNTIME" == "true" ]]; then', block)
        self.assertIn('args+=(--require-kvm)', block)
        self.assertIn('> "$GITHUB_WORKSPACE/aosp-host-presync-freshness.json"', block)

    def test_all_host_evidence_files_are_preserved_in_immutable_artifact(self) -> None:
        upload = self.text.index("- name: Upload immutable evidence files")
        upload_text = self.text[upload:]
        for name in (
            "admission/aosp-host-admission.json",
            "aosp-host-pre.json",
            "aosp-host-presync.json",
            "aosp-host-presync-freshness.json",
            "aosp-host-post.json",
            "aosp-host-trust-bundle.json",
        ):
            with self.subTest(name=name):
                self.assertIn(name, upload_text)

    def test_host_trust_binding_uses_exact_run_and_both_build_window_captures(self) -> None:
        marker = "- name: Bind exact host and toolchain continuity to completed AOSP run"
        start = self.text.index(marker)
        end = self.text.index("- name: Bind exact adb trust to completed runtime evidence", start)
        block = self.text[start:end]
        self.assertIn('--run-evidence "$GITHUB_WORKSPACE/aosp-run-evidence.json"', block)
        self.assertIn('--host-pre "$GITHUB_WORKSPACE/aosp-host-pre.json"', block)
        self.assertIn('--host-post "$GITHUB_WORKSPACE/aosp-host-post.json"', block)
        self.assertIn('> "$GITHUB_WORKSPACE/aosp-host-trust-bundle.json"', block)


if __name__ == "__main__":
    unittest.main()
