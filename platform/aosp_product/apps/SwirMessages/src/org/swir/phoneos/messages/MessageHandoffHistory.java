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
 * stores attached media bytes.
 */
public final class MessageHandoffHistory {
    public static final int MAX_ENTRIES = 8;
    public static final int MAX_SERIALIZED_LENGTH = 64 * 1024;
    public static final int MAX_PREVIEW_LENGTH = 96;

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
        String normalizedBody = MessagePolicy.normalizeBody(body);
        if (timestampMillis <= 0 || normalizedRecipients.isEmpty() || normalizedBody.trim().isEmpty()) {
            throw new IllegalArgumentException("invalid handoff history entry");
        }

        List<Entry> entries = new ArrayList<>();
        entries.add(new Entry(timestampMillis, normalizedRecipients, normalizedBody));
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
        String normalized = MessagePolicy.normalizeBody(body).trim().replace('\n', ' ');
        while (normalized.contains("  ")) normalized = normalized.replace("  ", " ");
        if (normalized.length() <= MAX_PREVIEW_LENGTH) return normalized;
        return normalized.substring(0, MAX_PREVIEW_LENGTH - 1) + "…";
    }

    private static String encode(List<Entry> entries) {
        StringBuilder out = new StringBuilder();
        int count = 0;
        for (Entry entry : entries) {
            if (entry == null || count >= MAX_ENTRIES) break;
            String recipients = MessagePolicy.normalizeRecipients(entry.recipients);
            String body = MessagePolicy.normalizeBody(entry.body);
            if (entry.timestampMillis <= 0 || recipients.isEmpty() || body.trim().isEmpty()) continue;
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
            String body = MessagePolicy.normalizeBody(decodeText(fields[2]));
            if (recipients.isEmpty() || body.trim().isEmpty()) return null;
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
