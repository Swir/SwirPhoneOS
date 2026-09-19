from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


CAMERA_ROOT = Path("platform/aosp_product/apps/SwirCamera")
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
LOCALES = ("values", "values-pl", "values-nb", "values-de", "values-es", "values-fr", "values-pt", "values-ar")


class SwirCameraDirectVideoSourceTests(unittest.TestCase):
    def test_camera_keeps_exact_camera_only_permission_boundary(self):
        root = ET.parse(CAMERA_ROOT / "AndroidManifest.xml").getroot()
        permissions = [node.get(ANDROID_NS + "name") for node in root.findall("uses-permission")]
        self.assertEqual(permissions, ["android.permission.CAMERA"])
        self.assertNotIn("android.permission.RECORD_AUDIO", permissions)

    def test_direct_video_is_scoped_h264_without_hidden_audio_capture(self):
        source = (CAMERA_ROOT / "src/org/swir/phoneos/camera/MainActivity.java").read_text(encoding="utf-8")
        for token in (
            "MediaCodec.createEncoderByType",
            "MediaFormat.MIMETYPE_VIDEO_AVC",
            "MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4",
            "CameraDevice.TEMPLATE_RECORD",
            "CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_VIDEO",
            "MediaStore.Video.Media.EXTERNAL_CONTENT_URI",
            "MediaStore.Video.Media.IS_PENDING",
            "Environment.DIRECTORY_MOVIES",
            "signalEndOfInputStream",
            "CameraPolicy.videoBitRate",
            "setOrientationHint",
        ):
            self.assertIn(token, source)
        self.assertNotIn("MediaRecorder", source)
        self.assertNotIn("Manifest.permission.RECORD_AUDIO", source)

    def test_video_state_machine_blocks_double_start_and_unbounded_finalize(self):
        source = (CAMERA_ROOT / "src/org/swir/phoneos/camera/MainActivity.java").read_text(encoding="utf-8")
        for token in (
            "VIDEO_FINALIZE_TIMEOUT_NS",
            "private volatile boolean videoTransition",
            "pendingVideoUri != null",
            "videoDrainThread != null",
            "System.nanoTime()",
            "videoTransition = true",
            "if (recordingVideo || videoTransition)",
            "if (videoTransition) return",
        ):
            self.assertIn(token, source)

    def test_unsupported_direct_video_keeps_visible_android_fallback(self):
        source = (CAMERA_ROOT / "src/org/swir/phoneos/camera/MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("MediaStore.ACTION_VIDEO_CAPTURE", source)
        self.assertIn("resolveActivity(getPackageManager())", source)
        self.assertIn("startActivity(intent)", source)

    def test_video_policy_is_bounded_and_host_tested(self):
        policy = (CAMERA_ROOT / "src/org/swir/phoneos/camera/CameraPolicy.java").read_text(encoding="utf-8")
        host = (CAMERA_ROOT / "hosttest/CameraPolicyHostTest.java").read_text(encoding="utf-8")
        for token in ("validVideoDimensions", "videoBitRate", "VIDEO_FRAME_RATE", "3840L * 2160L", "MAX_VIDEO_BIT_RATE"):
            self.assertIn(token, policy)
        for token in (
            "1080p video allowed",
            "4k video allowed",
            "oversized video rejected",
            "odd-width video rejected",
            "odd-height video rejected",
            "1080p bounded bitrate",
        ):
            self.assertIn(token, host)

    def test_all_camera_locales_share_direct_video_keys(self):
        expected = None
        required = {
            "record_video", "stop_video", "recording_video_silent", "finalizing_video",
            "video_saved_silent", "video_save_failed", "video_fallback_available",
            "video_fallback_unavailable", "video_size_row",
        }
        for directory in LOCALES:
            root = ET.parse(CAMERA_ROOT / "res" / directory / "strings.xml").getroot()
            keys = {node.get("name") for node in root.findall("string")}
            self.assertTrue(required.issubset(keys), directory)
            if expected is None:
                expected = keys
            else:
                self.assertEqual(expected, keys, directory)


if __name__ == "__main__":
    unittest.main()
