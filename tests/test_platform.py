from __future__ import annotations

from pathlib import Path
import unittest

from swirphoneos.platform import PlatformBaselineError, load_baseline, validate_baseline


def candidate() -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "CANDIDATE_NOT_PINNED",
        "checked_date": "2026-09-16",
        "platform": "Android 17",
        "api_level": 37,
        "manifest_url": "https://android.googlesource.com/platform/manifest",
        "tracking_manifest": "android-latest-release",
        "resolved_release_branch": "android17-release",
        "candidate_release_tag": "android-17.0.0_r1",
        "candidate_build_id": "CP2A.260605.016",
        "candidate_security_patch_level": "2026-06-05",
        "download_started": False,
        "build_completed": False,
        "sources": ["https://source.android.com/docs/setup/reference/build-numbers"],
        "notes": "Discovery only.",
    }


class PlatformBaselineTests(unittest.TestCase):
    def test_repository_candidate_is_valid_and_not_complete(self) -> None:
        root = Path(__file__).resolve().parents[1]
        baseline = load_baseline(root / "platform" / "aosp_baseline.json")
        self.assertEqual(baseline.platform, "Android 17")
        self.assertEqual(baseline.api_level, 37)
        self.assertEqual(baseline.resolved_release_branch, "android17-release")
        self.assertFalse(baseline.milestone_complete)
        self.assertFalse(baseline.download_started)

    def test_unpinned_candidate_cannot_claim_download(self) -> None:
        data = candidate()
        data["download_started"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_build_cannot_complete_before_download(self) -> None:
        data = candidate()
        data["status"] = "BUILT_VERIFIED"
        data["build_completed"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_pinned_not_built_cannot_claim_completed_build(self) -> None:
        data = candidate()
        data["status"] = "PINNED_NOT_BUILT"
        data["download_started"] = True
        data["build_completed"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_built_verified_requires_completed_build(self) -> None:
        data = candidate()
        data["status"] = "BUILT_VERIFIED"
        data["download_started"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_rejects_non_official_manifest_host(self) -> None:
        data = candidate()
        data["manifest_url"] = "https://example.invalid/platform/manifest"
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_rejects_bad_release_tag(self) -> None:
        data = candidate()
        data["candidate_release_tag"] = "latest"
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_rejects_non_official_source_docs(self) -> None:
        data = candidate()
        data["sources"] = ["https://example.invalid/aosp"]
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)


if __name__ == "__main__":
    unittest.main()
