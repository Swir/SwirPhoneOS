package org.swir.phoneos.phone;

public final class CallHistoryPolicy {
    public static final int MAX_RECENT_CALLS = 20;
    public static final int MAX_LABEL_LENGTH = 80;

    private CallHistoryPolicy() {}

    public static String displayLabel(boolean presentationAllowed, String cachedName, String number, String unknownLabel) {
        String fallback = clean(unknownLabel);
        if (fallback.isEmpty()) fallback = "Unknown";
        if (!presentationAllowed) return fallback;
        String name = clean(cachedName);
        if (!name.isEmpty()) return name;
        String normalizedNumber = clean(number);
        if (normalizedNumber.isEmpty() || normalizedNumber.charAt(0) == '-') return fallback;
        return normalizedNumber;
    }

    public static String typeKey(int type) {
        switch (type) {
            case 1: return "incoming";
            case 2: return "outgoing";
            case 3: return "missed";
            case 5: return "rejected";
            case 6: return "blocked";
            case 4: return "voicemail";
            default: return "other";
        }
    }

    public static long safeDurationSeconds(long seconds) {
        if (seconds < 0L) return 0L;
        return Math.min(seconds, 24L * 60L * 60L);
    }

    public static String formatDuration(long seconds) {
        long bounded = safeDurationSeconds(seconds);
        long minutes = bounded / 60L;
        long remainder = bounded % 60L;
        return minutes + ":" + (remainder < 10L ? "0" : "") + remainder;
    }

    private static String clean(String value) {
        if (value == null) return "";
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < value.length() && out.length() < MAX_LABEL_LENGTH; i++) {
            char ch = value.charAt(i);
            if (!Character.isISOControl(ch)) out.append(ch);
        }
        return out.toString().trim();
    }
}
