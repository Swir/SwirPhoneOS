package org.swir.phoneos.clock;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.AlarmClock;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.FormatStyle;
import java.util.Locale;

/** Permission-minimal daily clock with world time, foreground timer/stopwatch and explicit alarm hand-off. */
public final class MainActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private TextView localTime;
    private TextView localDate;
    private TextView worldTime;
    private Button worldZoneButton;
    private TextView stopwatchText;
    private TextView timerText;
    private EditText timerMinutes;
    private EditText alarmHour;
    private EditText alarmMinute;
    private Button stopwatchToggle;
    private int worldZoneIndex;
    private long stopwatchAccumulated;
    private long stopwatchStartedAt;
    private boolean stopwatchRunning;
    private long timerDuration;
    private long timerStartedAt;
    private boolean timerRunning;

    private final Runnable ticker = new Runnable() {
        @Override public void run() {
            renderTimes();
            renderStopwatch();
            renderTimer();
            handler.postDelayed(this, 250L);
        }
    };

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(4, 11, 23));
        getWindow().setNavigationBarColor(Color.rgb(4, 11, 23));
        setContentView(buildUi());
    }

    @Override protected void onStart() {
        super.onStart();
        handler.removeCallbacks(ticker);
        handler.post(ticker);
    }

    @Override protected void onStop() {
        handler.removeCallbacks(ticker);
        super.onStop();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(24));
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        root.addView(text(getString(R.string.app_name), 28, Color.rgb(105, 216, 255)), matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, Color.rgb(180, 198, 217));
        subtitle.setPadding(0, dp(4), 0, dp(16));
        root.addView(subtitle, matchWrap());

        LinearLayout nowCard = card();
        nowCard.addView(text(getString(R.string.now), 13, Color.rgb(105, 216, 255)), matchWrap());
        localTime = text(getString(R.string.clock_placeholder), 44, Color.WHITE);
        localTime.setGravity(Gravity.CENTER_HORIZONTAL);
        nowCard.addView(localTime, matchWrap());
        localDate = text("", 15, Color.rgb(180, 198, 217));
        localDate.setGravity(Gravity.CENTER_HORIZONTAL);
        nowCard.addView(localDate, matchWrap());
        root.addView(nowCard, spaced());

        LinearLayout worldCard = card();
        worldCard.addView(text(getString(R.string.world_clock), 17, Color.rgb(105, 216, 255)), matchWrap());
        worldTime = text(getString(R.string.clock_placeholder), 34, Color.WHITE);
        worldTime.setGravity(Gravity.CENTER_HORIZONTAL);
        worldTime.setPadding(0, dp(4), 0, dp(6));
        worldCard.addView(worldTime, matchWrap());
        worldZoneButton = button(R.string.world_clock);
        worldZoneButton.setContentDescription(getString(R.string.next_zone_description));
        worldZoneButton.setOnClickListener(v -> {
            worldZoneIndex = ClockCore.nextWorldZoneIndex(worldZoneIndex);
            renderTimes();
        });
        worldCard.addView(worldZoneButton, matchWrap());
        root.addView(worldCard, spaced());

        LinearLayout stopwatchCard = card();
        stopwatchCard.addView(text(getString(R.string.stopwatch), 17, Color.rgb(105, 216, 255)), matchWrap());
        stopwatchText = text(getString(R.string.duration_zero), 34, Color.WHITE);
        stopwatchText.setGravity(Gravity.CENTER_HORIZONTAL);
        stopwatchCard.addView(stopwatchText, matchWrap());
        LinearLayout stopwatchButtons = row();
        stopwatchToggle = button(R.string.start);
        stopwatchToggle.setOnClickListener(v -> toggleStopwatch());
        Button reset = button(R.string.reset);
        reset.setOnClickListener(v -> resetStopwatch());
        stopwatchButtons.addView(stopwatchToggle, weighted());
        stopwatchButtons.addView(reset, weighted());
        stopwatchCard.addView(stopwatchButtons, matchWrap());
        root.addView(stopwatchCard, spaced());

        LinearLayout timerCard = card();
        timerCard.addView(text(getString(R.string.timer), 17, Color.rgb(105, 216, 255)), matchWrap());
        timerText = text(getString(R.string.duration_zero), 34, Color.WHITE);
        timerText.setGravity(Gravity.CENTER_HORIZONTAL);
        timerCard.addView(timerText, matchWrap());
        timerMinutes = input(R.string.timer_minutes_hint);
        timerMinutes.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        timerCard.addView(timerMinutes, matchWrap());
        LinearLayout timerButtons = row();
        Button timerStart = button(R.string.start_timer);
        timerStart.setOnClickListener(v -> startTimer());
        Button timerCancel = button(R.string.cancel);
        timerCancel.setOnClickListener(v -> cancelTimer());
        timerButtons.addView(timerStart, weighted());
        timerButtons.addView(timerCancel, weighted());
        timerCard.addView(timerButtons, matchWrap());
        root.addView(timerCard, spaced());

        LinearLayout alarmCard = card();
        alarmCard.addView(text(getString(R.string.alarm), 17, Color.rgb(105, 216, 255)), matchWrap());
        TextView alarmBody = text(getString(R.string.alarm_body), 14, Color.rgb(180, 198, 217));
        alarmBody.setPadding(0, dp(4), 0, dp(8));
        alarmCard.addView(alarmBody, matchWrap());
        LinearLayout alarmInputs = row();
        alarmHour = input(R.string.hour_hint);
        alarmMinute = input(R.string.minute_hint);
        alarmHour.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        alarmMinute.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        alarmInputs.addView(alarmHour, weighted());
        alarmInputs.addView(alarmMinute, weighted());
        alarmCard.addView(alarmInputs, matchWrap());
        Button setAlarm = button(R.string.set_alarm);
        setAlarm.setOnClickListener(v -> handOffAlarm());
        alarmCard.addView(setAlarm, matchWrap());
        root.addView(alarmCard, spaced());
        return scroll;
    }

    private void renderTimes() {
        Locale locale = getResources().getConfiguration().getLocales().get(0);
        ZonedDateTime now = ZonedDateTime.now();
        long epochMillis = System.currentTimeMillis();
        localTime.setText(DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(locale).format(now));
        localDate.setText(DateTimeFormatter.ofLocalizedDate(FormatStyle.FULL).withLocale(locale).format(now));
        String zoneId = ClockCore.worldZoneId(worldZoneIndex);
        worldTime.setText(ClockCore.worldTime(zoneId, epochMillis, locale));
        worldZoneButton.setText(ClockCore.worldZoneLabel(zoneId, epochMillis, locale));
    }

    private void toggleStopwatch() {
        long now = SystemClock.elapsedRealtime();
        if (stopwatchRunning) {
            stopwatchAccumulated = ClockCore.stopwatchElapsed(stopwatchAccumulated, stopwatchStartedAt, now, true);
            stopwatchRunning = false;
            stopwatchToggle.setText(R.string.start);
        } else {
            stopwatchStartedAt = now;
            stopwatchRunning = true;
            stopwatchToggle.setText(R.string.pause);
        }
        renderStopwatch();
    }

    private void resetStopwatch() {
        stopwatchAccumulated = 0L;
        stopwatchStartedAt = SystemClock.elapsedRealtime();
        renderStopwatch();
    }

    private void renderStopwatch() {
        long elapsed = ClockCore.stopwatchElapsed(stopwatchAccumulated, stopwatchStartedAt, SystemClock.elapsedRealtime(), stopwatchRunning);
        stopwatchText.setText(ClockCore.formatDuration(elapsed));
    }

    private void startTimer() {
        long duration = ClockCore.timerMillis(timerMinutes.getText().toString());
        if (duration < 0L) {
            Toast.makeText(this, R.string.invalid_timer, Toast.LENGTH_SHORT).show();
            return;
        }
        timerDuration = duration;
        timerStartedAt = SystemClock.elapsedRealtime();
        timerRunning = true;
        renderTimer();
    }

    private void cancelTimer() {
        timerRunning = false;
        timerDuration = 0L;
        timerStartedAt = 0L;
        timerText.setText(R.string.duration_zero);
    }

    private void renderTimer() {
        if (!timerRunning) return;
        long remaining = ClockCore.timerRemaining(timerDuration, timerStartedAt, SystemClock.elapsedRealtime());
        timerText.setText(ClockCore.formatDuration(remaining));
        if (remaining == 0L) {
            timerRunning = false;
            Toast.makeText(this, R.string.timer_finished, Toast.LENGTH_LONG).show();
        }
    }

    private void handOffAlarm() {
        int hour = parseInt(alarmHour.getText().toString());
        int minute = parseInt(alarmMinute.getText().toString());
        if (!ClockCore.validAlarmTime(hour, minute)) {
            Toast.makeText(this, R.string.invalid_alarm, Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(AlarmClock.ACTION_SET_ALARM)
                .putExtra(AlarmClock.EXTRA_HOUR, hour)
                .putExtra(AlarmClock.EXTRA_MINUTES, minute)
                .putExtra(AlarmClock.EXTRA_MESSAGE, getString(R.string.alarm_message))
                .putExtra(AlarmClock.EXTRA_SKIP_UI, false);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.alarm_unavailable, Toast.LENGTH_SHORT).show();
    }

    private int parseInt(String value) {
        try { return Integer.parseInt(value.trim()); }
        catch (RuntimeException ignored) { return -1; }
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

    private EditText input(int hint) {
        EditText value = new EditText(this);
        value.setHint(hint);
        value.setHintTextColor(Color.rgb(140, 160, 181));
        value.setTextColor(Color.WHITE);
        value.setSingleLine(true);
        value.setContentDescription(getString(hint));
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
