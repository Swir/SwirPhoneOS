package org.swir.phoneos.phone;

public final class CallHistoryPolicy {
    public static final int MAX_ENTRIES = 100;

    private CallHistoryPolicy() {}

    public static String safeDialTarget(int presentation, int allowedPresentation, String rawNumber) {
        if (presentation != allowedPresentation) return "";
        return DialerPolicy.normalize(rawNumber);
    }

    public static boolean mayRevealNumber(int presentation, int allowedPresentation, String rawNumber) {
        return !safeDialTarget(presentation, allowedPresentation, rawNumber).isEmpty();
    }
}
