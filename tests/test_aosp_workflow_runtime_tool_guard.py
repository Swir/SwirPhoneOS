from __future__ import annotations

from pathlib import Path
import unittest


class AospWorkflowRuntimeToolGuardTests(unittest.TestCase):
    def test_runtime_tool_trust_is_bound_to_workflow_inputs(self) -> None:
        workflow = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")
        required = (
            "SWIR_REQUESTED_JOBS: ${{ inputs.jobs }}",
            "SWIR_COLLECT_RUNTIME: ${{ inputs.collect_runtime }}",
            "SWIR_ADB_PATH: ${{ inputs.adb_path }}",
            "python -m swirphoneos.runtime_tool_evidence capture",
            "python -m swirphoneos.runtime_tool_evidence verify",
            "python -m swirphoneos.cuttlefish_i18n",
            "python -m swirphoneos.runtime_review_evidence",
            "python -m swirphoneos.runtime_trust_bundle",
            "python -m swirphoneos.runtime_review_trust_bundle",
            "python -m swirphoneos.cuttlefish_host_tool_evidence capture",
            "python -m swirphoneos.cuttlefish_host_tool_evidence verify",
            "python -m swirphoneos.cuttlefish_host_tool_trust_bundle",
            'repo sync -c --no-tags --optimized-fetch --prune -j"$SWIR_REQUESTED_JOBS"',
            'm -j"$SWIR_REQUESTED_JOBS"',
            '--adb "$SWIR_ADB_PATH"',
            "runtime-tool-evidence.json",
            "runtime-tool-prelaunch-verification.json",
            "runtime-tool-post-verification.json",
            "runtime-i18n-evidence.json",
            "runtime-review-evidence.json",
            "runtime-trust-bundle.json",
            "runtime-review-trust-bundle.json",
            "cuttlefish-host-tool-evidence.json",
            "cuttlefish-host-tool-prelaunch-verification.json",
            "cuttlefish-host-tool-postreview-verification.json",
            "cuttlefish-host-tool-prestop-verification.json",
            "cuttlefish-host-tool-trust-bundle.json",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, workflow)

    def test_localization_review_finishes_before_post_runtime_tool_verification(self) -> None:
        workflow = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")
        prelaunch = workflow.index("runtime-tool-prelaunch-verification.json")
        locale_matrix = workflow.index("python -m swirphoneos.cuttlefish_i18n")
        runtime_review = workflow.index("python -m swirphoneos.runtime_review_evidence")
        post = workflow.index("runtime-tool-post-verification.json")
        trust = workflow.index("python -m swirphoneos.runtime_trust_bundle")
        final = workflow.index("python -m swirphoneos.runtime_review_trust_bundle")
        self.assertLess(prelaunch, locale_matrix)
        self.assertLess(locale_matrix, runtime_review)
        self.assertLess(runtime_review, post)
        self.assertLess(post, trust)
        self.assertLess(trust, final)

    def test_cuttlefish_launch_and_stop_use_exact_hash_verified_aosp_output_paths(self) -> None:
        workflow = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")
        capture = workflow.index("python -m swirphoneos.cuttlefish_host_tool_evidence capture")
        prelaunch = workflow.index("cuttlefish-host-tool-prelaunch-verification.json")
        launch = workflow.index('LAUNCH_CVD="$SWIR_AOSP_WORKSPACE/out/host/linux-x86/bin/launch_cvd"')
        review = workflow.index("python -m swirphoneos.runtime_review_evidence")
        postreview = workflow.index("cuttlefish-host-tool-postreview-verification.json")
        run_bind = workflow.index("python -m swirphoneos aosp-run-evidence")
        trust = workflow.index("python -m swirphoneos.cuttlefish_host_tool_trust_bundle")
        stop = workflow.index('STOP_CVD="$SWIR_AOSP_WORKSPACE/out/host/linux-x86/bin/stop_cvd"')
        prestop = workflow.index("cuttlefish-host-tool-prestop-verification.json")
        stop_exec = workflow.index('              "$STOP_CVD"')
        self.assertLess(capture, prelaunch)
        self.assertLess(prelaunch, launch)
        self.assertLess(review, postreview)
        self.assertLess(postreview, run_bind)
        self.assertLess(run_bind, trust)
        self.assertLess(trust, stop)
        self.assertLess(stop, prestop)
        self.assertLess(prestop, stop_exec)
        self.assertNotIn("command -v launch_cvd", workflow)
        self.assertNotIn("command -v stop_cvd", workflow)

    def test_dispatch_values_are_not_interpolated_directly_into_shell_commands(self) -> None:
        workflow = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")
        forbidden = (
            '--adb "${{ inputs.adb_path }}"',
            '-j"${{ inputs.jobs }}"',
            'test "${{ inputs.jobs }}"',
            'basename "${{ inputs.adb_path }}"',
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, workflow)

    def test_runtime_tool_artifacts_are_uploaded_but_do_not_claim_phone_support(self) -> None:
        workflow = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")
        upload = workflow.split("- name: Upload immutable evidence files", 1)[1]
        for name in (
            "runtime-tool-evidence.json",
            "runtime-tool-prelaunch-verification.json",
            "runtime-tool-post-verification.json",
            "runtime-i18n-evidence.json",
            "runtime-review-evidence.json",
            "runtime-trust-bundle.json",
            "runtime-review-trust-bundle.json",
            "cuttlefish-host-tool-evidence.json",
            "cuttlefish-host-tool-prelaunch-verification.json",
            "cuttlefish-host-tool-postreview-verification.json",
            "cuttlefish-host-tool-prestop-verification.json",
            "cuttlefish-host-tool-trust-bundle.json",
        ):
            self.assertIn(name, upload)
        self.assertNotIn("flash ", workflow)
        self.assertNotIn("fastboot flash", workflow)


if __name__ == "__main__":
    unittest.main()
