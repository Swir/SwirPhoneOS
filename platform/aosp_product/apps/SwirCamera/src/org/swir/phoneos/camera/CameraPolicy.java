package org.swir.phoneos.camera;

import java.util.Locale;

public final class CameraPolicy {
    public static final int LENS_FRONT = 0;
    public static final int LENS_BACK = 1;
    public static final int LENS_EXTERNAL = 2;
    public static final int LENS_UNKNOWN = -1;
    public static final int VIDEO_FRAME_RATE = 30;
    private static final int MIN_VIDEO_BIT_RATE = 2_000_000;
    private static final int MAX_VIDEO_BIT_RATE = 20_000_000;

    private CameraPolicy() {}

    public static boolean validDimensions(int width, int height) {
        return width > 0 && height > 0 && width <= 32768 && height <= 32768;
    }

    public static boolean validVideoDimensions(int width, int height) {
        if (!validDimensions(width, height)) return false;
        if ((width & 1) != 0 || (height & 1) != 0) return false;
        long area = (long) width * (long) height;
        return area <= 3840L * 2160L;
    }

    public static int videoBitRate(int width, int height) {
        if (!validVideoDimensions(width, height)) return 0;
        long requested = (long) width * (long) height * 5L;
        if (requested < MIN_VIDEO_BIT_RATE) return MIN_VIDEO_BIT_RATE;
        if (requested > MAX_VIDEO_BIT_RATE) return MAX_VIDEO_BIT_RATE;
        return (int) requested;
    }

    public static double megapixels(int width, int height) {
        if (!validDimensions(width, height)) return 0.0;
        return ((double) width * (double) height) / 1_000_000.0;
    }

    public static String formatMegapixels(int width, int height) {
        return String.format(Locale.ROOT, "%.1f", megapixels(width, height));
    }

    public static int normalizeLensFacing(Integer facing) {
        if (facing == null) return LENS_UNKNOWN;
        int value = facing.intValue();
        if (value == LENS_FRONT || value == LENS_BACK || value == LENS_EXTERNAL) return value;
        return LENS_UNKNOWN;
    }

    public static int nextPreferredLens(int current) {
        return current == LENS_FRONT ? LENS_BACK : LENS_FRONT;
    }

    public static int jpegOrientation(int sensorOrientation, int displayRotationDegrees, boolean frontFacing) {
        int sensor = normalizeDegrees(sensorOrientation);
        int display = normalizeDegrees(displayRotationDegrees);
        int result = frontFacing ? sensor + display : sensor - display;
        return normalizeDegrees(result);
    }

    private static int normalizeDegrees(int value) {
        int normalized = value % 360;
        if (normalized < 0) normalized += 360;
        return normalized;
    }
}
