package org.swir.phoneos.files;

import java.util.Locale;

/** Pure-Java file-name and search policy shared by the Android UI and host tests. */
public final class FilePolicy {
    private static final int MAX_NAME_CHARS = 120;

    private FilePolicy() {}

    public static boolean validName(String value) {
        if (value == null) return false;
        String name = value.trim();
        if (name.isEmpty() || name.length() > MAX_NAME_CHARS || ".".equals(name) || "..".equals(name)) return false;
        for (int i = 0; i < name.length(); i++) {
            char c = name.charAt(i);
            if (c == '/' || c == '\\' || c == '\u0000' || Character.isISOControl(c)) return false;
        }
        return true;
    }

    public static boolean matches(String displayName, String query) {
        if (query == null || query.trim().isEmpty()) return true;
        if (displayName == null) return false;
        return displayName.toLowerCase(Locale.ROOT).contains(query.trim().toLowerCase(Locale.ROOT));
    }
}
