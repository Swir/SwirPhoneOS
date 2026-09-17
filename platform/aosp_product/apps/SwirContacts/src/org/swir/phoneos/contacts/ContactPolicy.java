package org.swir.phoneos.contacts;

import java.util.Locale;

/** Pure Java validation and vCard policy for owner-managed local contacts. */
public final class ContactPolicy {
    public static final int MAX_NAME = 160;
    public static final int MAX_PHONE = 64;
    public static final int MAX_EMAIL = 254;
    public static final int MAX_IMPORT_BYTES = 1_000_000;

    private ContactPolicy() {}

    public static String normalizeName(String raw) { return bounded(raw, MAX_NAME, false); }
    public static String normalizeEmail(String raw) { return bounded(raw, MAX_EMAIL, true); }

    public static String normalizePhone(String raw) {
        if (raw == null) return "";
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < raw.length() && out.length() < MAX_PHONE; i++) {
            char c = raw.charAt(i);
            if (Character.isDigit(c) || c == '*' || c == '#') out.append(c);
            else if (c == '+' && out.length() == 0) out.append(c);
        }
        return out.toString();
    }

    public static boolean validContact(String name, String phone, String email) {
        String cleanName = normalizeName(name);
        String cleanPhone = normalizePhone(phone);
        String cleanEmail = normalizeEmail(email);
        if (cleanName.isEmpty()) return false;
        if (cleanPhone.isEmpty() && cleanEmail.isEmpty()) return false;
        return cleanEmail.isEmpty() || validEmail(cleanEmail);
    }

    public static boolean validEmail(String email) {
        String value = normalizeEmail(email);
        int at = value.indexOf('@');
        return at > 0 && at == value.lastIndexOf('@') && at < value.length() - 3 && value.indexOf('.', at + 2) > at + 1;
    }

    public static boolean matches(String query, String name, String phone, String email) {
        String q = bounded(query, 128, false).toLowerCase(Locale.ROOT);
        if (q.isEmpty()) return true;
        return normalizeName(name).toLowerCase(Locale.ROOT).contains(q)
                || normalizePhone(phone).contains(q)
                || normalizeEmail(email).toLowerCase(Locale.ROOT).contains(q);
    }

    public static String toVCard(String name, String phone, String email) {
        String cleanName = normalizeName(name);
        String cleanPhone = normalizePhone(phone);
        String cleanEmail = normalizeEmail(email);
        if (!validContact(cleanName, cleanPhone, cleanEmail)) return "";
        StringBuilder out = new StringBuilder("BEGIN:VCARD\r\nVERSION:3.0\r\n");
        out.append("FN:").append(escapeVCard(cleanName)).append("\r\n");
        if (!cleanPhone.isEmpty()) out.append("TEL:").append(escapeVCard(cleanPhone)).append("\r\n");
        if (!cleanEmail.isEmpty()) out.append("EMAIL:").append(escapeVCard(cleanEmail)).append("\r\n");
        return out.append("END:VCARD\r\n").toString();
    }

    public static String escapeVCard(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
                .replace("\r", "").replace("\n", "\\n");
    }

    private static String bounded(String raw, int max, boolean trimAllWhitespace) {
        if (raw == null) return "";
        String value = raw.trim();
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < value.length() && out.length() < max; i++) {
            char c = value.charAt(i);
            if (Character.isISOControl(c)) continue;
            if (trimAllWhitespace && Character.isWhitespace(c)) continue;
            out.append(c);
        }
        return out.toString();
    }
}
