package org.swir.phoneos.gallery;

import java.util.Locale;

/** Pure-Java media filtering and album-label rules shared by Android and host tests. */
public final class MediaPolicy {
    private static final int MAX_QUERY_LENGTH = 120;
    private static final int MAX_ALBUM_NAME_LENGTH = 80;

    private MediaPolicy() {}

    public static boolean supportedMime(String mimeType) {
        if (mimeType == null) return false;
        String value = mimeType.trim().toLowerCase(Locale.ROOT);
        return value.startsWith("image/") || value.startsWith("video/");
    }

    public static boolean matches(String query, String displayName, String mimeType) {
        return matches(query, displayName, mimeType, "");
    }

    public static boolean matches(String query, String displayName, String mimeType, String albumName) {
        if (!supportedMime(mimeType)) return false;
        String needle = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        if (needle.length() > MAX_QUERY_LENGTH) return false;
        if (needle.isEmpty()) return true;
        String name = displayName == null ? "" : displayName.toLowerCase(Locale.ROOT);
        String mime = mimeType.toLowerCase(Locale.ROOT);
        String album = albumName == null ? "" : albumName.toLowerCase(Locale.ROOT);
        return name.contains(needle) || mime.contains(needle) || album.contains(needle);
    }

    public static String safeAlbumName(String value, String fallback) {
        String safeFallback = fallback == null ? "" : fallback.trim();
        if (safeFallback.isEmpty()) safeFallback = "Album";
        String raw = value == null ? "" : value;
        StringBuilder clean = new StringBuilder();
        for (int index = 0; index < raw.length() && clean.length() < MAX_ALBUM_NAME_LENGTH; index++) {
            char ch = raw.charAt(index);
            if (!Character.isISOControl(ch)) clean.append(ch);
        }
        String result = clean.toString().trim();
        return result.isEmpty() ? safeFallback : result;
    }

    public static boolean isVideo(String mimeType) {
        return supportedMime(mimeType) && mimeType.trim().toLowerCase(Locale.ROOT).startsWith("video/");
    }

    public static long safeEpochSeconds(long value) {
        return Math.max(0L, value);
    }
}
