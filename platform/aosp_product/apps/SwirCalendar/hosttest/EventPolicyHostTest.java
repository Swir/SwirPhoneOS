package org.swir.phoneos.calendar;

public final class EventPolicyHostTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check(EventPolicy.validTitle("Build review"), "valid title rejected");
        check(!EventPolicy.validTitle("   "), "blank title accepted");
        long start = 1_700_000_000_000L;
        check(EventPolicy.normalizeEnd(start, start) == start + EventPolicy.DEFAULT_DURATION_MS, "end normalization failed");
        check(EventPolicy.matches("ROOM", "Build review", "Blue room"), "search failed");
        check(EventPolicy.escapeIcs("A,B;C").equals("A\\,B\\;C"), "ICS escaping failed");
        String ics = EventPolicy.toIcs("42@swir", "Build review", "Blue room", start, start + 1000);
        check(ics.contains("BEGIN:VEVENT"), "VEVENT missing");
        check(ics.contains("SUMMARY:Build review"), "summary missing");
        check(ics.endsWith("END:VCALENDAR\r\n"), "calendar terminator missing");
    }
}
