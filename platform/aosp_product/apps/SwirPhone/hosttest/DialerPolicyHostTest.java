package org.swir.phoneos.phone;

public final class DialerPolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check("+4712345678".equals(DialerPolicy.normalize("+47 123 45 678")), "international normalization");
        check("+4712345".equals(DialerPolicy.normalize("+٤٧ ١٢٣٤٥")), "Arabic-Indic digits canonicalize to ASCII");
        check("+4712345".equals(DialerPolicy.normalize("+47\u00A012345")), "localized spacing is accepted and removed");
        check("123#45".equals(DialerPolicy.normalize("(123)-#45")), "formatting normalization");
        check(DialerPolicy.normalize("12A34").isEmpty(), "letters must fail closed");
        check(DialerPolicy.normalize("+#").isEmpty(), "at least one digit is required");
        check(DialerPolicy.isDialable("112"), "emergency-style numeric input is dialable for system handoff");
        check("12*".equals(DialerPolicy.appendKey("12", '*')), "keypad append");
        check("123".equals(DialerPolicy.appendKey("12", '٣')), "localized keypad digit canonicalizes to ASCII");
        check("12".equals(DialerPolicy.appendKey("12", 'A')), "unsupported key ignored");
        check("12".equals(DialerPolicy.eraseLast("123")), "backspace");
        check("A".equals(DialerPolicy.eraseLast("A🚀")), "backspace removes one supplementary Unicode code point");
        check(DialerPolicy.eraseLast("").isEmpty(), "empty backspace");
        StringBuilder longNumber = new StringBuilder();
        for (int i = 0; i < DialerPolicy.MAX_DIAL_LENGTH + 1; i++) longNumber.append('1');
        check(DialerPolicy.normalize(longNumber.toString()).isEmpty(), "oversized dial strings fail closed");
        System.out.println("DialerPolicyHostTest OK");
    }
}
