package org.swir.phoneos.gallery;

public final class MediaPolicyHostTest {
    public static void main(String[] args) {
        require(MediaPolicy.supportedMime("image/jpeg"), "JPEG must be supported");
        require(MediaPolicy.supportedMime("video/mp4"), "MP4 must be supported");
        require(!MediaPolicy.supportedMime("audio/mpeg"), "Audio must stay outside Gallery scope");
        require(MediaPolicy.matches("sun", "Sunset.JPG", "image/jpeg"), "Name search must be case-insensitive");
        require(MediaPolicy.matches("video", "clip.mp4", "video/mp4"), "MIME search must work");
        require(!MediaPolicy.matches("x".repeat(121), "x.jpg", "image/jpeg"), "Oversized query must fail closed");
        require(MediaPolicy.isVideo("video/webm"), "Video classification must work");
        require(!MediaPolicy.isVideo("image/png"), "Images must not be classified as video");
        require(MediaPolicy.safeEpochSeconds(-5L) == 0L, "Negative media time must clamp");
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
