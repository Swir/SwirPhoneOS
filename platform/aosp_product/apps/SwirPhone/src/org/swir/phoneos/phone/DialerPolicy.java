package org.swir.phoneos.phone;

public final class DialerPolicy {
    public static final int MAX_DIAL_LENGTH = 64;

    private DialerPolicy() {}

    public static String normalize(String raw) {
        if (raw == null) return "";
        String value = raw.trim();
        if (value.isEmpty() || value.codePointCount(0, value.length()) > MAX_DIAL_LENGTH) return "";
        StringBuilder out = new StringBuilder(value.length());
        boolean plusSeen = false;
        int digits = 0;
        for (int offset = 0; offset < value.length();) {
            int codePoint = value.codePointAt(offset);
            offset += Character.charCount(codePoint);
            if (Character.isDigit(codePoint)) {
                int digit = Character.digit(codePoint, 10);
                if (digit < 0) return "";
                out.append((char) ('0' + digit));
                digits++;
            } else if (codePoint == '+' && out.length() == 0 && !plusSeen) {
                out.append('+');
                plusSeen = true;
            } else if (codePoint == '*' || codePoint == '#') {
                out.appendCodePoint(codePoint);
            } else if (Character.isWhitespace(codePoint)
                    || Character.isSpaceChar(codePoint)
                    || codePoint == '-'
                    || codePoint == '('
                    || codePoint == ')') {
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
        int digit = Character.digit(key, 10);
        if (!(Character.isDigit(key) || key == '*' || key == '#')) return current == null ? "" : current;
        String base = current == null ? "" : current;
        if (base.codePointCount(0, base.length()) >= MAX_DIAL_LENGTH) return base;
        return Character.isDigit(key) && digit >= 0 ? base + (char) ('0' + digit) : base + key;
    }

    public static String eraseLast(String current) {
        if (current == null || current.isEmpty()) return "";
        int lastStart = current.offsetByCodePoints(current.length(), -1);
        return current.substring(0, lastStart);
    }
}
