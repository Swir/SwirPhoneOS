from __future__ import annotations

import json
from pathlib import Path
import unittest


WORKFLOW = Path(".github/workflows/aosp-builder-admission-request.yml")
REQUEST = Path(".github/aosp-admission-request.json")
TARGET = Path(".github/workflows/aosp-builder-admission.yml")


class AospBuilderAdmissionRequestWorkflowTests(unittest.TestCase):
    def test_dispatcher_is_bounded_main_only_and_least_privilege(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "push:\n    branches: [main]",
            "- '.github/aosp-admission-request.json'",
            "workflow_dispatch:",
            "contents: read",
            "actions: write",
            "group: swir-aosp-admission-request",
            "cancel-in-progress: false",
            "runs-on: ubuntu-latest",
            "timeout-minutes: 5",
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "persist-credentials: false",
            'default_branch != "main"',
            'api_url != "https://api.github.com"',
            "aosp-builder-admission.yml/dispatches",
            '"target_ref": default_branch',
            '"build_verified": False',
            '"boot_verified": False',
            '"status_promotion_performed": False',
        )
        for token in required:
            self.assertIn(token, text)

        forbidden = (
            "contents: write",
            "pull_request:",
            "pull_request_target:",
            "schedule:",
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

    def test_checked_in_request_is_exact_and_requires_runtime_ready_builder(self) -> None:
        raw = REQUEST.read_bytes()
        self.assertGreater(len(raw), 0)
        self.assertLessEqual(len(raw), 8192)
        request = json.loads(raw.decode("utf-8"))
        self.assertEqual(
            set(request),
            {"schema_version", "operation", "request_id", "jobs", "require_kvm"},
        )
        self.assertEqual(request["schema_version"], 1)
        self.assertEqual(request["operation"], "AOSP_BUILDER_ADMISSION_REQUEST")
        self.assertEqual(request["jobs"], 16)
        self.assertIs(request["require_kvm"], True)
        self.assertRegex(request["request_id"], r"^[a-z0-9][a-z0-9._-]{0,63}$")

    def test_dispatch_target_remains_read_only_self_hosted_admission(self) -> None:
        text = TARGET.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("runs-on: [self-hosted, linux, x64, swir-aosp-builder]", text)
        self.assertIn("name: Read-only AOSP builder admission", text)
        self.assertIn("python -m swirphoneos build-preflight", text)
        self.assertIn("python -m swirphoneos.aosp_host_evidence", text)
        self.assertNotIn("repo sync", text)
        self.assertNotIn("launch_cvd", text)
        self.assertNotIn("fastboot", text)


if __name__ == "__main__":
    unittest.main()
