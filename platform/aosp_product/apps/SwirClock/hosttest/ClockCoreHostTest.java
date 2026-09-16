package org.swir.phoneos.clock;

import java.util.Locale;

public final class ClockCoreHostTest {
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
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
        require(ClockCore.worldTime("UTC", 0L, Locale.US).startsWith("12:00"), "UTC epoch formatting");
        System.out.println("SwirClock ClockCore host tests passed");
    }
}
