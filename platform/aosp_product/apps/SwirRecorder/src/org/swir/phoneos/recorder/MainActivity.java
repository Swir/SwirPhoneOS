package org.swir.phoneos.recorder;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.MediaRecorder;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Date;
import java.util.Locale;

/** Foreground-only owner-controlled voice recorder with app-private storage and explicit export. */
public final class MainActivity extends Activity {
    private static final int AUDIO_PERMISSION_REQUEST = 6201;
    private static final int EXPORT_REQUEST = 6202;
    private static final int MAX_LIST_ITEMS = 100;

    private AudioManager audioManager;
    private MediaRecorder recorder;
    private MediaPlayer player;
    private File activeRecording;
    private File pendingExport;
    private boolean recordingPaused;
    private TextView microphoneState;
    private TextView recordingState;
    private LinearLayout recordingList;
    private Button startButton;
    private Button pauseButton;
    private Button stopButton;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        audioManager = getSystemService(AudioManager.class);
        getWindow().setStatusBarColor(Color.rgb(4, 11, 23));
        getWindow().setNavigationBarColor(Color.rgb(4, 11, 23));
        setContentView(buildUi());
        refreshControls();
    }

    @Override protected void onStart() {
        super.onStart();
        refreshMicrophoneState();
        refreshRecordings();
    }

    @Override protected void onStop() {
        stopPlayback();
        if (recorder != null) stopRecording(false);
        super.onStop();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == AUDIO_PERMISSION_REQUEST) {
            refreshMicrophoneState();
            if (!hasAudioPermission()) Toast.makeText(this, R.string.permission_denied, Toast.LENGTH_SHORT).show();
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != EXPORT_REQUEST) return;
        File source = pendingExport;
        pendingExport = null;
        if (resultCode != RESULT_OK || data == null || data.getData() == null || source == null) return;
        try (FileInputStream input = new FileInputStream(source); OutputStream output = getContentResolver().openOutputStream(data.getData(), "w")) {
            if (output == null) throw new IOException("No output stream");
            byte[] buffer = new byte[16384];
            int count;
            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            output.flush();
            Toast.makeText(this, R.string.export_complete, Toast.LENGTH_SHORT).show();
        } catch (IOException | SecurityException error) {
            Toast.makeText(this, R.string.export_failed, Toast.LENGTH_LONG).show();
        }
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(28));
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        root.addView(text(getString(R.string.app_name), 28, Color.rgb(105, 216, 255)), matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, Color.rgb(180, 198, 217));
        subtitle.setPadding(0, dp(4), 0, dp(14));
        root.addView(subtitle, matchWrap());

        LinearLayout microphoneCard = card();
        microphoneCard.addView(text(getString(R.string.microphone_title), 17, Color.rgb(105, 216, 255)), matchWrap());
        microphoneState = text(getString(R.string.microphone_permission_body), 14, Color.rgb(180, 198, 217));
        microphoneState.setPadding(0, dp(4), 0, dp(8));
        microphoneCard.addView(microphoneState, matchWrap());
        Button permission = button(R.string.grant_microphone);
        permission.setOnClickListener(v -> requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, AUDIO_PERMISSION_REQUEST));
        microphoneCard.addView(permission, matchWrap());
        root.addView(microphoneCard, spaced());

        LinearLayout controlCard = card();
        controlCard.addView(text(getString(R.string.recording_controls), 17, Color.rgb(105, 216, 255)), matchWrap());
        recordingState = text(getString(R.string.state_idle), 22, Color.WHITE);
        recordingState.setPadding(0, dp(6), 0, dp(8));
        controlCard.addView(recordingState, matchWrap());
        LinearLayout controls = row();
        startButton = button(R.string.start_recording);
        startButton.setOnClickListener(v -> startRecording());
        pauseButton = button(R.string.pause);
        pauseButton.setOnClickListener(v -> togglePause());
        stopButton = button(R.string.stop);
        stopButton.setOnClickListener(v -> stopRecording(true));
        controls.addView(startButton, weighted());
        controls.addView(pauseButton, weighted());
        controls.addView(stopButton, weighted());
        controlCard.addView(controls, matchWrap());
        root.addView(controlCard, spaced());

        root.addView(text(getString(R.string.recordings), 18, Color.rgb(105, 216, 255)), spaced());
        recordingList = new LinearLayout(this);
        recordingList.setOrientation(LinearLayout.VERTICAL);
        root.addView(recordingList, matchWrap());

        TextView footer = text(getString(R.string.footer), 12, Color.rgb(140, 160, 181));
        footer.setPadding(0, dp(16), 0, 0);
        footer.setOnClickListener(v -> openGitHub());
        root.addView(footer, matchWrap());
        return scroll;
    }

    private boolean hasAudioPermission() {
        return checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
    }

    private boolean microphoneMuted() {
        return audioManager != null && audioManager.isMicrophoneMute();
    }

    private void refreshMicrophoneState() {
        boolean granted = hasAudioPermission();
        String permission = getString(granted ? R.string.permission_granted : R.string.permission_missing);
        String microphone = getString(microphoneMuted() ? R.string.mic_muted : R.string.mic_available);
        microphoneState.setText(getString(R.string.microphone_status, permission, microphone));
    }

    private void startRecording() {
        refreshMicrophoneState();
        if (!hasAudioPermission()) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, AUDIO_PERMISSION_REQUEST);
            return;
        }
        if (!RecorderPolicy.canRecord(true, microphoneMuted())) {
            Toast.makeText(this, R.string.microphone_muted_block, Toast.LENGTH_SHORT).show();
            return;
        }
        stopPlayback();
        File directory = new File(getFilesDir(), "recordings");
        if (!directory.isDirectory() && !directory.mkdirs()) {
            Toast.makeText(this, R.string.recording_failed, Toast.LENGTH_LONG).show();
            return;
        }
        activeRecording = new File(directory, RecorderPolicy.recordingFileName(System.currentTimeMillis()));
        MediaRecorder candidate = null;
        try {
            candidate = new MediaRecorder(this);
            candidate.setAudioSource(MediaRecorder.AudioSource.MIC);
            candidate.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            candidate.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            candidate.setAudioSamplingRate(44100);
            candidate.setAudioEncodingBitRate(128000);
            candidate.setOutputFile(activeRecording.getAbsolutePath());
            candidate.prepare();
            candidate.start();
            recorder = candidate;
            recordingPaused = false;
            recordingState.setText(R.string.state_recording);
            Toast.makeText(this, R.string.recording_started, Toast.LENGTH_SHORT).show();
        } catch (IOException | RuntimeException error) {
            if (candidate != null) candidate.release();
            recorder = null;
            if (activeRecording != null) activeRecording.delete();
            activeRecording = null;
            Toast.makeText(this, R.string.recording_failed, Toast.LENGTH_LONG).show();
        }
        refreshControls();
    }

    private void togglePause() {
        if (recorder == null) return;
        try {
            if (recordingPaused) {
                recorder.resume();
                recordingPaused = false;
                recordingState.setText(R.string.state_recording);
            } else {
                recorder.pause();
                recordingPaused = true;
                recordingState.setText(R.string.state_paused);
            }
            pauseButton.setText(recordingPaused ? R.string.resume : R.string.pause);
        } catch (RuntimeException error) {
            Toast.makeText(this, R.string.recording_failed, Toast.LENGTH_LONG).show();
            stopRecording(false);
        }
    }

    private void stopRecording(boolean ownerRequested) {
        if (recorder == null) return;
        File completed = activeRecording;
        boolean valid = true;
        try {
            recorder.stop();
        } catch (RuntimeException error) {
            valid = false;
        } finally {
            recorder.release();
            recorder = null;
            activeRecording = null;
            recordingPaused = false;
        }
        if (!valid || completed == null || !RecorderPolicy.canExport(completed.length())) {
            if (completed != null) completed.delete();
            if (ownerRequested) Toast.makeText(this, R.string.recording_failed, Toast.LENGTH_LONG).show();
        } else if (ownerRequested) {
            Toast.makeText(this, R.string.recording_stopped, Toast.LENGTH_SHORT).show();
        }
        recordingState.setText(R.string.state_idle);
        refreshControls();
        refreshRecordings();
    }

    private void refreshControls() {
        boolean active = recorder != null;
        if (startButton != null) startButton.setEnabled(!active);
        if (pauseButton != null) {
            pauseButton.setEnabled(active);
            pauseButton.setText(recordingPaused ? R.string.resume : R.string.pause);
        }
        if (stopButton != null) stopButton.setEnabled(active);
    }

    private void refreshRecordings() {
        if (recordingList == null) return;
        recordingList.removeAllViews();
        File directory = new File(getFilesDir(), "recordings");
        File[] files = directory.listFiles(file -> file.isFile() && RecorderPolicy.isRecordingFile(file.getName()));
        if (files == null || files.length == 0) {
            recordingList.addView(text(getString(R.string.empty), 14, Color.rgb(180, 198, 217)), spaced());
            return;
        }
        Arrays.sort(files, Comparator.comparingLong(File::lastModified).reversed());
        int shown = 0;
        for (File file : files) {
            if (activeRecording != null && activeRecording.equals(file)) continue;
            recordingList.addView(recordingCard(file), spaced());
            if (++shown >= MAX_LIST_ITEMS) break;
        }
        if (shown == 0) recordingList.addView(text(getString(R.string.empty), 14, Color.rgb(180, 198, 217)), spaced());
    }

    private View recordingCard(File file) {
        LinearLayout card = card();
        card.addView(text(file.getName(), 15, Color.WHITE), matchWrap());
        Locale locale = getResources().getConfiguration().getLocales().get(0);
        DateFormat format = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT, locale);
        card.addView(text(getString(R.string.recording_meta, format.format(new Date(file.lastModified())), android.text.format.Formatter.formatShortFileSize(this, file.length())), 13, Color.rgb(180, 198, 217)), matchWrap());
        LinearLayout actions = row();
        Button play = button(R.string.play);
        play.setOnClickListener(v -> play(file));
        Button export = button(R.string.export);
        export.setOnClickListener(v -> export(file));
        Button delete = button(R.string.delete);
        delete.setOnClickListener(v -> confirmDelete(file));
        actions.addView(play, weighted());
        actions.addView(export, weighted());
        actions.addView(delete, weighted());
        card.addView(actions, matchWrap());
        return card;
    }

    private void play(File file) {
        stopPlayback();
        if (!RecorderPolicy.canExport(file.length())) {
            Toast.makeText(this, R.string.invalid_recording, Toast.LENGTH_SHORT).show();
            return;
        }
        MediaPlayer candidate = new MediaPlayer();
        try {
            candidate.setDataSource(file.getAbsolutePath());
            candidate.setOnCompletionListener(value -> stopPlayback());
            candidate.prepare();
            candidate.start();
            player = candidate;
        } catch (IOException | RuntimeException error) {
            candidate.release();
            Toast.makeText(this, R.string.playback_failed, Toast.LENGTH_SHORT).show();
        }
    }

    private void stopPlayback() {
        if (player != null) {
            try { if (player.isPlaying()) player.stop(); } catch (RuntimeException ignored) {}
            player.release();
            player = null;
        }
    }

    private void export(File file) {
        if (!RecorderPolicy.canExport(file.length())) {
            Toast.makeText(this, R.string.invalid_recording, Toast.LENGTH_SHORT).show();
            return;
        }
        pendingExport = file;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("audio/mp4")
                .putExtra(Intent.EXTRA_TITLE, file.getName());
        if (intent.resolveActivity(getPackageManager()) != null) startActivityForResult(intent, EXPORT_REQUEST);
        else {
            pendingExport = null;
            Toast.makeText(this, R.string.export_failed, Toast.LENGTH_SHORT).show();
        }
    }

    private void confirmDelete(File file) {
        new AlertDialog.Builder(this)
                .setTitle(R.string.delete_title)
                .setMessage(R.string.delete_body)
                .setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.delete_confirm, (dialog, which) -> {
                    stopPlayback();
                    if (!file.delete()) Toast.makeText(this, R.string.delete_failed, Toast.LENGTH_SHORT).show();
                    refreshRecordings();
                })
                .show();
    }

    private void openGitHub() {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/Swir"));
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private LinearLayout card() {
        LinearLayout value = new LinearLayout(this);
        value.setOrientation(LinearLayout.VERTICAL);
        value.setPadding(dp(14), dp(14), dp(14), dp(14));
        value.setBackgroundColor(Color.rgb(13, 34, 55));
        return value;
    }

    private LinearLayout row() {
        LinearLayout value = new LinearLayout(this);
        value.setOrientation(LinearLayout.HORIZONTAL);
        return value;
    }

    private Button button(int label) {
        Button value = new Button(this);
        value.setAllCaps(false);
        value.setText(label);
        value.setTextColor(Color.WHITE);
        value.setBackgroundColor(Color.rgb(17, 61, 92));
        value.setMinHeight(dp(48));
        return value;
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams spaced() {
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, 0, 0, dp(12));
        return params;
    }

    private LinearLayout.LayoutParams weighted() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        params.setMargins(dp(3), dp(6), dp(3), 0);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
