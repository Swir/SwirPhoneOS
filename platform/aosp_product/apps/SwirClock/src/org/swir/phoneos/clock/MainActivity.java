package org.swir.phoneos.clock;

import android.app.Activity;
import android.content.Intent;
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
    private static final String PREFS = "swir_clock_preferences";
    private static final String KEY_WORLD_ZONE = "world_zone_index";
    private static final String STATE_STOPWATCH_ACCUMULATED = "stopwatch_accumulated";
    private static final String STATE_STOPWATCH_STARTED_ELAPSED = "stopwatch_started_elapsed";
    private static final String STATE_STOPWATCH_STARTED_WALL = "stopwatch_started_wall";
    private static final String STATE_STOPWATCH_RUNNING = "stopwatch_running";
    private static final String STATE_TIMER_DURATION = "timer_duration";
    private static final String STATE_TIMER_STARTED_ELAPSED = "timer_started_elapsed";
    private static final String STATE_TIMER_STARTED_WALL = "timer_started_wall";
    private static final String STATE_TIMER_RUNNING = "timer_running";

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
    private long stopwatchStartedWall;
    private boolean stopwatchRunning;
    private long timerDuration;
    private long timerStartedAt;
    private long timerStartedWall;
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
        worldZoneIndex = ClockCore.safeWorldZoneIndex(
                getSharedPreferences(PREFS, MODE_PRIVATE).getInt(KEY_WORLD_ZONE, 0));
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_surface));
        setContentView(buildUi());
        restoreSessionState(state);
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

    @Override protected void onSaveInstanceState(Bundle outState) {
        outState.putLong(STATE_STOPWATCH_ACCUMULATED, stopwatchAccumulated);
        outState.putLong(STATE_STOPWATCH_STARTED_ELAPSED, stopwatchStartedAt);
        outState.putLong(STATE_STOPWATCH_STARTED_WALL, stopwatchStartedWall);
        outState.putBoolean(STATE_STOPWATCH_RUNNING, stopwatchRunning);
        outState.putLong(STATE_TIMER_DURATION, timerDuration);
        outState.putLong(STATE_TIMER_STARTED_ELAPSED, timerStartedAt);
        outState.putLong(STATE_TIMER_STARTED_WALL, timerStartedWall);
        outState.putBoolean(STATE_TIMER_RUNNING, timerRunning);
        super.onSaveInstanceState(outState);
    }

    private View buildUi() {
        int spaceXs = getResources().getDimensionPixelSize(R.dimen.swir_space_xs);
        int spaceSm = getResources().getDimensionPixelSize(R.dimen.swir_space_sm);
        int spaceMd = getResources().getDimensionPixelSize(R.dimen.swir_space_md);
        int spaceLg = getResources().getDimensionPixelSize(R.dimen.swir_space_lg);

        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(spaceMd, spaceMd, spaceMd, spaceLg);
        root.setBackgroundColor(getColor(R.color.swir_background));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        root.addView(text(getString(R.string.app_name), 28, getColor(R.color.swir_text_primary)), matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, spaceXs, 0, spaceMd);
        root.addView(subtitle, matchWrap());

        LinearLayout nowCard = card();
        nowCard.addView(text(getString(R.string.now), 13, getColor(R.color.swir_accent_cyan)), matchWrap());
        localTime = text(getString(R.string.clock_placeholder), 44, getColor(R.color.swir_text_primary));
        localTime.setGravity(Gravity.CENTER_HORIZONTAL);
        nowCard.addView(localTime, matchWrap());
        localDate = text("", 15, getColor(R.color.swir_text_secondary));
        localDate.setGravity(Gravity.CENTER_HORIZONTAL);
        nowCard.addView(localDate, matchWrap());
        root.addView(nowCard, spaced());

        LinearLayout worldCard = card();
        worldCard.addView(text(getString(R.string.world_clock), 17, getColor(R.color.swir_accent_cyan)), matchWrap());
        worldTime = text(getString(R.string.clock_placeholder), 34, getColor(R.color.swir_text_primary));
        worldTime.setGravity(Gravity.CENTER_HORIZONTAL);
        worldTime.setPadding(0, spaceXs, 0, spaceSm);
        worldCard.addView(worldTime, matchWrap());
        worldZoneButton = button(R.string.world_clock);
        worldZoneButton.setContentDescription(getString(R.string.next_zone_description));
        worldZoneButton.setOnClickListener(v -> {
            worldZoneIndex = ClockCore.nextWorldZoneIndex(worldZoneIndex);
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putInt(KEY_WORLD_ZONE, worldZoneIndex).apply();
            renderTimes();
        });
        worldCard.addView(worldZoneButton, matchWrap());
        root.addView(worldCard, spaced());

        LinearLayout stopwatchCard = card();
        stopwatchCard.addView(text(getString(R.string.stopwatch), 17, getColor(R.color.swir_accent_cyan)), matchWrap());
        stopwatchText = text(getString(R.string.duration_zero), 34, getColor(R.color.swir_text_primary));
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
        timerCard.addView(text(getString(R.string.timer), 17, getColor(R.color.swir_accent_cyan)), matchWrap());
        timerText = text(getString(R.string.duration_zero), 34, getColor(R.color.swir_text_primary));
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
        alarmCard.addView(text(getString(R.string.alarm), 17, getColor(R.color.swir_accent_cyan)), matchWrap());
        TextView alarmBody = text(getString(R.string.alarm_body), 14, getColor(R.color.swir_text_secondary));
        alarmBody.setPadding(0, spaceXs, 0, spaceSm);
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

    private void restoreSessionState(Bundle state) {
        if (state == null) return;
        long nowElapsed = SystemClock.elapsedRealtime();
        long nowWall = System.currentTimeMillis();

        stopwatchAccumulated = ClockCore.stopwatchElapsed(
                Math.max(0L, state.getLong(STATE_STOPWATCH_ACCUMULATED, 0L)), 0L, 0L, false);
        long savedStopwatchElapsed = state.getLong(STATE_STOPWATCH_STARTED_ELAPSED, -1L);
        long savedStopwatchWall = state.getLong(STATE_STOPWATCH_STARTED_WALL, -1L);
        boolean savedStopwatchRunning = state.getBoolean(STATE_STOPWATCH_RUNNING, false);
        if (savedStopwatchRunning && ClockCore.canRestoreElapsedSession(
                savedStopwatchElapsed, savedStopwatchWall, nowElapsed, nowWall)) {
            stopwatchStartedAt = savedStopwatchElapsed;
            stopwatchStartedWall = savedStopwatchWall;
            stopwatchRunning = true;
            stopwatchToggle.setText(R.string.pause);
        } else {
            stopwatchStartedAt = nowElapsed;
            stopwatchStartedWall = nowWall;
            stopwatchRunning = false;
            stopwatchToggle.setText(R.string.start);
        }

        long savedTimerDuration = state.getLong(STATE_TIMER_DURATION, 0L);
        long savedTimerElapsed = state.getLong(STATE_TIMER_STARTED_ELAPSED, -1L);
        long savedTimerWall = state.getLong(STATE_TIMER_STARTED_WALL, -1L);
        boolean savedTimerRunning = state.getBoolean(STATE_TIMER_RUNNING, false);
        long restoredRemaining = savedTimerRunning
                ? ClockCore.restoredTimerRemaining(
                        savedTimerDuration, savedTimerElapsed, savedTimerWall, nowElapsed, nowWall)
                : -1L;
        if (restoredRemaining > 0L) {
            timerDuration = savedTimerDuration;
            timerStartedAt = savedTimerElapsed;
            timerStartedWall = savedTimerWall;
            timerRunning = true;
        } else {
            timerDuration = 0L;
            timerStartedAt = 0L;
            timerStartedWall = 0L;
            timerRunning = false;
        }
        renderStopwatch();
        renderTimer();
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
        long nowElapsed = SystemClock.elapsedRealtime();
        long nowWall = System.currentTimeMillis();
        if (stopwatchRunning) {
            stopwatchAccumulated = ClockCore.stopwatchElapsed(stopwatchAccumulated, stopwatchStartedAt, nowElapsed, true);
            stopwatchRunning = false;
            stopwatchStartedAt = nowElapsed;
            stopwatchStartedWall = nowWall;
            stopwatchToggle.setText(R.string.start);
        } else {
            stopwatchStartedAt = nowElapsed;
            stopwatchStartedWall = nowWall;
            stopwatchRunning = true;
            stopwatchToggle.setText(R.string.pause);
        }
        renderStopwatch();
    }

    private void resetStopwatch() {
        stopwatchAccumulated = 0L;
        stopwatchStartedAt = SystemClock.elapsedRealtime();
        stopwatchStartedWall = System.currentTimeMillis();
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
        timerStartedWall = System.currentTimeMillis();
        timerRunning = true;
        renderTimer();
    }

    private void cancelTimer() {
        timerRunning = false;
        timerDuration = 0L;
        timerStartedAt = 0L;
        timerStartedWall = 0L;
        timerText.setText(R.string.duration_zero);
    }

    private void renderTimer() {
        if (!timerRunning) return;
        long remaining = ClockCore.timerRemaining(timerDuration, timerStartedAt, SystemClock.elapsedRealtime());
        timerText.setText(ClockCore.formatDuration(remaining));
        if (remaining == 0L) {
            timerRunning = false;
            timerDuration = 0L;
            timerStartedAt = 0L;
            timerStartedWall = 0L;
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
        int spaceMd = getResources().getDimensionPixelSize(R.dimen.swir_space_md);
        LinearLayout value = new LinearLayout(this);
        value.setOrientation(LinearLayout.VERTICAL);
        value.setPadding(spaceMd, spaceMd, spaceMd, spaceMd);
        value.setBackgroundColor(getColor(R.color.swir_surface));
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
        value.setTextColor(getColor(R.color.swir_text_primary));
        value.setBackgroundColor(getColor(R.color.swir_surface_alt));
        value.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        return value;
    }

    private EditText input(int hint) {
        EditText value = new EditText(this);
        value.setHint(hint);
        value.setHintTextColor(getColor(R.color.swir_text_secondary));
        value.setTextColor(getColor(R.color.swir_text_primary));
        value.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
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
        params.setMargins(0, 0, 0, getResources().getDimensionPixelSize(R.dimen.swir_space_md));
        return params;
    }

    private LinearLayout.LayoutParams weighted() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        int margin = getResources().getDimensionPixelSize(R.dimen.swir_space_xs);
        params.setMargins(margin, getResources().getDimensionPixelSize(R.dimen.swir_space_sm), margin, 0);
        return params;
    }
}
