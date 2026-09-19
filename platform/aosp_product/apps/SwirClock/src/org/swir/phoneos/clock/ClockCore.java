package org.swir.phoneos.clock;

import java.time.DateTimeException;
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
    private static final long MAX_SESSION_DRIFT_MILLIS = 2L * 60L * 1000L;
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

    /**
     * Verifies that an elapsed-realtime snapshot still belongs to this boot/session.
     *
     * Android's monotonic elapsed clock resets at reboot while wall time does not. A restored
     * activity therefore carries both clocks and resumes only when their deltas remain close.
     * Large wall-clock corrections fail closed rather than resurrecting a stale timer.
     */
    public static boolean canRestoreElapsedSession(
            long startedElapsedMillis,
            long startedWallMillis,
            long nowElapsedMillis,
            long nowWallMillis) {
        if (startedElapsedMillis < 0L || startedWallMillis <= 0L || nowElapsedMillis < 0L || nowWallMillis <= 0L) {
            return false;
        }
        if (nowElapsedMillis < startedElapsedMillis || nowWallMillis < startedWallMillis) {
            return false;
        }
        long elapsedDelta = nowElapsedMillis - startedElapsedMillis;
        long wallDelta = nowWallMillis - startedWallMillis;
        long difference = elapsedDelta >= wallDelta ? elapsedDelta - wallDelta : wallDelta - elapsedDelta;
        return difference <= MAX_SESSION_DRIFT_MILLIS;
    }

    /** Returns remaining time for a verified restored timer, or -1 when the snapshot is stale. */
    public static long restoredTimerRemaining(
            long durationMillis,
            long startedElapsedMillis,
            long startedWallMillis,
            long nowElapsedMillis,
            long nowWallMillis) {
        if (durationMillis <= 0L || durationMillis > MAX_TIMER_MILLIS) return -1L;
        if (!canRestoreElapsedSession(startedElapsedMillis, startedWallMillis, nowElapsedMillis, nowWallMillis)) {
            return -1L;
        }
        return timerRemaining(durationMillis, startedElapsedMillis, nowElapsedMillis);
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

    public static int safeWorldZoneIndex(int index) {
        return index >= 0 && index < WORLD_ZONE_IDS.length ? index : 0;
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
        if (locale == null) throw new IllegalArgumentException("locale required");
        ZoneId zone = requireZoneId(zoneId);
        ZonedDateTime value = ZonedDateTime.ofInstant(Instant.ofEpochMilli(epochMillis), zone);
        DateTimeFormatter formatter = DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(locale);
        return formatter.format(value);
    }

    public static String worldZoneLabel(String zoneId, long epochMillis, Locale locale) {
        if (locale == null) throw new IllegalArgumentException("locale required");
        requireZoneId(zoneId);
        TimeZone timeZone = TimeZone.getTimeZone(zoneId);
        boolean daylight = timeZone.inDaylightTime(new Date(epochMillis));
        return timeZone.getDisplayName(daylight, TimeZone.LONG, locale);
    }

    private static ZoneId requireZoneId(String zoneId) {
        if (zoneId == null || zoneId.trim().isEmpty()) {
            throw new IllegalArgumentException("zone required");
        }
        try {
            return ZoneId.of(zoneId);
        } catch (DateTimeException exc) {
            throw new IllegalArgumentException("invalid world zone", exc);
        }
    }
}
