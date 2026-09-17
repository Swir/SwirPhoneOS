package org.swir.phoneos.recorder;

public final class RecorderPolicyHostTest {
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        require(RecorderPolicy.canTransition(RecorderPolicy.State.IDLE, RecorderPolicy.State.RECORDING), "idle to recording");
        require(RecorderPolicy.canTransition(RecorderPolicy.State.RECORDING, RecorderPolicy.State.READY), "recording to ready");
        require(RecorderPolicy.canTransition(RecorderPolicy.State.READY, RecorderPolicy.State.PLAYING), "ready to playing");
        require(RecorderPolicy.canTransition(RecorderPolicy.State.PLAYING, RecorderPolicy.State.READY), "playing to ready");
        require(!RecorderPolicy.canTransition(RecorderPolicy.State.IDLE, RecorderPolicy.State.PLAYING), "idle cannot play");
        require(!RecorderPolicy.canTransition(RecorderPolicy.State.READY, RecorderPolicy.State.READY), "same state transition rejected");
        require(RecorderPolicy.recordingFileName(123L).equals("swir-recording-123.m4a"), "stable private file name");
        require(RecorderPolicy.formatDuration(0L).equals("00:00:00"), "zero duration");
        require(RecorderPolicy.formatDuration(3_661_000L).equals("01:01:01"), "hour duration");
        require(RecorderPolicy.formatDuration(-1L).equals("00:00:00"), "negative duration clamps");
        require(!RecorderPolicy.exportable(0L), "empty recording is not exportable");
        require(RecorderPolicy.exportable(1L), "non-empty recording is exportable");
    }
}
