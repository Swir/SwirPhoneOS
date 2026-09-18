from __future__ import annotations

from pathlib import Path
import unittest


class AospSourceWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = Path(".github/workflows/aosp-build-evidence.yml").read_text(encoding="utf-8")

    def test_clean_source_is_verified_after_manifest_and_before_staging(self) -> None:
        manifest = self.text.index("python -m swirphoneos aosp-manifest")
        source_pre = self.text.index("python -m swirphoneos.aosp_source_evidence", manifest)
        stage = self.text.index("python -m swirphoneos stage-product")
        self.assertLess(manifest, source_pre)
        self.assertLess(source_pre, stage)
        self.assertIn("source-prebuild-evidence.json", self.text)

    def test_clean_source_is_reverified_after_build_before_run_binding(self) -> None:
        build = self.text.index('m -j"$SWIR_REQUESTED_JOBS"')
        source_post = self.text.index("python -m swirphoneos.aosp_source_evidence", build)
        run_bind = self.text.index("python -m swirphoneos aosp-run-evidence")
        self.assertLess(build, source_post)
        self.assertLess(source_post, run_bind)
        self.assertIn("source-postbuild-evidence.json", self.text)

    def test_source_trust_bundle_binds_the_completed_run_before_runtime_trust(self) -> None:
        run_bind = self.text.index("python -m swirphoneos aosp-run-evidence")
        source_trust = self.text.index("python -m swirphoneos.aosp_source_trust_bundle")
        runtime_trust = self.text.index("python -m swirphoneos.runtime_trust_bundle")
        self.assertLess(run_bind, source_trust)
        self.assertLess(source_trust, runtime_trust)
        block = self.text[source_trust:runtime_trust]
        self.assertIn('--resolved-manifest-evidence "$GITHUB_WORKSPACE/resolved-manifest.json"', block)
        self.assertIn('--source-pre "$GITHUB_WORKSPACE/source-prebuild-evidence.json"', block)
        self.assertIn('--source-post "$GITHUB_WORKSPACE/source-postbuild-evidence.json"', block)
        self.assertIn("source-trust-bundle.json", block)

    def test_source_evidence_survives_success_and_failure_artifact_upload(self) -> None:
        upload = self.text[self.text.index("Upload immutable evidence files"):]
        for name in (
            "source-prebuild-evidence.json",
            "source-postbuild-evidence.json",
            "source-trust-bundle.json",
        ):
            self.assertIn(name, upload)
        self.assertIn("if: ${{ always() }}", self.text)


if __name__ == "__main__":
    unittest.main()
