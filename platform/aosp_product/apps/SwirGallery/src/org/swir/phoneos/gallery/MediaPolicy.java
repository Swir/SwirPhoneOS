package org.swir.phoneos.gallery;

import java.util.Locale;

/** Pure-Java media filtering rules shared by the Android activity and host tests. */
public final class MediaPolicy {
    private static final int MAX_QUERY_LENGTH = 120;

    private MediaPolicy() {}

    public static boolean supportedMime(String mimeType) {
        if (mimeType == null) return false;
        String value = mimeType.trim().toLowerCase(Locale.ROOT);
        return value.startsWith("image/") || value.startsWith("video/");
    }

    public static boolean matches(String query, String displayName, String mimeType) {
        if (!supportedMime(mimeType)) return false;
        String needle = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        if (needle.length() > MAX_QUERY_LENGTH) return false;
        if (needle.isEmpty()) return true;
        String name = displayName == null ? "" : displayName.toLowerCase(Locale.ROOT);
        String mime = mimeType.toLowerCase(Locale.ROOT);
        return name.contains(needle) || mime.contains(needle);
    }

    public static boolean isVideo(String mimeType) {
        return supportedMime(mimeType) && mimeType.trim().toLowerCase(Locale.ROOT).startsWith("video/");
    }

    public static long safeEpochSeconds(long value) {
        return Math.max(0L, value);
    }
}
