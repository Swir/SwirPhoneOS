package org.swir.phoneos.camera;

public final class CameraPolicyHostTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check(CameraPolicy.normalizeRotation(-10) == 0, "negative rotation");
        check(CameraPolicy.normalizeRotation(91) == 90, "quarter rotation");
        check(CameraPolicy.normalizeRotation(181) == 180, "half rotation");
        check(CameraPolicy.normalizeRotation(270) == 270, "three-quarter rotation");
        int[][] sizes = {{640, 480}, {1280, 720}, {1920, 1080}};
        check(CameraPolicy.pickBestSizeIndex(sizes, 1366, 768) == 1, "best preview size");
        check(CameraPolicy.pickBestSizeIndex(null, 1, 1) == -1, "missing sizes");
        String name = CameraPolicy.safeMediaName("SWIR PHOTO", 1234L, "JPG");
        check("SWIRPHOTO_1234.jpg".equals(name), "safe media name");
        check(CameraPolicy.safeMediaName("..", 0L, "").endsWith(".bin"), "fallback extension");
        check(CameraPolicy.canCapture(true, true, true, true), "capture gate");
        check(!CameraPolicy.canCapture(true, true, false, true), "session gate");
        check(!CameraPolicy.canStopVideo(true, 100L), "minimum video duration");
        check(CameraPolicy.canStopVideo(true, 1000L), "video stop gate");
    }
}
