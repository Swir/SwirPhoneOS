package org.swir.phoneos.browser;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

public final class BrowserPolicy {
    private static final String SEARCH_ENDPOINT = "https://duckduckgo.com/?q=";

    private BrowserPolicy() {}

    public static String normalizeAddress(String raw) {
        if (raw == null) return "about:blank";
        String value = raw.trim();
        if (value.isEmpty()) return "about:blank";
        String lower = value.toLowerCase(Locale.ROOT);
        if (lower.equals("about:blank")) return "about:blank";
        if (lower.startsWith("https://") || lower.startsWith("http://")) return value;
        if (!value.contains(" ") && value.contains(".")) return "https://" + value;
        return SEARCH_ENDPOINT + URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    public static boolean isAllowedUri(String raw) {
        if (raw == null || raw.isBlank()) return false;
        if (raw.equalsIgnoreCase("about:blank")) return true;
        try {
            URI uri = URI.create(raw.trim());
            String scheme = uri.getScheme();
            if (scheme == null) return false;
            String normalized = scheme.toLowerCase(Locale.ROOT);
            return (normalized.equals("https") || normalized.equals("http")) && uri.getHost() != null;
        } catch (IllegalArgumentException ignored) {
            return false;
        }
    }

    public static boolean canShare(String raw) {
        if (!isAllowedUri(raw)) return false;
        return !raw.equalsIgnoreCase("about:blank");
    }
}
