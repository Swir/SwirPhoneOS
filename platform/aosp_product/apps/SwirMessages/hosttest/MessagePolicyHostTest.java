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
        System.out.println("MessagePolicyHostTest OK");
    }
}
