from __future__ import annotations

from pathlib import Path
import unittest

from swirphoneos.platform import PlatformBaselineError, load_baseline, validate_baseline


PIN = {
    "manifest_commit": "5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f",
    "manifest_tree": "1541b7154f1532032baf7c73f222256cc29e8cfb",
    "tag_object": "7a9e46ba6ed424f922a3457f4964e67e0b966201",
    "repo_init_revision": "android-17.0.0_r1",
}


def candidate(*, pinned: bool = False) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": 2,
        "status": "PINNED_NOT_BUILT" if pinned else "CANDIDATE_NOT_PINNED",
        "checked_date": "2026-09-16",
        "platform": "Android 17",
        "api_level": 37,
        "manifest_url": "https://android.googlesource.com/platform/manifest",
        "tracking_manifest": "android-latest-release",
        "resolved_release_branch": "android17-release",
        "candidate_release_tag": "android-17.0.0_r1",
        "candidate_build_id": "CP2A.260605.016",
        "candidate_security_patch_level": "2026-06-05",
        "manifest_commit": None,
        "manifest_tree": None,
        "tag_object": None,
        "repo_init_revision": None,
        "download_started": False,
        "build_completed": False,
        "sources": [
            "https://source.android.com/docs/setup/reference/build-numbers",
            "https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1",
        ],
        "notes": "Discovery/pin metadata only.",
    }
    if pinned:
        data.update(PIN)
    return data


class PlatformBaselineTests(unittest.TestCase):
    def test_repository_candidate_is_pinned_but_not_complete(self) -> None:
        root = Path(__file__).resolve().parents[1]
        baseline = load_baseline(root / "platform" / "aosp_baseline.json")
        self.assertEqual(baseline.platform, "Android 17")
        self.assertEqual(baseline.api_level, 37)
        self.assertEqual(baseline.resolved_release_branch, "android17-release")
        self.assertEqual(baseline.status, "PINNED_NOT_BUILT")
        self.assertTrue(baseline.pinned)
        self.assertFalse(baseline.milestone_complete)
        self.assertFalse(baseline.download_started)
        self.assertEqual(baseline.manifest_commit, PIN["manifest_commit"])

    def test_unpinned_candidate_cannot_claim_download(self) -> None:
        data = candidate()
        data["download_started"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_unpinned_candidate_rejects_partial_pin(self) -> None:
        data = candidate()
        data["manifest_commit"] = PIN["manifest_commit"]
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_pinned_requires_complete_pin(self) -> None:
        data = candidate(pinned=True)
        data["manifest_tree"] = None
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_pinned_revision_must_match_release_tag(self) -> None:
        data = candidate(pinned=True)
        data["repo_init_revision"] = "android-17.0.0_r2"
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_bad_sha_is_rejected(self) -> None:
        data = candidate(pinned=True)
        data["tag_object"] = "ABC"
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_build_cannot_complete_before_download(self) -> None:
        data = candidate(pinned=True)
        data["status"] = "BUILT_VERIFIED"
        data["build_completed"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_pinned_not_built_cannot_claim_completed_build(self) -> None:
        data = candidate(pinned=True)
        data["download_started"] = True
        data["build_completed"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_built_verified_requires_completed_build(self) -> None:
        data = candidate(pinned=True)
        data["status"] = "BUILT_VERIFIED"
        data["download_started"] = True
        with self.assertRaises(PlatformBaselineError):
            validate_baseline(data)

    def test_built_verified_with_pin_and_build_is_complete(self) -> None:
        data = candidate(pinned=True)
        data["status"] = "BUILT_VERIFIED"
        data["download_started"] = True
        data["build_completed"] = True
        baseline = validate_baseline(data)
        self.assertTrue(baseline.milestone_complete)

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
