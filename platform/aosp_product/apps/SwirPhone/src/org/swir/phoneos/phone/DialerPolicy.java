package org.swir.phoneos.phone;

public final class DialerPolicy {
    public static final int MAX_DIAL_LENGTH = 64;

    private DialerPolicy() {}

    public static String normalize(String raw) {
        if (raw == null) return "";
        String value = raw.trim();
        if (value.isEmpty() || value.length() > MAX_DIAL_LENGTH) return "";
        StringBuilder out = new StringBuilder(value.length());
        boolean plusSeen = false;
        int digits = 0;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (Character.isDigit(c)) {
                out.append(c);
                digits++;
            } else if (c == '+' && out.length() == 0 && !plusSeen) {
                out.append(c);
                plusSeen = true;
            } else if (c == '*' || c == '#') {
                out.append(c);
            } else if (c == ' ' || c == '-' || c == '(' || c == ')') {
                // Formatting characters are intentionally discarded.
            } else {
                return "";
            }
        }
        return digits == 0 ? "" : out.toString();
    }

    public static boolean isDialable(String raw) {
        return !normalize(raw).isEmpty();
    }

    public static String appendKey(String current, char key) {
        if (!(Character.isDigit(key) || key == '*' || key == '#')) return current == null ? "" : current;
        String base = current == null ? "" : current;
        if (base.length() >= MAX_DIAL_LENGTH) return base;
        return base + key;
    }

    public static String eraseLast(String current) {
        if (current == null || current.isEmpty()) return "";
        return current.substring(0, current.length() - 1);
    }
}
