from __future__ import annotations

from pathlib import Path
import unittest


WORKFLOW = Path(".github/workflows/aosp-build-request.yml")


class AospBuildRequestWorkflowTests(unittest.TestCase):
    def test_request_workflow_is_hosted_main_only_and_least_privilege(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "workflow_dispatch:",
            "contents: read",
            "actions: write",
            "group: swir-aosp-build-request",
            "cancel-in-progress: false",
            "runs-on: ubuntu-latest",
            "timeout-minutes: 10",
            "persist-credentials: false",
            'test "$GH_API_URL" = "https://api.github.com"',
            'test "$GH_DEFAULT_BRANCH" = "main"',
            'test "$GITHUB_REF" = "refs/heads/main"',
            "actions/runs/{run_id}",
            "SwirPhoneOS-aosp-builder-admission",
            "swirphoneos.aosp_build_request",
            "aosp-build-evidence.yml/dispatches",
            "aosp-build-request-report.json",
        )
        for token in required:
            self.assertIn(token, text)

        forbidden = (
            "contents: write",
            "pull_request:\n",
            "pull_request_target:",
            "schedule:",
            "runs-on: [self-hosted",
            "repo init",
            "repo sync",
            "launch_cvd",
            "adb ",
            "fastboot",
            "sudo ",
            "rm -rf",
        )
        for token in forbidden:
            self.assertNotIn(token, text)

    def test_build_dispatch_is_admission_bound_not_user_supplied_job_budget(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("admission_run_id:", text)
        self.assertIn("collect_runtime:", text)
        self.assertNotIn("\n      jobs:\n", text)
        self.assertIn("builder-admission.json", text)
        self.assertIn("builder-admission-envelope.json", text)
        self.assertIn('--preflight "$GITHUB_WORKSPACE/admission/builder-admission.json"', text)
        self.assertIn('--source-commit "$GITHUB_SHA"', text)
        self.assertIn('--repository "$GITHUB_REPOSITORY"', text)
        self.assertIn('--admission-run-id "$SWIR_ADMISSION_RUN_ID"', text)
        self.assertIn('--collect-runtime "$SWIR_COLLECT_RUNTIME"', text)

    def test_build_dispatch_validates_github_2026_response_fail_closed(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "response.read(4097)",
            "status != 200",
            "GitHub AOSP build dispatch response is empty or oversized.",
            "object_pairs_hook=strict_object",
            'expected_keys = {"workflow_run_id", "run_url", "html_url"}',
            "GitHub AOSP build dispatch response field set is not exact.",
            "GitHub AOSP build dispatch workflow run id is malformed.",
            "GitHub AOSP build dispatch run URL is inconsistent.",
            "GitHub AOSP build dispatch HTML URL is inconsistent.",
            '"operation": "AOSP_BUILD_WORKFLOW_DISPATCH"',
            '"build_verified": False',
            '"boot_verified": False',
            '"status_promotion_performed": False',
            "aosp-build-dispatch-status.json",
        )
        for token in required:
            self.assertIn(token, text)

        self.assertNotIn("status not in {200, 204}", text)
        self.assertNotIn("aosp-build-dispatch-status.txt", text)


if __name__ == "__main__":
    unittest.main()
