package org.swir.phoneos.phone;

public final class CallHistoryPolicyHostTest {
    public static void main(String[] args) {
        expect("Alice", CallHistoryPolicy.displayLabel(true, " Alice ", "+4712345678", "Unknown"));
        expect("+4712345678", CallHistoryPolicy.displayLabel(true, "", "+4712345678", "Unknown"));
        expect("Unknown", CallHistoryPolicy.displayLabel(false, "Alice", "+4712345678", "Unknown"));
        expect("Unknown", CallHistoryPolicy.displayLabel(true, "", "-1", "Unknown"));
        expect("AB", CallHistoryPolicy.displayLabel(true, "A\nB", "", "Unknown"));
        expect("incoming", CallHistoryPolicy.typeKey(1));
        expect("outgoing", CallHistoryPolicy.typeKey(2));
        expect("missed", CallHistoryPolicy.typeKey(3));
        expect("voicemail", CallHistoryPolicy.typeKey(4));
        expect("rejected", CallHistoryPolicy.typeKey(5));
        expect("blocked", CallHistoryPolicy.typeKey(6));
        expect("other", CallHistoryPolicy.typeKey(99));
        expect("0:00", CallHistoryPolicy.formatDuration(-1));
        expect("1:05", CallHistoryPolicy.formatDuration(65));
        if (CallHistoryPolicy.MAX_RECENT_CALLS != 20) throw new AssertionError("recent call limit drifted");
        System.out.println("CallHistoryPolicyHostTest: PASS");
    }

    private static void expect(String expected, String actual) {
        if (!expected.equals(actual)) throw new AssertionError("expected=" + expected + " actual=" + actual);
    }
}
