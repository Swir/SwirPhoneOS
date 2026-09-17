package org.swir.phoneos.phone;

/** Pure Java policy for owner-entered dial strings. */
public final class DialPolicy {
    public static final int MAX_NUMBER_LENGTH = 64;

    private DialPolicy() {}

    public static String normalize(String raw) {
        if (raw == null) return "";
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < raw.length() && out.length() < MAX_NUMBER_LENGTH; i++) {
            char c = raw.charAt(i);
            if (Character.isDigit(c) || c == '*' || c == '#') {
                out.append(c);
            } else if (c == '+' && out.length() == 0) {
                out.append(c);
            }
        }
        return out.toString();
    }

    public static boolean valid(String raw) {
        String value = normalize(raw);
        if (value.isEmpty() || value.length() > MAX_NUMBER_LENGTH) return false;
        for (int i = 0; i < value.length(); i++) {
            if (Character.isDigit(value.charAt(i))) return true;
        }
        return false;
    }

    public static String append(String current, String token) {
        String base = normalize(current);
        String addition = token == null ? "" : token;
        if (addition.length() != 1) return base;
        char c = addition.charAt(0);
        if (!(Character.isDigit(c) || c == '*' || c == '#' || (c == '+' && base.isEmpty()))) return base;
        if (base.length() >= MAX_NUMBER_LENGTH) return base;
        return base + c;
    }

    public static String backspace(String current) {
        String value = normalize(current);
        return value.isEmpty() ? value : value.substring(0, value.length() - 1);
    }
}
