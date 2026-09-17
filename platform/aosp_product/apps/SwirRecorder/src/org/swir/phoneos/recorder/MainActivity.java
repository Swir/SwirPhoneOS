package org.swir.phoneos.recorder;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.media.MediaPlayer;
import android.media.MediaRecorder;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.OutputStream;

public final class MainActivity extends Activity {
    private static final int REQUEST_MIC = 41;
    private static final int REQUEST_EXPORT = 42;
    private static final int BG = Color.rgb(7, 14, 24);
    private static final int PANEL = Color.rgb(15, 29, 44);
    private static final int ACCENT = Color.rgb(64, 211, 255);
    private static final int RECORD = Color.rgb(255, 87, 116);

    private final Handler timer = new Handler(Looper.getMainLooper());
    private MediaRecorder recorder;
    private MediaPlayer player;
    private File currentFile;
    private RecorderPolicy.State state = RecorderPolicy.State.IDLE;
    private long recordingStartedAt;
    private TextView status;
    private TextView duration;
    private Button recordButton;
    private Button playButton;
    private Button exportButton;
    private Button deleteButton;
    private boolean startAfterPermission;

    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (state == RecorderPolicy.State.RECORDING) {
                duration.setText(getString(R.string.duration_value, RecorderPolicy.formatDuration(System.currentTimeMillis() - recordingStartedAt)));
                timer.postDelayed(this, 250L);
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        setContentView(buildUi());
        render();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(dp(22), dp(24), dp(22), dp(24));
        root.setBackgroundColor(BG);

        TextView title = text(R.string.title, 30, Color.WHITE);
        title.setTypeface(title.getTypeface(), 1);
        root.addView(title, fullWrap());
        TextView subtitle = text(R.string.subtitle, 14, Color.LTGRAY);
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, dp(6), 0, dp(28));
        root.addView(subtitle, fullWrap());

        status = text(R.string.status_idle, 18, ACCENT);
        status.setGravity(Gravity.CENTER);
        root.addView(status, fullWrap());
        duration = text(R.string.duration_zero, 42, Color.WHITE);
        duration.setGravity(Gravity.CENTER);
        duration.setPadding(0, dp(12), 0, dp(24));
        root.addView(duration, fullWrap());

        recordButton = button(R.string.start_recording, RECORD);
        recordButton.setOnClickListener(v -> onRecordPressed());
        root.addView(recordButton, new LinearLayout.LayoutParams(-1, dp(58)));

        LinearLayout row = new LinearLayout(this);
        row.setPadding(0, dp(12), 0, 0);
        playButton = button(R.string.play, PANEL);
        playButton.setOnClickListener(v -> onPlayPressed());
        exportButton = button(R.string.export, PANEL);
        exportButton.setOnClickListener(v -> exportRecording());
        deleteButton = button(R.string.delete, PANEL);
        deleteButton.setOnClickListener(v -> confirmDelete());
        for (Button b : new Button[]{playButton, exportButton, deleteButton}) row.addView(b, new LinearLayout.LayoutParams(0, dp(52), 1f));
        root.addView(row, new LinearLayout.LayoutParams(-1, -2));

        TextView privacy = text(R.string.privacy_note, 12, Color.GRAY);
        privacy.setGravity(Gravity.CENTER);
        privacy.setPadding(dp(8), dp(24), dp(8), 0);
        root.addView(privacy, fullWrap());
        return root;
    }

    private void onRecordPressed() {
        if (state == RecorderPolicy.State.RECORDING) {
            stopRecording();
            return;
        }
        if (state == RecorderPolicy.State.PLAYING) stopPlayback();
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            startAfterPermission = true;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_MIC);
            return;
        }
        startRecording();
    }

    private void startRecording() {
        releaseRecorder();
        currentFile = new File(getFilesDir(), RecorderPolicy.recordingFileName(System.currentTimeMillis()));
        try {
            recorder = new MediaRecorder(this);
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioSamplingRate(44100);
            recorder.setAudioEncodingBitRate(128000);
            recorder.setOutputFile(currentFile.getAbsolutePath());
            recorder.prepare();
            recorder.start();
            recordingStartedAt = System.currentTimeMillis();
            state = RecorderPolicy.State.RECORDING;
            timer.removeCallbacks(tick);
            timer.post(tick);
            render();
        } catch (IOException | RuntimeException exc) {
            releaseRecorder();
            if (currentFile != null) currentFile.delete();
            currentFile = null;
            state = RecorderPolicy.State.IDLE;
            render();
            Toast.makeText(this, R.string.recording_failed, Toast.LENGTH_LONG).show();
        }
    }

    private void stopRecording() {
        boolean saved = false;
        try {
            if (recorder != null) {
                recorder.stop();
                saved = currentFile != null && RecorderPolicy.exportable(currentFile.length());
            }
        } catch (RuntimeException exc) {
            if (currentFile != null) currentFile.delete();
        } finally {
            releaseRecorder();
            timer.removeCallbacks(tick);
        }
        if (saved) {
            state = RecorderPolicy.State.READY;
            duration.setText(getString(R.string.duration_value, RecorderPolicy.formatDuration(System.currentTimeMillis() - recordingStartedAt)));
            Toast.makeText(this, R.string.saved, Toast.LENGTH_SHORT).show();
        } else {
            currentFile = null;
            state = RecorderPolicy.State.IDLE;
            Toast.makeText(this, R.string.recording_failed, Toast.LENGTH_LONG).show();
        }
        render();
    }

    private void onPlayPressed() {
        if (state == RecorderPolicy.State.PLAYING) {
            stopPlayback();
            return;
        }
        if (currentFile == null || !RecorderPolicy.exportable(currentFile.length())) {
            Toast.makeText(this, R.string.no_recording, Toast.LENGTH_SHORT).show();
            return;
        }
        try {
            releasePlayer();
            player = new MediaPlayer();
            player.setDataSource(currentFile.getAbsolutePath());
            player.setOnCompletionListener(mp -> stopPlayback());
            player.prepare();
            player.start();
            state = RecorderPolicy.State.PLAYING;
            render();
        } catch (IOException | RuntimeException exc) {
            releasePlayer();
            state = RecorderPolicy.State.READY;
            render();
            Toast.makeText(this, R.string.playback_failed, Toast.LENGTH_LONG).show();
        }
    }

    private void stopPlayback() {
        releasePlayer();
        state = currentFile != null && RecorderPolicy.exportable(currentFile.length()) ? RecorderPolicy.State.READY : RecorderPolicy.State.IDLE;
        render();
    }

    private void exportRecording() {
        if (currentFile == null || !RecorderPolicy.exportable(currentFile.length())) {
            Toast.makeText(this, R.string.no_recording, Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("audio/mp4");
        intent.putExtra(Intent.EXTRA_TITLE, currentFile.getName());
        startActivityForResult(intent, REQUEST_EXPORT);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_EXPORT || resultCode != RESULT_OK || data == null || data.getData() == null || currentFile == null) return;
        Uri target = data.getData();
        try (FileInputStream input = new FileInputStream(currentFile); OutputStream output = getContentResolver().openOutputStream(target, "w")) {
            if (output == null) throw new IOException("no output stream");
            byte[] buffer = new byte[64 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            output.flush();
            Toast.makeText(this, R.string.export_success, Toast.LENGTH_SHORT).show();
        } catch (IOException exc) {
            Toast.makeText(this, R.string.export_failed, Toast.LENGTH_LONG).show();
        }
    }

    private void confirmDelete() {
        if (currentFile == null) return;
        new AlertDialog.Builder(this)
            .setTitle(R.string.delete_title)
            .setMessage(R.string.delete_message)
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.delete_confirm, (dialog, which) -> deleteRecording())
            .show();
    }

    private void deleteRecording() {
        if (state == RecorderPolicy.State.PLAYING) stopPlayback();
        if (state == RecorderPolicy.State.RECORDING) return;
        if (currentFile != null) currentFile.delete();
        currentFile = null;
        state = RecorderPolicy.State.IDLE;
        duration.setText(R.string.duration_zero);
        render();
    }

    private void render() {
        boolean recording = state == RecorderPolicy.State.RECORDING;
        boolean ready = currentFile != null && RecorderPolicy.exportable(currentFile.length());
        status.setText(recording ? R.string.status_recording : state == RecorderPolicy.State.PLAYING ? R.string.status_playing : ready ? R.string.status_ready : R.string.status_idle);
        recordButton.setText(recording ? R.string.stop_recording : R.string.start_recording);
        playButton.setText(state == RecorderPolicy.State.PLAYING ? R.string.stop_playback : R.string.play);
        playButton.setEnabled(ready);
        exportButton.setEnabled(ready && state != RecorderPolicy.State.PLAYING);
        deleteButton.setEnabled(ready && !recording);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQUEST_MIC) return;
        boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
        if (granted && startAfterPermission) startRecording();
        else if (!granted) Toast.makeText(this, R.string.microphone_permission_denied, Toast.LENGTH_LONG).show();
        startAfterPermission = false;
    }

    private void releaseRecorder() {
        if (recorder != null) {
            recorder.reset();
            recorder.release();
            recorder = null;
        }
    }

    private void releasePlayer() {
        if (player != null) {
            if (player.isPlaying()) player.stop();
            player.release();
            player = null;
        }
    }

    private Button button(int label, int color) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(color);
        button.setAllCaps(false);
        return button;
    }

    private TextView text(int value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams fullWrap() { return new LinearLayout.LayoutParams(-1, -2); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override
    protected void onDestroy() {
        timer.removeCallbacks(tick);
        if (state == RecorderPolicy.State.RECORDING) {
            try { recorder.stop(); } catch (RuntimeException ignored) { if (currentFile != null) currentFile.delete(); }
        }
        releaseRecorder();
        releasePlayer();
        super.onDestroy();
    }
}
