package org.swir.phoneos.camera;

import java.util.Locale;

public final class CameraPolicy {
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

    public static String lensLabel(int facing) {
        if (facing == 0) return "FRONT";
        if (facing == 1) return "BACK";
        if (facing == 2) return "EXTERNAL";
        return "UNKNOWN";
    }
}
