package org.swir.phoneos.messages;

import java.util.ArrayList;
import java.util.List;

public final class MessagePolicy {
    public static final int MAX_RECIPIENTS = 10;
    public static final int MAX_RECIPIENT_LENGTH = 32;
    public static final int MAX_BODY_LENGTH = 4000;

    private MessagePolicy() {}

    public static String normalizeRecipients(String raw) {
        if (raw == null) return "";
        String[] parts = raw.trim().split("[,;]", -1);
        List<String> normalized = new ArrayList<>();
        for (String part : parts) {
            String value = normalizeRecipient(part);
            if (value.isEmpty()) return "";
            if (!normalized.contains(value)) normalized.add(value);
            if (normalized.size() > MAX_RECIPIENTS) return "";
        }
        return String.join(",", normalized);
    }

    public static String normalizeRecipient(String raw) {
        if (raw == null) return "";
        String value = raw.trim();
        if (value.isEmpty()) return "";
        StringBuilder out = new StringBuilder();
        int digits = 0;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (Character.isDigit(c)) {
                out.append(c);
                digits++;
            } else if (c == '+' && out.length() == 0) {
                out.append(c);
            } else if (c == ' ' || c == '-' || c == '(' || c == ')' || c == '.') {
                continue;
            } else {
                return "";
            }
            if (out.length() > MAX_RECIPIENT_LENGTH) return "";
        }
        if (digits < 3) return "";
        return out.toString();
    }

    public static String normalizeBody(String raw) {
        if (raw == null) return "";
        String value = raw.replace("\r\n", "\n").replace('\r', '\n');
        if (value.length() > MAX_BODY_LENGTH) return value.substring(0, MAX_BODY_LENGTH);
        return value;
    }

    public static boolean canHandoff(String recipients, String body) {
        return !normalizeRecipients(recipients).isEmpty() && !normalizeBody(body).trim().isEmpty();
    }

    public static int remainingCharacters(String body) {
        return MAX_BODY_LENGTH - normalizeBody(body).length();
    }
}
