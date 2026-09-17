package org.swir.phoneos.recorder;

import java.util.Locale;

public final class RecorderPolicy {
    public enum State { IDLE, RECORDING, READY, PLAYING }

    private RecorderPolicy() {}

    public static boolean canTransition(State from, State to) {
        if (from == null || to == null || from == to) return false;
        return switch (from) {
            case IDLE -> to == State.RECORDING;
            case RECORDING -> to == State.READY || to == State.IDLE;
            case READY -> to == State.RECORDING || to == State.PLAYING || to == State.IDLE;
            case PLAYING -> to == State.READY || to == State.IDLE;
        };
    }

    public static String recordingFileName(long epochMillis) {
        if (epochMillis < 0) throw new IllegalArgumentException("epochMillis");
        return "swir-recording-" + epochMillis + ".m4a";
    }

    public static String formatDuration(long millis) {
        long safe = Math.max(0L, millis);
        long totalSeconds = safe / 1000L;
        long hours = totalSeconds / 3600L;
        long minutes = (totalSeconds % 3600L) / 60L;
        long seconds = totalSeconds % 60L;
        return String.format(Locale.ROOT, "%02d:%02d:%02d", hours, minutes, seconds);
    }

    public static boolean exportable(long fileLength) {
        return fileLength > 0L;
    }
}
