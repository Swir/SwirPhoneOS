package org.swir.phoneos.recorder;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

/** Pure-Java recording/file rules shared by the Android activity and host tests. */
public final class RecorderPolicy {
    private static final long MAX_EXPORT_BYTES = 512L * 1024L * 1024L;
    private static final DateTimeFormatter NAME_TIME = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss-SSS", Locale.ROOT).withZone(ZoneOffset.UTC);

    private RecorderPolicy() {}

    public static String recordingFileName(long epochMillis) {
        long safe = Math.max(0L, epochMillis);
        return "swir-recording-" + NAME_TIME.format(Instant.ofEpochMilli(safe)) + ".m4a";
    }

    public static boolean isRecordingFile(String name) {
        return name != null && name.matches("swir-recording-[0-9]{8}-[0-9]{6}-[0-9]{3}\\.m4a");
    }

    public static boolean canExport(long bytes) {
        return bytes > 0L && bytes <= MAX_EXPORT_BYTES;
    }

    public static boolean canRecord(boolean permissionGranted, boolean microphoneMuted) {
        return permissionGranted && !microphoneMuted;
    }
}
