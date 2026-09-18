package org.swir.phoneos.clock;

import java.util.Locale;

public final class ClockCoreHostTest {
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void requireThrows(Runnable action, String message) {
        try {
            action.run();
            throw new AssertionError(message);
        } catch (IllegalArgumentException expected) {
            // expected fail-closed validation
        }
    }

    public static void main(String[] args) {
        require(ClockCore.timerMillis("5") == 300_000L, "five minute timer");
        require(ClockCore.timerMillis("0") == -1L, "zero timer rejected");
        require(ClockCore.timerMillis("1441") == -1L, "oversized timer rejected");
        require(ClockCore.timerMillis("5.5") == -1L, "non-integer timer rejected");
        require(ClockCore.validAlarmTime(0, 0), "midnight valid");
        require(ClockCore.validAlarmTime(23, 59), "end of day valid");
        require(!ClockCore.validAlarmTime(24, 0), "hour overflow rejected");
        require(!ClockCore.validAlarmTime(12, 60), "minute overflow rejected");
        require(ClockCore.stopwatchElapsed(1_000L, 2_000L, 4_500L, true) == 3_500L, "stopwatch elapsed");
        require(ClockCore.stopwatchElapsed(1_000L, 2_000L, 4_500L, false) == 1_000L, "paused stopwatch stable");
        require(ClockCore.timerRemaining(60_000L, 10_000L, 40_000L) == 30_000L, "timer remaining");
        require(ClockCore.timerRemaining(60_000L, 10_000L, 90_000L) == 0L, "expired timer clamps");
        require("01:01:01".equals(ClockCore.formatDuration(3_661_999L)), "duration formatting");

        require(ClockCore.worldZoneCount() == 5, "reviewed world zone inventory");
        require(ClockCore.safeWorldZoneIndex(0) == 0, "valid saved zone preserved");
        require(ClockCore.safeWorldZoneIndex(4) == 4, "last valid saved zone preserved");
        require(ClockCore.safeWorldZoneIndex(-1) == 0, "negative saved zone falls back to UTC");
        require(ClockCore.safeWorldZoneIndex(99) == 0, "oversized saved zone falls back to UTC");
        require("UTC".equals(ClockCore.worldZoneId(0)), "UTC first world zone");
        require("Europe/Oslo".equals(ClockCore.worldZoneId(1)), "Oslo world zone");
        require("Europe/Warsaw".equals(ClockCore.worldZoneId(2)), "Warsaw world zone");
        require("America/New_York".equals(ClockCore.worldZoneId(3)), "New York world zone");
        require("Asia/Tokyo".equals(ClockCore.worldZoneId(4)), "Tokyo world zone");
        require(ClockCore.nextWorldZoneIndex(4) == 0, "world zone selection wraps");
        requireThrows(() -> ClockCore.worldZoneId(-1), "negative world zone rejected");
        requireThrows(() -> ClockCore.nextWorldZoneIndex(5), "overflow world zone rejected");
        requireThrows(() -> ClockCore.worldTime("Not/AZone", 0L, Locale.US), "invalid IANA world-time zone rejected");
        requireThrows(() -> ClockCore.worldZoneLabel("Not/AZone", 0L, Locale.US), "invalid IANA world-label zone rejected");
        require(ClockCore.worldTime("UTC", 0L, Locale.US).startsWith("12:00"), "UTC epoch formatting");
        require(ClockCore.worldTime("Asia/Tokyo", 0L, Locale.US).startsWith("9:00"), "Tokyo epoch formatting");
        require(!ClockCore.worldZoneLabel("Europe/Oslo", 0L, Locale.US).trim().isEmpty(), "localized zone label");
        System.out.println("SwirClock ClockCore host tests passed");
    }
}
