package org.swir.phoneos.clock;

import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.FormatStyle;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/** Pure-Java time calculations shared by the Android activity and host tests. */
public final class ClockCore {
    private static final long MAX_TIMER_MILLIS = 24L * 60L * 60L * 1000L;
    private static final String[] WORLD_ZONE_IDS = {
            "UTC",
            "Europe/Oslo",
            "Europe/Warsaw",
            "America/New_York",
            "Asia/Tokyo"
    };

    private ClockCore() {}

    public static long timerMillis(String minutesText) {
        if (minutesText == null) return -1L;
        String value = minutesText.trim();
        if (!value.matches("[0-9]{1,4}")) return -1L;
        try {
            long minutes = Long.parseLong(value);
            if (minutes < 1L || minutes > 1440L) return -1L;
            return minutes * 60_000L;
        } catch (NumberFormatException ignored) {
            return -1L;
        }
    }

    public static boolean validAlarmTime(int hour, int minute) {
        return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
    }

    public static long stopwatchElapsed(long accumulatedMillis, long startedAtMillis, long nowMillis, boolean running) {
        if (accumulatedMillis < 0L || startedAtMillis < 0L || nowMillis < 0L) return 0L;
        if (!running) return Math.min(accumulatedMillis, MAX_TIMER_MILLIS * 365L);
        long delta = Math.max(0L, nowMillis - startedAtMillis);
        long max = MAX_TIMER_MILLIS * 365L;
        if (accumulatedMillis > max - Math.min(delta, max)) return max;
        return Math.min(max, accumulatedMillis + delta);
    }

    public static long timerRemaining(long durationMillis, long startedAtMillis, long nowMillis) {
        if (durationMillis <= 0L || durationMillis > MAX_TIMER_MILLIS || startedAtMillis < 0L || nowMillis < 0L) return 0L;
        long elapsed = Math.max(0L, nowMillis - startedAtMillis);
        return Math.max(0L, durationMillis - elapsed);
    }

    public static String formatDuration(long millis) {
        long safe = Math.max(0L, millis);
        long totalSeconds = safe / 1000L;
        long hours = totalSeconds / 3600L;
        long minutes = (totalSeconds % 3600L) / 60L;
        long seconds = totalSeconds % 60L;
        return String.format(Locale.ROOT, "%02d:%02d:%02d", hours, minutes, seconds);
    }

    public static int worldZoneCount() {
        return WORLD_ZONE_IDS.length;
    }

    public static String worldZoneId(int index) {
        if (index < 0 || index >= WORLD_ZONE_IDS.length) {
            throw new IllegalArgumentException("world zone index out of range");
        }
        return WORLD_ZONE_IDS[index];
    }

    public static int nextWorldZoneIndex(int index) {
        if (index < 0 || index >= WORLD_ZONE_IDS.length) {
            throw new IllegalArgumentException("world zone index out of range");
        }
        return (index + 1) % WORLD_ZONE_IDS.length;
    }

    public static String worldTime(String zoneId, long epochMillis, Locale locale) {
        if (zoneId == null || locale == null) throw new IllegalArgumentException("zone/locale required");
        ZoneId zone = ZoneId.of(zoneId);
        ZonedDateTime value = ZonedDateTime.ofInstant(Instant.ofEpochMilli(epochMillis), zone);
        DateTimeFormatter formatter = DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(locale);
        return formatter.format(value);
    }

    public static String worldZoneLabel(String zoneId, long epochMillis, Locale locale) {
        if (zoneId == null || locale == null) throw new IllegalArgumentException("zone/locale required");
        ZoneId.of(zoneId);
        TimeZone timeZone = TimeZone.getTimeZone(zoneId);
        boolean daylight = timeZone.inDaylightTime(new Date(epochMillis));
        return timeZone.getDisplayName(daylight, TimeZone.LONG, locale);
    }
}
