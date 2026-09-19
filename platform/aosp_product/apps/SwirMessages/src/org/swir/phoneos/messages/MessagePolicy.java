package org.swir.phoneos.messages;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class MessagePolicy {
    public static final int MAX_RECIPIENTS = 10;
    public static final int MAX_RECIPIENT_LENGTH = 32;
    public static final int MAX_BODY_LENGTH = 4000;
    public static final long MAX_ATTACHMENT_BYTES = 25L * 1024L * 1024L;
    public static final int MAX_ATTACHMENT_NAME_LENGTH = 180;

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

    public static boolean isSupportedMediaMime(String rawMime) {
        if (rawMime == null) return false;
        String mime = rawMime.trim().toLowerCase(Locale.ROOT);
        if (mime.isEmpty() || mime.length() > 128 || mime.indexOf(';') >= 0) return false;
        for (int i = 0; i < mime.length(); i++) {
            char c = mime.charAt(i);
            if (Character.isISOControl(c) || Character.isWhitespace(c)) return false;
        }
        return mime.startsWith("image/") || mime.startsWith("video/") || mime.startsWith("audio/");
    }

    public static String safeAttachmentName(String rawName) {
        if (rawName == null) return "";
        String value = rawName.trim();
        if (value.isEmpty() || value.length() > MAX_ATTACHMENT_NAME_LENGTH || ".".equals(value) || "..".equals(value)) return "";
        if (value.indexOf('/') >= 0 || value.indexOf('\\') >= 0) return "";
        for (int i = 0; i < value.length(); i++) {
            if (Character.isISOControl(value.charAt(i))) return "";
        }
        return value;
    }

    public static boolean attachmentReviewReady(String mime, String displayName, long sizeBytes) {
        return isSupportedMediaMime(mime)
                && !safeAttachmentName(displayName).isEmpty()
                && sizeBytes > 0L
                && sizeBytes <= MAX_ATTACHMENT_BYTES;
    }

    /** Source-stage owner-visible media handoff only; this does not claim carrier MMS delivery. */
    public static boolean canMediaHandoff(String recipients, String body, String mime, String displayName, long sizeBytes) {
        if (normalizeRecipients(recipients).isEmpty()) return false;
        normalizeBody(body); // Enforce the same bounded body normalization even when text is optional.
        return attachmentReviewReady(mime, displayName, sizeBytes);
    }

    public static int remainingCharacters(String body) {
        return MAX_BODY_LENGTH - normalizeBody(body).length();
    }
}
