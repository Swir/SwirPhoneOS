from pathlib import Path
import unittest


class AospHostWorkflowIntegrationTests(unittest.TestCase):
    WORKFLOW = Path(".github/workflows/aosp-build-evidence.yml")

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = cls.WORKFLOW.read_text(encoding="utf-8")

    def test_pre_and_post_host_capture_bound_complete_build_window(self) -> None:
        pre_capture = self.text.index("--phase PRE_BUILD")
        source_sync = self.text.index("repo init -u https://android.googlesource.com/platform/manifest")
        build_step = self.text.index("- name: Build SwirPhoneOS Cuttlefish product")
        post_capture = self.text.index("--phase POST_BUILD")
        run_binding = self.text.index("python -m swirphoneos aosp-run-evidence")
        host_binding = self.text.index("python -m swirphoneos.aosp_host_trust_bundle")

        self.assertLess(pre_capture, source_sync)
        self.assertLess(source_sync, build_step)
        self.assertLess(build_step, post_capture)
        self.assertLess(post_capture, run_binding)
        self.assertLess(run_binding, host_binding)

    def test_workflow_has_exactly_two_host_captures_and_one_trust_binding(self) -> None:
        self.assertEqual(self.text.count("python -m swirphoneos.aosp_host_evidence"), 2)
        self.assertEqual(self.text.count("--phase PRE_BUILD"), 1)
        self.assertEqual(self.text.count("--phase POST_BUILD"), 1)
        self.assertEqual(self.text.count("python -m swirphoneos.aosp_host_trust_bundle"), 1)

    def test_all_host_evidence_files_are_preserved_in_immutable_artifact(self) -> None:
        upload = self.text.index("- name: Upload immutable evidence files")
        upload_text = self.text[upload:]
        for name in (
            "aosp-host-pre.json",
            "aosp-host-post.json",
            "aosp-host-trust-bundle.json",
        ):
            with self.subTest(name=name):
                self.assertIn(name, upload_text)

    def test_host_trust_binding_uses_exact_run_and_both_captures(self) -> None:
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
