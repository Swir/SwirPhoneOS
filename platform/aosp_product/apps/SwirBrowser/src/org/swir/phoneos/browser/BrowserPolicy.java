package org.swir.phoneos.browser;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

public final class BrowserPolicy {
    public static final int MAX_URL_LENGTH = 2048;
    public static final int MAX_QUERY_LENGTH = 512;
    public static final int MAX_DOWNLOAD_FILENAME_LENGTH = 120;
    public static final int MAX_MIME_TYPE_LENGTH = 128;

    private BrowserPolicy() {}

    public static String normalizeUrl(String input) {
        if (input == null) return "";
        String value = input.trim();
        if (value.isEmpty() || value.length() > MAX_URL_LENGTH || hasControl(value)) return "";
        if (!value.contains("://") && looksLikeHost(value)) value = "https://" + value;
        try {
            URI uri = new URI(value);
            if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null || uri.getHost().isBlank()) return "";
            if (uri.getUserInfo() != null || uri.getPort() < -1 || uri.getPort() > 65535) return "";
            return uri.toASCIIString();
        } catch (URISyntaxException | IllegalArgumentException ex) {
            return "";
        }
    }

    public static String searchUrl(String query) {
        if (query == null) return "";
        String value = query.trim();
        if (value.isEmpty() || value.length() > MAX_QUERY_LENGTH || hasControl(value)) return "";
        return "https://duckduckgo.com/?q=" + URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    public static boolean isSafeUrl(String url) {
        return !normalizeUrl(url).isEmpty();
    }

    public static boolean isSafeDownloadUrl(String url) {
        if (url == null) return false;
        String value = url.trim();
        if (value.isEmpty() || hasControl(value)) return false;
        try {
            URI uri = new URI(value);
            return "https".equalsIgnoreCase(uri.getScheme()) && !normalizeUrl(value).isEmpty();
        } catch (URISyntaxException | IllegalArgumentException ex) {
            return false;
        }
    }

    public static String safeDownloadFileName(String candidate) {
        if (candidate == null) return "download.bin";
        String value = candidate.trim();
        if (value.isEmpty()) return "download.bin";
        StringBuilder out = new StringBuilder(Math.min(value.length(), MAX_DOWNLOAD_FILENAME_LENGTH));
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if (Character.isISOControl(ch) || ch == '/' || ch == '\\' || ch == ':' || ch == '*' || ch == '?' || ch == '"' || ch == '<' || ch == '>' || ch == '|') out.append('_');
            else out.append(ch);
        }
        value = out.toString().trim();
        while (value.startsWith(".")) value = value.substring(1).trim();
        while (value.endsWith(".") || value.endsWith(" ")) value = value.substring(0, value.length() - 1).trim();
        if (value.isEmpty()) return "download.bin";
        if (value.length() <= MAX_DOWNLOAD_FILENAME_LENGTH) return value;
        int dot = value.lastIndexOf('.');
        String extension = dot > 0 && value.length() - dot <= 16 ? value.substring(dot) : "";
        int baseLimit = MAX_DOWNLOAD_FILENAME_LENGTH - extension.length();
        String base = value.substring(0, Math.max(1, baseLimit)).trim();
        while (base.endsWith(".")) base = base.substring(0, base.length() - 1).trim();
        if (base.isEmpty()) base = "download";
        return base + extension;
    }

    public static String safeMimeType(String candidate) {
        if (candidate == null) return "";
        String value = candidate.trim().toLowerCase(Locale.ROOT);
        if (value.isEmpty() || value.length() > MAX_MIME_TYPE_LENGTH || hasControl(value)) return "";
        int slash = value.indexOf('/');
        if (slash <= 0 || slash != value.lastIndexOf('/') || slash == value.length() - 1) return "";
        return safeMimeToken(value.substring(0, slash)) && safeMimeToken(value.substring(slash + 1)) ? value : "";
    }

    public static String displayHost(String url) {
        String normalized = normalizeUrl(url);
        if (normalized.isEmpty()) return "";
        try {
            String host = new URI(normalized).getHost();
            return host == null ? "" : host;
        } catch (URISyntaxException ex) {
            return "";
        }
    }

    private static boolean safeMimeToken(String value) {
        if (value.isEmpty()) return false;
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if (!(Character.isLetterOrDigit(ch) || ch == '!' || ch == '#' || ch == '$' || ch == '&' || ch == '^' || ch == '_' || ch == '.' || ch == '+' || ch == '-')) return false;
        }
        return true;
    }

    private static boolean hasControl(String value) {
        for (int i = 0; i < value.length(); i++) if (Character.isISOControl(value.charAt(i))) return true;
        return false;
    }

    private static boolean looksLikeHost(String value) {
        return !value.contains(" ") && (value.contains(".") || "localhost".equalsIgnoreCase(value));
    }
}
