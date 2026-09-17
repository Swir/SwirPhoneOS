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
            'repo sync -c --no-tags --optimized-fetch --prune -j"$SWIR_REQUESTED_JOBS"',
            'm -j"$SWIR_REQUESTED_JOBS"',
            '--adb "$SWIR_ADB_PATH"',
            "runtime-tool-evidence.json",
            "runtime-tool-prelaunch-verification.json",
            "runtime-tool-post-verification.json",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, workflow)

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
        ):
            self.assertIn(name, upload)
        self.assertNotIn("flash ", workflow)
        self.assertNotIn("fastboot flash", workflow)


if __name__ == "__main__":
    unittest.main()
