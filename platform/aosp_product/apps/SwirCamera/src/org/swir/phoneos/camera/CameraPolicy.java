package org.swir.phoneos.camera;

import java.util.Locale;

public final class CameraPolicy {
    public static final int LENS_FRONT = 0;
    public static final int LENS_BACK = 1;
    public static final int LENS_EXTERNAL = 2;
    public static final int LENS_UNKNOWN = -1;

    private CameraPolicy() {}

    public static boolean validDimensions(int width, int height) {
        return width > 0 && height > 0 && width <= 32768 && height <= 32768;
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
