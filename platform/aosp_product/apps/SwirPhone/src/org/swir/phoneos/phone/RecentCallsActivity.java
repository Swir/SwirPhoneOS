package org.swir.phoneos.phone;

import android.Manifest;
import android.app.Activity;
import android.app.role.RoleManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.CallLog;
import android.telecom.TelecomManager;
import android.text.format.DateUtils;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class RecentCallsActivity extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private TextView statusView;
    private LinearLayout listView;
    private int loadGeneration;
    private volatile boolean destroyed;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        setContentView(buildUi());
    }

    @Override protected void onResume() {
        super.onResume();
        loadRecentCalls();
    }

    @Override protected void onDestroy() {
        destroyed = true;
        loadGeneration++;
        worker.shutdownNow();
        super.onDestroy();
    }

    private ScrollView buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int padding = dim(R.dimen.swir_space_lg);
        root.setPadding(padding, padding, padding, padding);
        root.setBackgroundColor(getColor(R.color.swir_background));
        scroll.addView(root, new ScrollView.LayoutParams(-1, -2));

        root.addView(text(getString(R.string.recent_calls_eyebrow), 13, getColor(R.color.swir_accent_cyan)), matchWrap());
        root.addView(text(getString(R.string.recent_calls_title), 30, getColor(R.color.swir_text_primary)), matchWrap());
        root.addView(text(getString(R.string.recent_calls_subtitle), 14, getColor(R.color.swir_text_secondary)), matchWrap());

        statusView = text("", 14, getColor(R.color.swir_text_secondary));
        LinearLayout.LayoutParams statusParams = matchWrap();
        statusParams.topMargin = dim(R.dimen.swir_space_md);
        root.addView(statusView, statusParams);

        listView = new LinearLayout(this);
        listView.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams listParams = matchWrap();
        listParams.topMargin = dim(R.dimen.swir_space_sm);
        root.addView(listView, listParams);
        return scroll;
    }

    private void loadRecentCalls() {
        listView.removeAllViews();
        if (!hasHistoryAccess()) {
            statusView.setText(R.string.recent_calls_access_required);
            return;
        }
        statusView.setText(R.string.recent_calls_loading);
        final int generation = ++loadGeneration;
        worker.execute(() -> {
            LoadResult result = queryRecentCalls();
            runOnUiThread(() -> {
                if (destroyed || generation != loadGeneration) return;
                render(result);
            });
        });
    }

    private boolean hasHistoryAccess() {
        RoleManager roleManager = getSystemService(RoleManager.class);
        boolean roleHeld = roleManager != null
                && roleManager.isRoleAvailable(RoleManager.ROLE_DIALER)
                && roleManager.isRoleHeld(RoleManager.ROLE_DIALER);
        return roleHeld && checkSelfPermission(Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED;
    }

    private LoadResult queryRecentCalls() {
        String[] projection = {
                CallLog.Calls.NUMBER,
                CallLog.Calls.NUMBER_PRESENTATION,
                CallLog.Calls.TYPE,
                CallLog.Calls.DATE,
                CallLog.Calls.DURATION
        };
        List<RecentCall> calls = new ArrayList<>();
        try (Cursor cursor = getContentResolver().query(
                CallLog.Calls.CONTENT_URI,
                projection,
                null,
                null,
                CallLog.Calls.DATE + " DESC")) {
            if (cursor == null) return LoadResult.failed();
            int numberIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.NUMBER);
            int presentationIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.NUMBER_PRESENTATION);
            int typeIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.TYPE);
            int dateIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.DATE);
            int durationIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.DURATION);
            while (cursor.moveToNext() && calls.size() < CallHistoryPolicy.MAX_ENTRIES) {
                int presentation = cursor.getInt(presentationIndex);
                String safeNumber = "";
                if (presentation == TelecomManager.PRESENTATION_ALLOWED) {
                    String rawNumber = cursor.getString(numberIndex);
                    safeNumber = CallHistoryPolicy.safeDialTarget(
                            presentation,
                            TelecomManager.PRESENTATION_ALLOWED,
                            rawNumber);
                }
                calls.add(new RecentCall(
                        safeNumber,
                        cursor.getInt(typeIndex),
                        cursor.getLong(dateIndex),
                        Math.max(0L, cursor.getLong(durationIndex))));
            }
            return LoadResult.success(calls);
        } catch (SecurityException | IllegalArgumentException | IllegalStateException exception) {
            return LoadResult.failed();
        }
    }

    private void render(LoadResult result) {
        listView.removeAllViews();
        if (!result.success) {
            statusView.setText(R.string.recent_calls_load_failed);
            return;
        }
        if (result.calls.isEmpty()) {
            statusView.setText(R.string.recent_calls_empty);
            return;
        }
        statusView.setText(getString(R.string.recent_calls_count_format, result.calls.size()));
        for (RecentCall call : result.calls) listView.addView(callRow(call));
    }

    private LinearLayout callRow(RecentCall call) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        int inset = dim(R.dimen.swir_space_md);
        row.setPadding(inset, inset, inset, inset);
        row.setBackgroundColor(getColor(R.color.swir_surface));

        String visibleNumber = call.number.isEmpty() ? getString(R.string.unknown_number) : call.number;
        row.addView(text(visibleNumber, 19, getColor(R.color.swir_text_primary)), matchWrap());

        String when = DateUtils.formatDateTime(
                this,
                call.dateMillis,
                DateUtils.FORMAT_SHOW_DATE | DateUtils.FORMAT_SHOW_TIME | DateUtils.FORMAT_ABBREV_MONTH);
        TextView meta = text(
                getString(R.string.recent_calls_meta_format, getString(directionLabel(call.type)), when),
                13,
                getColor(R.color.swir_text_secondary));
        row.addView(meta, matchWrap());

        if (call.durationSeconds > 0L) {
            row.addView(text(
                    getString(R.string.recent_calls_duration_format, DateUtils.formatElapsedTime(call.durationSeconds)),
                    13,
                    getColor(R.color.swir_text_secondary)), matchWrap());
        }

        if (!call.number.isEmpty()) {
            Button dialAgain = actionButton(R.string.recent_calls_dial_again);
            dialAgain.setOnClickListener(v -> openDialer(call.number));
            LinearLayout.LayoutParams dialParams = matchWrap();
            dialParams.topMargin = dim(R.dimen.swir_space_sm);
            row.addView(dialAgain, dialParams);
        }

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.bottomMargin = dim(R.dimen.swir_space_sm);
        row.setLayoutParams(params);
        return row;
    }

    private void openDialer(String safeNumber) {
        String normalized = DialerPolicy.normalize(safeNumber);
        if (normalized.isEmpty()) return;
        Intent intent = new Intent(Intent.ACTION_DIAL, Uri.fromParts("tel", normalized, null));
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private int directionLabel(int type) {
        switch (type) {
            case CallLog.Calls.INCOMING_TYPE: return R.string.call_history_incoming;
            case CallLog.Calls.OUTGOING_TYPE: return R.string.call_history_outgoing;
            case CallLog.Calls.MISSED_TYPE: return R.string.call_history_missed;
            case CallLog.Calls.REJECTED_TYPE: return R.string.call_history_rejected;
            case CallLog.Calls.BLOCKED_TYPE: return R.string.call_history_blocked;
            case CallLog.Calls.VOICEMAIL_TYPE: return R.string.call_history_voicemail;
            default: return R.string.call_history_unknown_direction;
        }
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        int vertical = dim(R.dimen.swir_space_xs);
        view.setPadding(0, vertical, 0, vertical);
        return view;
    }

    private Button actionButton(int textRes) {
        Button button = new Button(this);
        button.setText(textRes);
        button.setMinHeight(dim(R.dimen.swir_touch_min));
        return button;
    }

    private LinearLayout.LayoutParams matchWrap() { return new LinearLayout.LayoutParams(-1, -2); }
    private int dim(int id) { return getResources().getDimensionPixelSize(id); }

    private static final class RecentCall {
        final String number;
        final int type;
        final long dateMillis;
        final long durationSeconds;

        RecentCall(String number, int type, long dateMillis, long durationSeconds) {
            this.number = number;
            this.type = type;
            this.dateMillis = dateMillis;
            this.durationSeconds = durationSeconds;
        }
    }

    private static final class LoadResult {
        final boolean success;
        final List<RecentCall> calls;

        private LoadResult(boolean success, List<RecentCall> calls) {
            this.success = success;
            this.calls = calls;
        }

        static LoadResult success(List<RecentCall> calls) { return new LoadResult(true, calls); }
        static LoadResult failed() { return new LoadResult(false, new ArrayList<>()); }
    }
}
