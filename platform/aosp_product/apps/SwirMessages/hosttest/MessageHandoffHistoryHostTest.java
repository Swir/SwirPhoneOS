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
        check("Hello there".equals(entries.get(0).body), "persisted body is the sanitized UI preview");

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
        check(preview.codePointCount(0, preview.length()) == MessageHandoffHistory.MAX_PREVIEW_CODEPOINTS, "preview is code-point bounded");
        check(preview.endsWith("…"), "truncated preview is explicit");
        check("two lines".equals(MessageHandoffHistory.preview("two\n lines")), "preview collapses whitespace");
        check("control text".equals(MessageHandoffHistory.preview("control\u0000\u0007 text")), "preview removes control characters");

        StringBuilder emojiBody = new StringBuilder();
        for (int i = 0; i < 140; i++) emojiBody.appendCodePoint(0x1F680);
        String emojiPreview = MessageHandoffHistory.preview(emojiBody.toString());
        check(emojiPreview.codePointCount(0, emojiPreview.length()) == MessageHandoffHistory.MAX_PREVIEW_CODEPOINTS, "supplementary Unicode is not split by the bound");
        check(emojiPreview.endsWith("…"), "Unicode truncation remains explicit");

        String minimized = MessageHandoffHistory.prepend("", 3000L, "12345", longBody.toString());
        List<MessageHandoffHistory.Entry> minimizedEntries = MessageHandoffHistory.decode(minimized);
        check(minimizedEntries.size() == 1, "minimized history round trips");
        check(minimizedEntries.get(0).body.equals(preview), "full compose body is not retained in local history");

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
