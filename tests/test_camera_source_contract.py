from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path("platform/aosp_product/apps/SwirCamera")
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class SwirCameraSourceContractTests(unittest.TestCase):
    def test_camera_hardware_feature_is_optional_for_portable_product_builds(self):
        manifest = ET.fromstring((ROOT / "AndroidManifest.xml").read_text(encoding="utf-8"))
        features = manifest.findall("uses-feature")
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].get(ANDROID_NS + "name"), "android.hardware.camera.any")
        self.assertEqual(features[0].get(ANDROID_NS + "required"), "false")

    def test_manifest_requests_exactly_camera_permission(self):
        manifest = ET.fromstring((ROOT / "AndroidManifest.xml").read_text(encoding="utf-8"))
        permissions = [node.get(ANDROID_NS + "name") for node in manifest.findall("uses-permission")]
        self.assertEqual(permissions, ["android.permission.CAMERA"])

    def test_video_path_is_deliberately_silent_and_scoped(self):
        activity = (ROOT / "src/org/swir/phoneos/camera/MainActivity.java").read_text(encoding="utf-8")
        self.assertNotIn("MediaRecorder.AudioSource", activity)
        self.assertNotIn("setAudioSource", activity)
        self.assertNotIn("Manifest.permission.RECORD_AUDIO", activity)
        self.assertIn("MediaStore.Video.Media.RELATIVE_PATH", activity)
        self.assertIn('"Movies/SwirPhoneOS"', activity)
        self.assertIn("MediaStore.Video.Media.IS_PENDING", activity)

    def test_photo_path_uses_scoped_pending_mediastore_item(self):
        activity = (ROOT / "src/org/swir/phoneos/camera/MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("MediaStore.Images.Media.RELATIVE_PATH", activity)
        self.assertIn('"Pictures/SwirPhoneOS"', activity)
        self.assertIn("MediaStore.Images.Media.IS_PENDING", activity)
        self.assertIn("openOutputStream", activity)

    def test_capture_is_first_party_camera2_not_delegated_intent(self):
        activity = (ROOT / "src/org/swir/phoneos/camera/MainActivity.java").read_text(encoding="utf-8")
        for token in ("CameraManager", "CameraDevice.TEMPLATE_PREVIEW", "CameraDevice.TEMPLATE_STILL_CAPTURE", "CameraDevice.TEMPLATE_RECORD", "CameraCaptureSession", "ImageReader", "MediaRecorder"):
            self.assertIn(token, activity)
        self.assertNotIn("MediaStore.ACTION_IMAGE_CAPTURE", activity)
        self.assertNotIn("MediaStore.ACTION_VIDEO_CAPTURE", activity)


if __name__ == "__main__":
    unittest.main()
