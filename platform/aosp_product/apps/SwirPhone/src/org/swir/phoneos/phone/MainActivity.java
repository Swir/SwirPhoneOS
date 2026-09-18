package org.swir.phoneos.phone;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.role.RoleManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.CallLog;
import android.telecom.TelecomManager;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DateFormat;
import java.util.Date;

public final class MainActivity extends Activity {
    private static final int REQUEST_DIALER_ROLE = 7101;
    private static final int REQUEST_CALL_LOG = 7102;

    private EditText number;
    private Button dial;
    private Button roleButton;
    private Button activeCallButton;
    private Button recentCallsButton;
    private TextView roleStatus;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        setContentView(buildUi());
        refreshDialState();
        refreshPhoneRoleState();
    }

    @Override protected void onResume() {
        super.onResume();
        refreshPhoneRoleState();
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_DIALER_ROLE) refreshPhoneRoleState();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQUEST_CALL_LOG) return;
        if (grantResults.length == 1 && grantResults[0] == PackageManager.PERMISSION_GRANTED && isDefaultDialer()) {
            presentRecentCalls();
        } else {
            Toast.makeText(this, R.string.recent_calls_permission_denied, Toast.LENGTH_SHORT).show();
        }
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pagePadding = dim(R.dimen.swir_space_lg);
        root.setPadding(pagePadding, pagePadding, pagePadding, pagePadding);
        root.setBackgroundColor(getColor(R.color.swir_background));

        TextView eyebrow = text(getString(R.string.eyebrow), 13, getColor(R.color.swir_accent_cyan));
        root.addView(eyebrow, matchWrap());
        TextView title = text(getString(R.string.title), 30, getColor(R.color.swir_text_primary));
        root.addView(title, matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 15, getColor(R.color.swir_text_secondary));
        root.addView(subtitle, matchWrap());

        number = new EditText(this);
        number.setHint(R.string.number_hint);
        number.setTextColor(getColor(R.color.swir_text_primary));
        number.setHintTextColor(getColor(R.color.swir_text_secondary));
        number.setTextSize(28);
        number.setGravity(Gravity.CENTER_HORIZONTAL);
        number.setSingleLine(true);
        number.setInputType(InputType.TYPE_CLASS_PHONE);
        number.setContentDescription(getString(R.string.number_content_description));
        number.setMinHeight(dim(R.dimen.swir_touch_min));
        LinearLayout.LayoutParams numberParams = new LinearLayout.LayoutParams(-1, dp(64));
        numberParams.topMargin = dim(R.dimen.swir_space_lg);
        root.addView(number, numberParams);
        number.addTextChangedListener(new SimpleTextWatcher(this::refreshDialState));

        GridLayout keypad = new GridLayout(this);
        keypad.setColumnCount(3);
        keypad.setRowCount(4);
        String[] keys = getResources().getStringArray(R.array.dial_keys);
        for (String key : keys) keypad.addView(keyButton(key), gridCell());
        LinearLayout.LayoutParams keypadParams = new LinearLayout.LayoutParams(-1, 0, 1f);
        keypadParams.topMargin = dim(R.dimen.swir_space_md);
        root.addView(keypad, keypadParams);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setGravity(Gravity.CENTER);
        Button erase = actionButton(R.string.erase);
        erase.setOnClickListener(v -> number.setText(DialerPolicy.eraseLast(number.getText().toString())));
        erase.setOnLongClickListener(v -> { number.getText().clear(); return true; });
        actions.addView(erase, weighted());
        dial = actionButton(R.string.open_dialer);
        dial.setOnClickListener(v -> openSystemDialer());
        actions.addView(dial, weighted());
        root.addView(actions, matchWrap());

        roleStatus = text(getString(R.string.role_inactive), 13, getColor(R.color.swir_text_secondary));
        roleStatus.setGravity(Gravity.CENTER_HORIZONTAL);
        LinearLayout.LayoutParams roleStatusParams = matchWrap();
        roleStatusParams.topMargin = dim(R.dimen.swir_space_sm);
        root.addView(roleStatus, roleStatusParams);

        LinearLayout phoneActions = new LinearLayout(this);
        phoneActions.setOrientation(LinearLayout.VERTICAL);
        phoneActions.setGravity(Gravity.CENTER);
        roleButton = actionButton(R.string.request_default_phone);
        roleButton.setOnClickListener(v -> requestDefaultPhoneRole());
        phoneActions.addView(roleButton, matchWrap());
        activeCallButton = actionButton(R.string.open_active_call);
        activeCallButton.setOnClickListener(v -> openActiveCall());
        phoneActions.addView(activeCallButton, matchWrap());
        recentCallsButton = actionButton(R.string.open_recent_calls);
        recentCallsButton.setOnClickListener(v -> requestRecentCalls());
        phoneActions.addView(recentCallsButton, matchWrap());
        root.addView(phoneActions, matchWrap());

        TextView safety = text(getString(R.string.handoff_notice), 13, getColor(R.color.swir_text_secondary));
        safety.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(safety, matchWrap());
        return root;
    }

    private Button keyButton(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(24);
        button.setTextColor(getColor(R.color.swir_text_primary));
        button.setMinHeight(dim(R.dimen.swir_touch_min));
        button.setContentDescription(getString(R.string.key_content_description, label));
        button.setOnClickListener(v -> {
            String next = DialerPolicy.appendKey(number.getText().toString(), label.charAt(0));
            number.setText(next);
            number.setSelection(next.length());
        });
        return button;
    }

    private void openSystemDialer() {
        String normalized = DialerPolicy.normalize(number.getText().toString());
        if (normalized.isEmpty()) {
            Toast.makeText(this, R.string.invalid_number, Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(Intent.ACTION_DIAL, Uri.fromParts("tel", normalized, null));
        if (intent.resolveActivity(getPackageManager()) == null) {
            Toast.makeText(this, R.string.no_dialer, Toast.LENGTH_SHORT).show();
            return;
        }
        startActivity(intent);
    }

    private void requestDefaultPhoneRole() {
        RoleManager roleManager = getSystemService(RoleManager.class);
        if (roleManager == null || !roleManager.isRoleAvailable(RoleManager.ROLE_DIALER)) {
            Toast.makeText(this, R.string.role_unavailable, Toast.LENGTH_SHORT).show();
            return;
        }
        if (roleManager.isRoleHeld(RoleManager.ROLE_DIALER)) {
            refreshPhoneRoleState();
            return;
        }
        Intent request = roleManager.createRequestRoleIntent(RoleManager.ROLE_DIALER);
        startActivityForResult(request, REQUEST_DIALER_ROLE);
    }

    private void openActiveCall() {
        if (!SwirInCallService.hasActiveCall()) {
            Toast.makeText(this, R.string.no_active_call, Toast.LENGTH_SHORT).show();
            refreshPhoneRoleState();
            return;
        }
        startActivity(new Intent(this, InCallActivity.class));
    }

    private void requestRecentCalls() {
        if (!isDefaultDialer()) {
            Toast.makeText(this, R.string.recent_calls_role_required, Toast.LENGTH_SHORT).show();
            refreshPhoneRoleState();
            return;
        }
        if (checkSelfPermission(Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.READ_CALL_LOG}, REQUEST_CALL_LOG);
            return;
        }
        presentRecentCalls();
    }

    private void presentRecentCalls() {
        if (!isDefaultDialer() || checkSelfPermission(Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, R.string.recent_calls_permission_denied, Toast.LENGTH_SHORT).show();
            return;
        }
        String[] projection = {
            CallLog.Calls.NUMBER,
            CallLog.Calls.CACHED_NAME,
            CallLog.Calls.NUMBER_PRESENTATION,
            CallLog.Calls.TYPE,
            CallLog.Calls.DATE,
            CallLog.Calls.DURATION
        };
        StringBuilder rows = new StringBuilder();
        try (Cursor cursor = getContentResolver().query(
                CallLog.Calls.CONTENT_URI,
                projection,
                null,
                null,
                CallLog.Calls.DATE + " DESC")) {
            if (cursor != null) {
                int count = 0;
                int numberIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.NUMBER);
                int nameIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.CACHED_NAME);
                int presentationIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.NUMBER_PRESENTATION);
                int typeIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.TYPE);
                int dateIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.DATE);
                int durationIndex = cursor.getColumnIndexOrThrow(CallLog.Calls.DURATION);
                DateFormat dateFormat = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT);
                while (cursor.moveToNext() && count < CallHistoryPolicy.MAX_RECENT_CALLS) {
                    boolean presentationAllowed = cursor.getInt(presentationIndex) == TelecomManager.PRESENTATION_ALLOWED;
                    String label = CallHistoryPolicy.displayLabel(
                            presentationAllowed,
                            cursor.getString(nameIndex),
                            cursor.getString(numberIndex),
                            getString(R.string.unknown_number));
                    String type = recentCallTypeLabel(CallHistoryPolicy.typeKey(cursor.getInt(typeIndex)));
                    String date = dateFormat.format(new Date(cursor.getLong(dateIndex)));
                    String duration = getString(
                            R.string.recent_call_duration,
                            CallHistoryPolicy.formatDuration(cursor.getLong(durationIndex)));
                    if (rows.length() > 0) rows.append("\n\n");
                    rows.append(getString(R.string.recent_call_row, label, type, date, duration));
                    count++;
                }
            }
        } catch (SecurityException exc) {
            Toast.makeText(this, R.string.recent_calls_permission_denied, Toast.LENGTH_SHORT).show();
            return;
        }
        if (rows.length() == 0) rows.append(getString(R.string.recent_calls_empty));
        new AlertDialog.Builder(this)
                .setTitle(R.string.recent_calls_title)
                .setMessage(rows.toString())
                .setPositiveButton(android.R.string.ok, null)
                .show();
    }

    private String recentCallTypeLabel(String key) {
        switch (key) {
            case "incoming": return getString(R.string.recent_call_incoming);
            case "outgoing": return getString(R.string.recent_call_outgoing);
            case "missed": return getString(R.string.recent_call_missed);
            case "rejected": return getString(R.string.recent_call_rejected);
            case "blocked": return getString(R.string.recent_call_blocked);
            case "voicemail": return getString(R.string.recent_call_voicemail);
            default: return getString(R.string.recent_call_other);
        }
    }

    private boolean isDefaultDialer() {
        RoleManager roleManager = getSystemService(RoleManager.class);
        return roleManager != null
                && roleManager.isRoleAvailable(RoleManager.ROLE_DIALER)
                && roleManager.isRoleHeld(RoleManager.ROLE_DIALER);
    }

    private void refreshPhoneRoleState() {
        if (roleStatus == null || roleButton == null || activeCallButton == null || recentCallsButton == null) return;
        RoleManager roleManager = getSystemService(RoleManager.class);
        boolean available = roleManager != null && roleManager.isRoleAvailable(RoleManager.ROLE_DIALER);
        boolean held = available && roleManager.isRoleHeld(RoleManager.ROLE_DIALER);
        roleStatus.setText(held ? R.string.role_active : R.string.role_inactive);
        roleButton.setEnabled(available && !held);
        activeCallButton.setEnabled(held && SwirInCallService.hasActiveCall());
        recentCallsButton.setEnabled(held);
    }

    private void refreshDialState() {
        if (dial != null) dial.setEnabled(DialerPolicy.isDialable(number.getText().toString()));
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
    private LinearLayout.LayoutParams weighted() { return new LinearLayout.LayoutParams(0, -2, 1f); }
    private GridLayout.LayoutParams gridCell() {
        GridLayout.LayoutParams params = new GridLayout.LayoutParams();
        params.width = 0;
        params.height = dp(62);
        params.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        int margin = dim(R.dimen.swir_space_xs);
        params.setMargins(margin, margin, margin, margin);
        return params;
    }
    private int dim(int id) { return getResources().getDimensionPixelSize(id); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private static final class SimpleTextWatcher implements android.text.TextWatcher {
        private final Runnable callback;
        SimpleTextWatcher(Runnable callback) { this.callback = callback; }
        @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
        @Override public void onTextChanged(CharSequence s, int start, int before, int count) { callback.run(); }
        @Override public void afterTextChanged(android.text.Editable s) {}
    }
}
