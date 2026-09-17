package org.swir.phoneos.phone;

public final class DialPolicyHostTest {
    public static void main(String[] args) {
        check("+481234#".equals(DialPolicy.normalize(" +48 (123) 4# ")), "normalize");
        check(DialPolicy.valid("112"), "valid number");
        check(!DialPolicy.valid("*#"), "requires digit");
        check("12#".equals(DialPolicy.append("12", "#")), "append");
        check("12".equals(DialPolicy.append("12", "+")), "plus only at start");
        check("12".equals(DialPolicy.backspace("123")), "backspace");
        StringBuilder huge = new StringBuilder();
        for (int i = 0; i < 100; i++) huge.append('9');
        check(DialPolicy.normalize(huge.toString()).length() == DialPolicy.MAX_NUMBER_LENGTH, "bounded");
    }

    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }
}
