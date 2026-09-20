package org.swir.phoneos.messages;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;

/**
 * Bounded, local-only history for explicit text compose handoffs.
 *
 * This records that Swir Messages handed text compose metadata to a compatible Android app.
 * It deliberately does not claim that an SMS or MMS was sent, delivered, or received, and it never
 * stores attached media bytes. Message bodies are reduced to the same short, sanitized preview shown
 * in the UI before they are persisted so the history does not retain the full compose text.
 */
public final class MessageHandoffHistory {
    public static final int MAX_ENTRIES = 8;
    public static final int MAX_SERIALIZED_LENGTH = 64 * 1024;
    public static final int MAX_PREVIEW_CODEPOINTS = 96;

    private MessageHandoffHistory() {}

    public static final class Entry {
        public final long timestampMillis;
        public final String recipients;
        public final String body;

        Entry(long timestampMillis, String recipients, String body) {
            this.timestampMillis = timestampMillis;
            this.recipients = recipients;
            this.body = body;
        }
    }

    public static String prepend(String encoded, long timestampMillis, String recipients, String body) {
        String normalizedRecipients = MessagePolicy.normalizeRecipients(recipients);
        String storedBody = preview(body);
        if (timestampMillis <= 0 || normalizedRecipients.isEmpty() || storedBody.isEmpty()) {
            throw new IllegalArgumentException("invalid handoff history entry");
        }

        List<Entry> entries = new ArrayList<>();
        entries.add(new Entry(timestampMillis, normalizedRecipients, storedBody));
        for (Entry entry : decode(encoded)) {
            if (entries.size() >= MAX_ENTRIES) break;
            entries.add(entry);
        }
        return encode(entries);
    }

    public static List<Entry> decode(String encoded) {
        if (encoded == null || encoded.isEmpty()) return Collections.emptyList();
        if (encoded.length() > MAX_SERIALIZED_LENGTH) return Collections.emptyList();

        List<Entry> entries = new ArrayList<>();
        String[] lines = encoded.split("\\n", -1);
        for (String line : lines) {
            if (line.isEmpty()) continue;
            if (entries.size() >= MAX_ENTRIES) break;
            Entry entry = decodeLine(line);
            if (entry != null) entries.add(entry);
        }
        return Collections.unmodifiableList(entries);
    }

    public static String preview(String body) {
        String normalized = MessagePolicy.normalizeBody(body).trim();
        if (normalized.isEmpty()) return "";

        StringBuilder out = new StringBuilder();
        boolean pendingSpace = false;
        boolean truncated = false;
        int codePoints = 0;
        for (int offset = 0; offset < normalized.length();) {
            int codePoint = normalized.codePointAt(offset);
            offset += Character.charCount(codePoint);

            if (Character.isWhitespace(codePoint) || Character.isISOControl(codePoint)) {
                pendingSpace = out.length() > 0;
                continue;
            }

            if (pendingSpace) {
                if (codePoints >= MAX_PREVIEW_CODEPOINTS) {
                    truncated = true;
                    break;
                }
                out.append(' ');
                codePoints++;
                pendingSpace = false;
            }
            if (codePoints >= MAX_PREVIEW_CODEPOINTS) {
                truncated = true;
                break;
            }
            out.appendCodePoint(codePoint);
            codePoints++;
            if (offset < normalized.length() && codePoints >= MAX_PREVIEW_CODEPOINTS) truncated = true;
        }

        if (truncated && out.length() > 0) {
            int last = out.codePointBefore(out.length());
            out.delete(out.length() - Character.charCount(last), out.length());
            out.append('…');
        }
        return out.toString();
    }

    private static String encode(List<Entry> entries) {
        StringBuilder out = new StringBuilder();
        int count = 0;
        for (Entry entry : entries) {
            if (entry == null || count >= MAX_ENTRIES) break;
            String recipients = MessagePolicy.normalizeRecipients(entry.recipients);
            String body = preview(entry.body);
            if (entry.timestampMillis <= 0 || recipients.isEmpty() || body.isEmpty()) continue;
            if (out.length() > 0) out.append('\n');
            out.append(entry.timestampMillis)
                    .append('\t').append(encodeText(recipients))
                    .append('\t').append(encodeText(body));
            count++;
        }
        if (out.length() > MAX_SERIALIZED_LENGTH) {
            throw new IllegalStateException("handoff history exceeded storage bound");
        }
        return out.toString();
    }

    private static Entry decodeLine(String line) {
        String[] fields = line.split("\\t", -1);
        if (fields.length != 3) return null;
        try {
            long timestamp = Long.parseLong(fields[0]);
            if (timestamp <= 0) return null;
            String recipients = MessagePolicy.normalizeRecipients(decodeText(fields[1]));
            String body = preview(decodeText(fields[2]));
            if (recipients.isEmpty() || body.isEmpty()) return null;
            return new Entry(timestamp, recipients, body);
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private static String encodeText(String value) {
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static String decodeText(String value) {
        byte[] decoded = Base64.getUrlDecoder().decode(value);
        return new String(decoded, StandardCharsets.UTF_8);
    }
}
