package org.swir.phoneos.recorder;

public final class RecorderPolicyHostTest {
    public static void main(String[] args) {
        String name = RecorderPolicy.recordingFileName(0L);
        require(name.equals("swir-recording-19700101-000000-000.m4a"), "File name must be deterministic UTC");
        require(RecorderPolicy.isRecordingFile(name), "Generated recording name must validate");
        require(!RecorderPolicy.isRecordingFile("../recording.m4a"), "Traversal-like names must fail");
        require(RecorderPolicy.canExport(1L), "Non-empty recording must export");
        require(!RecorderPolicy.canExport(0L), "Empty recording must not export");
        require(!RecorderPolicy.canExport(513L * 1024L * 1024L), "Oversized recording must fail closed");
        require(RecorderPolicy.canRecord(true, false), "Granted and unmuted microphone may record");
        require(!RecorderPolicy.canRecord(false, false), "Missing permission must block recording");
        require(!RecorderPolicy.canRecord(true, true), "Muted microphone must block recording");
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
