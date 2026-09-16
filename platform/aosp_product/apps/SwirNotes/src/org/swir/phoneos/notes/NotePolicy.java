package org.swir.phoneos.notes;

import java.util.Locale;

public final class NotePolicy {
    public static final int MAX_TITLE = 120;
    public static final int MAX_BODY = 100_000;

    private NotePolicy() {}

    public static String normalizedTitle(String title) {
        return title == null ? "" : title.trim();
    }

    public static boolean validTitle(String title) {
        if (title == null || title.length() > MAX_TITLE) return false;
        for (int i = 0; i < title.length(); i++) {
            char ch = title.charAt(i);
            if (Character.isISOControl(ch) && ch != '\t') return false;
        }
        return true;
    }

    public static boolean validBody(String body) {
        return body != null && body.length() <= MAX_BODY;
    }

    public static boolean validNote(String title, String body) {
        return validTitle(title) && validBody(body)
                && !(normalizedTitle(title).isEmpty() && body.trim().isEmpty());
    }

    public static boolean matches(String query, String title, String body) {
        String q = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        if (q.isEmpty()) return true;
        String t = title == null ? "" : title.toLowerCase(Locale.ROOT);
        String b = body == null ? "" : body.toLowerCase(Locale.ROOT);
        return t.contains(q) || b.contains(q);
    }

    public static String safeExportBase(String title) {
        String value = normalizedTitle(title).replaceAll("[\\\\/:*?\"<>|]", "_");
        value = value.replaceAll("\\s+", " ").trim();
        if (value.length() > 64) value = value.substring(0, 64).trim();
        return value;
    }

    public static String exportMarkdown(String title, String body) {
        StringBuilder out = new StringBuilder();
        String cleanTitle = normalizedTitle(title);
        if (!cleanTitle.isEmpty()) out.append("# ").append(cleanTitle).append("\n\n");
        if (body != null) out.append(body);
        if (out.length() > 0 && out.charAt(out.length() - 1) != '\n') out.append('\n');
        return out.toString();
    }
}
