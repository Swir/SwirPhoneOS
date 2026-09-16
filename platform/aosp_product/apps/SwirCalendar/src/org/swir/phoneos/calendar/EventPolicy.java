package org.swir.phoneos.calendar;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

public final class EventPolicy {
    public static final int MAX_TITLE = 160;
    public static final int MAX_LOCATION = 240;
    public static final long DEFAULT_DURATION_MS = 60L * 60L * 1000L;

    private EventPolicy() {}

    public static boolean validTitle(String title) {
        return title != null && !title.trim().isEmpty() && title.length() <= MAX_TITLE;
    }

    public static boolean validLocation(String location) {
        return location != null && location.length() <= MAX_LOCATION;
    }

    public static long normalizeEnd(long startMillis, long endMillis) {
        if (startMillis < 0) return -1;
        return endMillis > startMillis ? endMillis : startMillis + DEFAULT_DURATION_MS;
    }

    public static boolean matches(String query, String title, String location) {
        String q = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        if (q.isEmpty()) return true;
        String t = title == null ? "" : title.toLowerCase(Locale.ROOT);
        String l = location == null ? "" : location.toLowerCase(Locale.ROOT);
        return t.contains(q) || l.contains(q);
    }

    public static String escapeIcs(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
                .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n");
    }

    private static String utc(long millis) {
        SimpleDateFormat format = new SimpleDateFormat("yyyyMMdd'T'HHmmss'Z'", Locale.ROOT);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date(millis));
    }

    public static String toIcs(String uid, String title, String location, long startMillis, long endMillis) {
        long end = normalizeEnd(startMillis, endMillis);
        return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//SwirPhoneOS//Calendar//EN\r\nBEGIN:VEVENT\r\n"
                + "UID:" + escapeIcs(uid) + "\r\nDTSTART:" + utc(startMillis) + "\r\nDTEND:" + utc(end) + "\r\n"
                + "SUMMARY:" + escapeIcs(title) + "\r\nLOCATION:" + escapeIcs(location) + "\r\n"
                + "END:VEVENT\r\nEND:VCALENDAR\r\n";
    }
}
