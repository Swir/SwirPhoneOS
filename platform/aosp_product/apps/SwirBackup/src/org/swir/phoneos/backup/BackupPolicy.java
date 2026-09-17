package org.swir.phoneos.backup;

import java.util.Locale;

public final class BackupPolicy {
    public static final int MAX_FILES = 64;
    public static final long MAX_ENTRY_BYTES = 134_217_728L;
    public static final long MAX_TOTAL_BYTES = 536_870_912L;

    private BackupPolicy() {}

    public static boolean validEntryName(String name) {
        if (name == null || name.isEmpty() || name.length() > 180 || name.startsWith("/") || name.startsWith("\\")) return false;
        if (name.contains("\\") || name.contains("../") || name.equals("..") || name.contains("/../")) return false;
        for (int i = 0; i < name.length(); i++) if (Character.isISOControl(name.charAt(i))) return false;
        return true;
    }

    public static String safeDisplayName(String raw) {
        String value = raw == null ? "" : raw.trim();
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < value.length() && out.length() < 96; i++) {
            char c = value.charAt(i);
            if (!Character.isISOControl(c) && c != '/' && c != '\\' && c != ':') out.append(c);
        }
        return out.length() == 0 ? "document" : out.toString();
    }

    public static String safeEntryName(String displayName, int index) {
        if (index < 0 || index >= MAX_FILES) return "";
        return String.format(Locale.ROOT, "files/%02d-%s", index + 1, safeDisplayName(displayName));
    }

    public static boolean sizeAllowed(long entryBytes, long totalBytes) {
        return entryBytes >= 0 && entryBytes <= MAX_ENTRY_BYTES && totalBytes >= 0 && totalBytes <= MAX_TOTAL_BYTES;
    }

    public static String backupFileName(long epochMillis) {
        return String.format(Locale.ROOT, "swir-backup-%d.swirbackup", Math.max(0L, epochMillis));
    }
}
