package org.swir.phoneos.apps;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

public final class AppCatalogPolicy {
    public static final int MAX_QUERY = 120;
    public static final int MAX_CATALOG_APPS = 512;
    public static final int MAX_LABEL = 120;
    public static final int MAX_VERSION = 96;

    public enum UpdateSource {
        SYSTEM_IMAGE,
        EXTERNAL_INSTALLER,
        LOCAL_UNKNOWN
    }

    public enum UpdateState {
        SYSTEM_BASELINE,
        SYSTEM_UPDATED,
        EXTERNAL_MANAGED,
        LOCAL_UNKNOWN
    }

    private AppCatalogPolicy() {}

    public static String normalizeQuery(String value) {
        if (value == null) return "";
        String trimmed = value.trim();
        if (trimmed.length() > MAX_QUERY) trimmed = trimmed.substring(0, MAX_QUERY);
        return trimmed.toLowerCase(Locale.ROOT);
    }

    public static boolean matches(String label, String packageName, String query) {
        String needle = normalizeQuery(query);
        if (needle.isEmpty()) return true;
        return normalizeLabel(label).toLowerCase(Locale.ROOT).contains(needle)
                || (packageName == null ? "" : packageName.toLowerCase(Locale.ROOT)).contains(needle);
    }

    public static boolean validPackageName(String value) {
        return value != null
                && value.matches("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+")
                && value.length() <= 255;
    }

    public static boolean catalogCapacityAvailable(int uniqueCount) {
        return uniqueCount >= 0 && uniqueCount < MAX_CATALOG_APPS;
    }

    public static String normalizeLabel(String value) {
        return boundedDisplayText(value, MAX_LABEL);
    }

    public static String normalizeVersion(String versionName, long versionCode) {
        String normalized = boundedDisplayText(versionName, MAX_VERSION);
        if (!normalized.isEmpty()) return normalized;
        return Long.toString(Math.max(0L, versionCode));
    }

    private static String boundedDisplayText(String value, int maxLength) {
        if (value == null || maxLength <= 0) return "";
        StringBuilder out = new StringBuilder(Math.min(value.length(), maxLength));
        boolean pendingSpace = false;
        for (int offset = 0; offset < value.length();) {
            int codePoint = value.codePointAt(offset);
            offset += Character.charCount(codePoint);
            if (Character.isISOControl(codePoint) || Character.isWhitespace(codePoint)) {
                if (out.length() > 0) pendingSpace = true;
                continue;
            }
            int width = Character.charCount(codePoint);
            int extra = pendingSpace && out.length() > 0 ? 1 : 0;
            if (out.length() + extra + width > maxLength) break;
            if (extra == 1) out.append(' ');
            out.appendCodePoint(codePoint);
            pendingSpace = false;
        }
        return out.toString();
    }

    public static String sha256(byte[] value) {
        if (value == null || value.length == 0) return "";
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value);
            StringBuilder out = new StringBuilder(64);
            for (byte b : digest) out.append(String.format(Locale.ROOT, "%02X", b & 0xff));
            return out.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    public static String shortDigest(String digest) {
        if (digest == null || !digest.matches("[0-9A-Fa-f]{64}")) return "";
        return digest.substring(0, 16).toUpperCase(Locale.ROOT);
    }

    public static UpdateSource updateSource(boolean systemImage, String installerPackage) {
        if (systemImage) return UpdateSource.SYSTEM_IMAGE;
        if (validPackageName(installerPackage)) return UpdateSource.EXTERNAL_INSTALLER;
        return UpdateSource.LOCAL_UNKNOWN;
    }

    public static UpdateState updateState(boolean systemImage, boolean updatedSystemApp, String installerPackage) {
        if (updatedSystemApp) return UpdateState.SYSTEM_UPDATED;
        if (systemImage) return UpdateState.SYSTEM_BASELINE;
        if (validPackageName(installerPackage)) return UpdateState.EXTERNAL_MANAGED;
        return UpdateState.LOCAL_UNKNOWN;
    }

    public static long normalizeUpdateTime(long epochMillis) {
        return epochMillis > 0L ? epochMillis : 0L;
    }
}
