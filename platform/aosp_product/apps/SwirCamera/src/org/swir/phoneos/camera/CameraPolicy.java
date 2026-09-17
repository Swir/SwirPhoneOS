package org.swir.phoneos.camera;

public final class CameraPolicy {
    public static final int MAX_MEDIA_NAME_LENGTH = 96;
    public static final long MIN_VIDEO_DURATION_MS = 500L;

    private CameraPolicy() {}

    public static int normalizeRotation(int degrees) {
        int normalized = ((degrees % 360) + 360) % 360;
        if (normalized < 45 || normalized >= 315) return 0;
        if (normalized < 135) return 90;
        if (normalized < 225) return 180;
        return 270;
    }

    public static int pickBestSizeIndex(int[][] sizes, int targetWidth, int targetHeight) {
        if (sizes == null || sizes.length == 0 || targetWidth <= 0 || targetHeight <= 0) return -1;
        int best = -1;
        long bestScore = Long.MAX_VALUE;
        double targetRatio = (double) targetWidth / (double) targetHeight;
        for (int i = 0; i < sizes.length; i++) {
            int[] item = sizes[i];
            if (item == null || item.length != 2 || item[0] <= 0 || item[1] <= 0) continue;
            double ratio = (double) item[0] / (double) item[1];
            long area = (long) item[0] * (long) item[1];
            long targetArea = (long) targetWidth * (long) targetHeight;
            long areaDelta = Math.abs(area - targetArea);
            long ratioPenalty = (long) (Math.abs(ratio - targetRatio) * 1_000_000_000L);
            long score = ratioPenalty + Math.min(areaDelta, 999_999_999L);
            if (score < bestScore) {
                bestScore = score;
                best = i;
            }
        }
        return best;
    }

    public static String safeMediaName(String prefix, long epochMillis, String extension) {
        String safePrefix = sanitizeToken(prefix, "SWIR");
        String safeExtension = sanitizeToken(extension, "bin").toLowerCase(java.util.Locale.ROOT);
        String candidate = safePrefix + "_" + Math.max(0L, epochMillis) + "." + safeExtension;
        if (candidate.length() <= MAX_MEDIA_NAME_LENGTH) return candidate;
        int keep = Math.max(1, MAX_MEDIA_NAME_LENGTH - safeExtension.length() - 2);
        return safePrefix.substring(0, Math.min(keep, safePrefix.length())) + "." + safeExtension;
    }

    private static String sanitizeToken(String value, String fallback) {
        if (value == null) return fallback;
        String trimmed = value.trim();
        if (trimmed.isEmpty()) return fallback;
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < trimmed.length(); i++) {
            char c = trimmed.charAt(i);
            if (Character.isLetterOrDigit(c) || c == '-' || c == '_') out.append(c);
        }
        return out.length() == 0 ? fallback : out.toString();
    }

    public static boolean canCapture(boolean permissionGranted, boolean cameraOpen, boolean sessionReady, boolean storageReady) {
        return permissionGranted && cameraOpen && sessionReady && storageReady;
    }

    public static boolean canStopVideo(boolean recording, long elapsedMs) {
        return recording && elapsedMs >= MIN_VIDEO_DURATION_MS;
    }
}
