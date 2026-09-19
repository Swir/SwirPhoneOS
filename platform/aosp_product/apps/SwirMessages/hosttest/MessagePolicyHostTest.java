package org.swir.phoneos.messages;

public final class MessagePolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check("+4712345678".equals(MessagePolicy.normalizeRecipient("+47 123 45 678")), "international recipient");
        check("12345,67890".equals(MessagePolicy.normalizeRecipients("12345; 67890")), "multi recipient normalization");
        check("12345".equals(MessagePolicy.normalizeRecipients("12345,12345")), "duplicates collapse");
        check(MessagePolicy.normalizeRecipient("12A34").isEmpty(), "letters fail closed");
        check(MessagePolicy.normalizeRecipient("++47123").isEmpty(), "second plus fails closed");
        check(MessagePolicy.canHandoff("112", "Need help"), "valid explicit handoff");
        check(!MessagePolicy.canHandoff("112", "   "), "empty body rejected");
        check("a\nb".equals(MessagePolicy.normalizeBody("a\r\nb")), "line endings normalize");
        StringBuilder longBody = new StringBuilder();
        for (int i = 0; i < MessagePolicy.MAX_BODY_LENGTH + 10; i++) longBody.append('x');
        check(MessagePolicy.normalizeBody(longBody.toString()).length() == MessagePolicy.MAX_BODY_LENGTH, "body bounded");
        check(MessagePolicy.remainingCharacters("abc") == MessagePolicy.MAX_BODY_LENGTH - 3, "remaining count");

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
