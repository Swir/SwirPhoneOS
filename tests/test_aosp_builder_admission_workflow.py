from __future__ import annotations

from pathlib import Path
import unittest


WORKFLOW = Path(".github/workflows/aosp-builder-admission.yml")
DOC = Path("docs/AOSP_BUILDER_ADMISSION.md")


class AospBuilderAdmissionWorkflowTests(unittest.TestCase):
    def test_admission_is_manual_bounded_and_read_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "workflow_dispatch:",
            "runs-on: [self-hosted, linux, x64, swir-aosp-builder]",
            "timeout-minutes: 10",
            "permissions:\n  contents: read",
            "python -m swirphoneos build-preflight",
            "python -m swirphoneos.aosp_host_evidence",
            "--phase PRE_BUILD",
            "aosp-host-admission.json",
            'report.get("operation") != "READ_ONLY_HOST_PREFLIGHT"',
            'workspace.get("cleanup_performed") is not False',
            'report.get("ready_for_full_build") is not True',
            'report.get("cuttlefish_kvm_available") is not True',
            "if: always()",
            "SwirPhoneOS-aosp-builder-admission",
            "retention-days: 14",
        )
        for token in required:
            self.assertIn(token, text)

        self.assertEqual(text.count("python -m swirphoneos.aosp_host_evidence"), 1)
        self.assertLess(
            text.index("python -m swirphoneos build-preflight"),
            text.index("python -m swirphoneos.aosp_host_evidence"),
        )
        self.assertLess(
            text.index("python -m swirphoneos.aosp_host_evidence"),
            text.index("- name: Upload bounded builder admission report and attestation"),
        )

        forbidden = (
            "repo init",
            "repo sync",
            "stage-product --workspace",
            " m -j",
            "launch_cvd",
            "cvd start",
            "adb ",
            "fastboot",
            "RecoverySystem",
            "UpdateEngine",
            "sudo ",
            "apt ",
            "dnf ",
            "yum ",
            "pacman ",
            "rm -rf",
        )
        for token in forbidden:
            self.assertNotIn(token, text)

    def test_admission_shares_the_full_builder_lock(self):
        admission = WORKFLOW.read_text(encoding="utf-8")
        full = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")
        self.assertIn("group: swir-aosp-builder", admission)
        self.assertIn("group: swir-aosp-builder", full)
        self.assertIn("cancel-in-progress: false", admission)

    def test_documentation_keeps_evidence_boundary_explicit(self):
        text = DOC.read_text(encoding="utf-8")
        for token in (
            "not build evidence",
            "not boot evidence",
            "does not sync Android source",
            "does not write to a phone",
            "exact host/toolchain identity snapshot",
            "SWIR_AOSP_WORKSPACE",
            "swir-aosp-builder",
            "AOSP build evidence",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
