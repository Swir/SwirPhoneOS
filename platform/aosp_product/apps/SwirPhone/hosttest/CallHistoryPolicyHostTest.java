package org.swir.phoneos.phone;

public final class CallHistoryPolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        final int allowed = 1;
        check("+4712345678".equals(CallHistoryPolicy.safeDialTarget(allowed, allowed, "+47 123 45 678")), "allowed caller is normalized");
        check(CallHistoryPolicy.safeDialTarget(2, allowed, "+4712345678").isEmpty(), "restricted caller stays private");
        check(CallHistoryPolicy.safeDialTarget(3, allowed, "12345").isEmpty(), "unknown caller stays private");
        check(CallHistoryPolicy.safeDialTarget(allowed, allowed, "12A34").isEmpty(), "malformed call-log number fails closed");
        check(CallHistoryPolicy.mayRevealNumber(allowed, allowed, "112"), "allowed dialable number may be revealed");
        check(!CallHistoryPolicy.mayRevealNumber(2, allowed, "112"), "presentation gate wins over a dialable number");
        check(CallHistoryPolicy.MAX_ENTRIES == 100, "history query remains bounded");
        System.out.println("CallHistoryPolicyHostTest OK");
    }
}
