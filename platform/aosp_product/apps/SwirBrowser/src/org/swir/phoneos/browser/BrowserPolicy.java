package org.swir.phoneos.browser;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

public final class BrowserPolicy {
    public static final int MAX_URL_LENGTH = 2048;
    public static final int MAX_QUERY_LENGTH = 512;

    private BrowserPolicy() {}

    public static String normalizeUrl(String raw) {
        if (raw == null) return "";
        String value = raw.trim();
        if (value.isEmpty() || value.length() > MAX_URL_LENGTH || containsControl(value)) return "";
        if (!value.contains("://")) value = "https://" + value;
        try {
            URI uri = new URI(value);
            if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null || uri.getHost().isEmpty()) return "";
            if (uri.getUserInfo() != null) return "";
            int port = uri.getPort();
            if (port < -1 || port > 65535) return "";
            return uri.toASCIIString();
        } catch (Exception error) {
            return "";
        }
    }

    public static String searchUrl(String query) {
        if (query == null) return "";
        String value = query.trim();
        if (value.isEmpty() || value.length() > MAX_QUERY_LENGTH || containsControl(value)) return "";
        return "https://duckduckgo.com/?q=" + URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    public static boolean isSafeUrl(String raw) {
        return !normalizeUrl(raw).isEmpty();
    }

    public static String displayHost(String raw) {
        String normalized = normalizeUrl(raw);
        if (normalized.isEmpty()) return "";
        try { return new URI(normalized).getHost(); }
        catch (Exception error) { return ""; }
    }

    private static boolean containsControl(String value) {
        for (int i = 0; i < value.length(); i++) if (Character.isISOControl(value.charAt(i))) return true;
        return false;
    }
}
