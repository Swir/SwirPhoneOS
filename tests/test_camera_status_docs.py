import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CameraStatusDocumentationTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_active_status_docs_describe_direct_video_without_runtime_overclaim(self) -> None:
        for relative in (
            "README.md",
            "ROADMAP.md",
            "BUILD_STATUS.md",
            "docs/SYSTEM_APPS.md",
            "docs/SWIR_CAMERA.md",
        ):
            with self.subTest(relative=relative):
                text = self.read(relative)
                self.assertIn("H.264", text)
                self.assertIn("MediaCodec", text)
                self.assertNotIn("video remains an explicit Android hand-off", text)

    def test_camera_video_capability_stays_open_until_runtime_review(self) -> None:
        roadmap = self.read("ROADMAP.md")
        system_apps = self.read("docs/SYSTEM_APPS.md")
        camera_contract = self.read("docs/SWIR_CAMERA.md")

        self.assertIn("`video_capture` deliberately stays open", roadmap)
        self.assertIn("`camera:video_capture` remains intentionally open", system_apps)
        self.assertIn("`camera:video_capture` remains open", camera_contract)
        self.assertNotIn("`camera:photo_capture`", system_apps)

    def test_camera_permission_and_audio_boundary_remain_explicit(self) -> None:
        readme = self.read("README.md")
        system_apps = self.read("docs/SYSTEM_APPS.md")
        camera_contract = self.read("docs/SWIR_CAMERA.md")

        self.assertIn("exactly `CAMERA`", readme)
        self.assertIn("Requests exactly `CAMERA`", system_apps)
        self.assertIn("android.permission.CAMERA", camera_contract)
        self.assertIn("does not request `RECORD_AUDIO`", system_apps)
        self.assertIn("does not request microphone", camera_contract)


if __name__ == "__main__":
    unittest.main()
