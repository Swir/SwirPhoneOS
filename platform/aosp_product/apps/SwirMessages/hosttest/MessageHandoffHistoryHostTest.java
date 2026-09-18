package org.swir.phoneos.messages;

import java.util.List;

public final class MessageHandoffHistoryHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        String encoded = MessageHandoffHistory.prepend("", 1000L, "+47 123 45 678", "Hello\r\nthere");
        List<MessageHandoffHistory.Entry> entries = MessageHandoffHistory.decode(encoded);
        check(entries.size() == 1, "one entry round trips");
        check(entries.get(0).timestampMillis == 1000L, "timestamp round trips");
        check("+4712345678".equals(entries.get(0).recipients), "recipient is normalized before storage");
        check("Hello\nthere".equals(entries.get(0).body), "body line endings normalize before storage");

        for (int i = 0; i < MessageHandoffHistory.MAX_ENTRIES + 4; i++) {
            encoded = MessageHandoffHistory.prepend(encoded, 2000L + i, "12345", "Message " + i);
        }
        entries = MessageHandoffHistory.decode(encoded);
        check(entries.size() == MessageHandoffHistory.MAX_ENTRIES, "history remains bounded");
        check(entries.get(0).timestampMillis == 2011L, "newest entry remains first");
        check("Message 11".equals(entries.get(0).body), "newest body remains first");

        check(MessageHandoffHistory.decode("garbage").isEmpty(), "corrupt rows fail closed");
        check(MessageHandoffHistory.decode("1\t%%%\t%%%").isEmpty(), "invalid base64 fails closed");
        check(MessageHandoffHistory.decode("-1\tMTIzNDU\tSGVsbG8").isEmpty(), "invalid timestamp fails closed");

        StringBuilder oversized = new StringBuilder();
        for (int i = 0; i <= MessageHandoffHistory.MAX_SERIALIZED_LENGTH; i++) oversized.append('x');
        check(MessageHandoffHistory.decode(oversized.toString()).isEmpty(), "oversized storage fails closed");

        StringBuilder longBody = new StringBuilder();
        for (int i = 0; i < 200; i++) longBody.append('a');
        String preview = MessageHandoffHistory.preview(longBody.toString());
        check(preview.length() == MessageHandoffHistory.MAX_PREVIEW_LENGTH, "preview is bounded");
        check(preview.endsWith("…"), "truncated preview is explicit");
        check("two lines".equals(MessageHandoffHistory.preview("two\n lines")), "preview collapses whitespace");

        boolean rejected = false;
        try {
            MessageHandoffHistory.prepend("", 0L, "12345", "hello");
        } catch (IllegalArgumentException expected) {
            rejected = true;
        }
        check(rejected, "invalid new entry is rejected");
        System.out.println("MessageHandoffHistoryHostTest OK");
    }
}
