package org.swir.phoneos.messages;

public final class MessagePolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static boolean hasUnpairedSurrogate(String value) {
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (i + 1 >= value.length() || !Character.isLowSurrogate(value.charAt(i + 1))) return true;
                i++;
            } else if (Character.isLowSurrogate(c)) {
                return true;
            }
        }
        return false;
    }

    public static void main(String[] args) {
        check("+4712345678".equals(MessagePolicy.normalizeRecipient("+47 123 45 678")), "international recipient");
        check("12345,67890".equals(MessagePolicy.normalizeRecipients("12345; 67890")), "multi recipient normalization");
        check("12345".equals(MessagePolicy.normalizeRecipients("12345,12345")), "duplicates collapse");
        check("+4712345".equals(MessagePolicy.normalizeRecipient("+٤٧ ١٢٣٤٥")), "Arabic-Indic digits canonicalize to ASCII");
        check("+4712345".equals(MessagePolicy.normalizeRecipient("+47\u00A012345")), "localized spacing is accepted and removed");
        check(MessagePolicy.normalizeRecipient("12A34").isEmpty(), "letters fail closed");
        check(MessagePolicy.normalizeRecipient("++47123").isEmpty(), "second plus fails closed");
        check(MessagePolicy.canHandoff("112", "Need help"), "valid explicit handoff");
        check(!MessagePolicy.canHandoff("112", "   "), "empty body rejected");
        check("a\nb".equals(MessagePolicy.normalizeBody("a\r\nb")), "line endings normalize");

        StringBuilder longBody = new StringBuilder();
        for (int i = 0; i < MessagePolicy.MAX_BODY_LENGTH + 10; i++) longBody.append('x');
        String normalizedLongBody = MessagePolicy.normalizeBody(longBody.toString());
        check(normalizedLongBody.codePointCount(0, normalizedLongBody.length()) == MessagePolicy.MAX_BODY_CODEPOINTS, "body bounded by code points");
        check(MessagePolicy.remainingCharacters("abc") == MessagePolicy.MAX_BODY_CODEPOINTS - 3, "remaining count");

        StringBuilder emojiBody = new StringBuilder();
        for (int i = 0; i < MessagePolicy.MAX_BODY_CODEPOINTS + 10; i++) emojiBody.appendCodePoint(0x1F680);
        String normalizedEmojiBody = MessagePolicy.normalizeBody(emojiBody.toString());
        check(normalizedEmojiBody.codePointCount(0, normalizedEmojiBody.length()) == MessagePolicy.MAX_BODY_CODEPOINTS, "supplementary Unicode body uses code-point limit");
        check(!hasUnpairedSurrogate(normalizedEmojiBody), "body truncation never splits a surrogate pair");
        check(MessagePolicy.remainingCharacters("🚀🚀🚀") == MessagePolicy.MAX_BODY_CODEPOINTS - 3, "emoji counter counts user-visible code points");

        check(MessagePolicy.isSupportedMediaMime("image/jpeg"), "image media accepted");
        check(MessagePolicy.isSupportedMediaMime("video/mp4"), "video media accepted");
        check(MessagePolicy.isSupportedMediaMime("audio/ogg"), "audio media accepted");
        check(!MessagePolicy.isSupportedMediaMime("application/pdf"), "non-media rejected");
        check(!MessagePolicy.isSupportedMediaMime("image/jpeg; charset=utf-8"), "parameterized media type rejected");
        check(!MessagePolicy.isSupportedMediaMime("image/*"), "wildcard subtype rejected");
        check(!MessagePolicy.isSupportedMediaMime("image/"), "empty subtype rejected");
        check(!MessagePolicy.isSupportedMediaMime("image/jpeg/extra"), "multiple slashes rejected");
        check("photo.jpg".equals(MessagePolicy.safeAttachmentName(" photo.jpg ")), "attachment name normalized");
        check(MessagePolicy.safeAttachmentName("../photo.jpg").isEmpty(), "attachment traversal rejected");
        check(MessagePolicy.safeAttachmentName("bad\\name.jpg").isEmpty(), "attachment backslash rejected");
        check(MessagePolicy.attachmentReviewReady("image/jpeg", "photo.jpg", 1024L), "bounded media ready");
        check(!MessagePolicy.attachmentReviewReady("image/jpeg", "photo.jpg", 0L), "zero-size media rejected");
        check(!MessagePolicy.attachmentReviewReady("image/jpeg", "photo.jpg", MessagePolicy.MAX_ATTACHMENT_BYTES + 1L), "oversize media rejected");
        check(MessagePolicy.canMediaHandoff("+4712345678", "", "image/jpeg", "photo.jpg", 1024L), "attachment-only handoff accepted");
        check(!MessagePolicy.canMediaHandoff("12", "caption", "image/jpeg", "photo.jpg", 1024L), "invalid media recipient rejected");
        System.out.println("MessagePolicyHostTest OK");
    }
}
