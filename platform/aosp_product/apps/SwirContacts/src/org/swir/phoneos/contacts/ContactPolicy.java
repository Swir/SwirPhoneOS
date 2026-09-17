package org.swir.phoneos.contacts;

import java.util.Locale;

public final class ContactPolicy {
    public static final int MAX_QUERY = 120;
    public static final int MAX_EXPORT_BASE = 80;
    private ContactPolicy() {}

    public static String normalizeQuery(String value) {
        if (value == null) return "";
        String trimmed = value.trim();
        if (trimmed.length() > MAX_QUERY) trimmed = trimmed.substring(0, MAX_QUERY);
        return trimmed.toLowerCase(Locale.ROOT);
    }

    public static boolean matches(String name, String phone, String query) {
        String needle = normalizeQuery(query);
        if (needle.isEmpty()) return true;
        String n = name == null ? "" : name.toLowerCase(Locale.ROOT);
        String p = phone == null ? "" : phone.toLowerCase(Locale.ROOT);
        return n.contains(needle) || p.contains(needle);
    }

    public static boolean validLookupKey(String value) {
        if (value == null || value.isBlank() || value.length() > 512) return false;
        for (int i = 0; i < value.length(); i++) if (Character.isISOControl(value.charAt(i))) return false;
        return true;
    }

    public static String safeExportBase(String name) {
        String value = name == null ? "" : name.trim();
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < value.length() && out.length() < MAX_EXPORT_BASE; i++) {
            char c = value.charAt(i);
            if (Character.isLetterOrDigit(c) || c == '-' || c == '_' || c == ' ') out.append(c);
        }
        String result = out.toString().trim().replace(' ', '_');
        return result.isEmpty() ? "contact" : result;
    }

    public static String vcardFileName(String name) {
        return safeExportBase(name) + ".vcf";
    }
}
