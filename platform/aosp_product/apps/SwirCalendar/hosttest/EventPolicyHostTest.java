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
        check("A,B;C\nD".equals(EventPolicy.unescapeIcs("A\\,B\\;C\\nD")), "ICS unescape failed");
        String ics = EventPolicy.toIcs("42@swir", "Build review", "Blue room", start, start + 1000);
        check(ics.contains("BEGIN:VEVENT"), "VEVENT missing");
        check(ics.contains("SUMMARY:Build review"), "summary missing");
        check(ics.endsWith("END:VCALENDAR\r\n"), "calendar terminator missing");

        EventPolicy.ImportedEvent imported = EventPolicy.parseSingleEvent(ics);
        check(imported != null, "exported event should import");
        check("Build review".equals(imported.title()), "import title mismatch");
        check("Blue room".equals(imported.location()), "import location mismatch");
        check(imported.startMillis() == start, "import start mismatch");
        check(imported.endMillis() == start + 1000, "import end mismatch");

        String allDay = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20260918\nSUMMARY:Release review\nEND:VEVENT\nEND:VCALENDAR\n";
        EventPolicy.ImportedEvent allDayEvent = EventPolicy.parseSingleEvent(allDay);
        check(allDayEvent != null, "all-day event rejected");
        check(allDayEvent.endMillis() - allDayEvent.startMillis() == EventPolicy.DEFAULT_ALL_DAY_DURATION_MS,
                "all-day default duration mismatch");

        check(EventPolicy.parseSingleEvent(ics.replace("SUMMARY:Build review", "SUMMARY:A\r\nSUMMARY:B")) == null,
                "duplicate summary accepted");
        check(EventPolicy.parseSingleEvent(ics.replace("DTEND:20231114T221321Z", "DTEND:bad")) == null,
                "bad time accepted");
        check(EventPolicy.parseSingleEvent(ics + "BEGIN:VCALENDAR\n") == null,
                "trailing second calendar accepted");
        check(EventPolicy.parseSingleEvent("BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20260918T090000\nSUMMARY:X\nEND:VEVENT\nEND:VCALENDAR") == null,
                "ambiguous local time accepted");
        check(EventPolicy.parseSingleEvent("x".repeat(EventPolicy.MAX_ICS_BYTES + 1)) == null,
                "oversize calendar accepted");
        check(EventPolicy.unescapeIcs("bad\\q") == null, "unknown escape accepted");
    }
}
