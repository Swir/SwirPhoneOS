package org.swir.phoneos.calendar;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

public final class EventPolicy {
    public static final int MAX_TITLE = 160;
    public static final int MAX_LOCATION = 240;
    public static final int MAX_ICS_BYTES = 64 * 1024;
    public static final long DEFAULT_DURATION_MS = 60L * 60L * 1000L;
    public static final long DEFAULT_ALL_DAY_DURATION_MS = 24L * 60L * 60L * 1000L;

    public static final class ImportedEvent {
        private final String title;
        private final String location;
        private final long startMillis;
        private final long endMillis;

        ImportedEvent(String title, String location, long startMillis, long endMillis) {
            this.title = title;
            this.location = location;
            this.startMillis = startMillis;
            this.endMillis = endMillis;
        }

        public String title() { return title; }
        public String location() { return location; }
        public long startMillis() { return startMillis; }
        public long endMillis() { return endMillis; }
    }

    private static final class ParsedTime {
        final long millis;
        final boolean allDay;
        ParsedTime(long millis, boolean allDay) {
            this.millis = millis;
            this.allDay = allDay;
        }
    }

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

    public static String unescapeIcs(String value) {
        if (value == null) return "";
        StringBuilder out = new StringBuilder(value.length());
        boolean escaped = false;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (!escaped) {
                if (c == '\\') escaped = true;
                else out.append(c);
                continue;
            }
            if (c == 'n' || c == 'N') out.append('\n');
            else if (c == '\\' || c == ';' || c == ',') out.append(c);
            else return null;
            escaped = false;
        }
        return escaped ? null : out.toString();
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

    /**
     * Parses one bounded, local VEVENT into the app-private agenda. This deliberately accepts a
     * small interoperable subset: UTC date-times or all-day dates, one event, no recurrence and no
     * implicit network/provider access. Unknown non-critical properties are ignored.
     */
    public static ImportedEvent parseSingleEvent(String ics) {
        if (ics == null || ics.isEmpty() || ics.length() > MAX_ICS_BYTES || ics.indexOf('\0') >= 0) return null;
        List<String> lines = unfoldLines(ics);
        if (lines == null || lines.size() < 4) return null;

        boolean calendarOpen = false;
        boolean eventOpen = false;
        boolean eventClosed = false;
        boolean calendarClosed = false;
        String title = null;
        String location = "";
        ParsedTime start = null;
        ParsedTime end = null;

        for (String line : lines) {
            if (line.isEmpty()) continue;
            if ("BEGIN:VCALENDAR".equals(line)) {
                if (calendarOpen || calendarClosed || eventOpen || eventClosed) return null;
                calendarOpen = true;
                continue;
            }
            if ("END:VCALENDAR".equals(line)) {
                if (!calendarOpen || eventOpen || !eventClosed || calendarClosed) return null;
                calendarClosed = true;
                continue;
            }
            if ("BEGIN:VEVENT".equals(line)) {
                if (!calendarOpen || eventOpen || eventClosed || calendarClosed) return null;
                eventOpen = true;
                continue;
            }
            if ("END:VEVENT".equals(line)) {
                if (!eventOpen || eventClosed) return null;
                eventOpen = false;
                eventClosed = true;
                continue;
            }
            if (!eventOpen) continue;

            int colon = line.indexOf(':');
            if (colon <= 0) return null;
            String key = line.substring(0, colon);
            String value = line.substring(colon + 1);
            if ("SUMMARY".equals(key)) {
                if (title != null) return null;
                title = unescapeIcs(value);
                if (!validTitle(title)) return null;
            } else if ("LOCATION".equals(key)) {
                if (!location.isEmpty()) return null;
                String decoded = unescapeIcs(value);
                if (decoded == null || !validLocation(decoded)) return null;
                location = decoded;
            } else if ("DTSTART".equals(key)) {
                if (start != null) return null;
                start = parseTime(value);
                if (start == null) return null;
            } else if ("DTEND".equals(key)) {
                if (end != null) return null;
                end = parseTime(value);
                if (end == null) return null;
            }
        }

        if (!calendarOpen || !calendarClosed || eventOpen || !eventClosed || title == null || start == null) return null;
        long resolvedEnd;
        if (end == null) resolvedEnd = start.millis + (start.allDay ? DEFAULT_ALL_DAY_DURATION_MS : DEFAULT_DURATION_MS);
        else resolvedEnd = end.millis;
        if (start.millis < 0 || resolvedEnd <= start.millis) return null;
        return new ImportedEvent(title, location, start.millis, resolvedEnd);
    }

    private static List<String> unfoldLines(String ics) {
        String normalized = ics.replace("\r\n", "\n").replace('\r', '\n');
        String[] raw = normalized.split("\n", -1);
        ArrayList<String> lines = new ArrayList<>();
        for (String line : raw) {
            if (!line.isEmpty() && (line.charAt(0) == ' ' || line.charAt(0) == '\t')) {
                if (lines.isEmpty()) return null;
                int last = lines.size() - 1;
                lines.set(last, lines.get(last) + line.substring(1));
            } else {
                lines.add(line);
            }
        }
        return lines;
    }

    private static ParsedTime parseTime(String value) {
        final boolean allDay;
        final String pattern;
        if (value.length() == 8) {
            allDay = true;
            pattern = "yyyyMMdd";
        } else if (value.length() == 16 && value.endsWith("Z")) {
            allDay = false;
            pattern = "yyyyMMdd'T'HHmmss'Z'";
        } else {
            return null;
        }
        SimpleDateFormat format = new SimpleDateFormat(pattern, Locale.ROOT);
        format.setLenient(false);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        try {
            Date parsed = format.parse(value);
            if (parsed == null) return null;
            return new ParsedTime(parsed.getTime(), allDay);
        } catch (ParseException ignored) {
            return null;
        }
    }
}
