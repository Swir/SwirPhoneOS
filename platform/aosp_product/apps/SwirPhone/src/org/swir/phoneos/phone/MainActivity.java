package org.swir.phoneos.phone;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private EditText number;
    private Button dial;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        setContentView(buildUi());
        refreshDialState();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(24), dp(24), dp(24), dp(24));
        root.setBackgroundColor(Color.rgb(5, 13, 24));

        TextView eyebrow = text(getString(R.string.eyebrow), 13, Color.rgb(74, 222, 255));
        root.addView(eyebrow, matchWrap());
        TextView title = text(getString(R.string.title), 30, Color.WHITE);
        root.addView(title, matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 15, Color.rgb(170, 191, 211));
        root.addView(subtitle, matchWrap());

        number = new EditText(this);
        number.setHint(R.string.number_hint);
        number.setTextColor(Color.WHITE);
        number.setHintTextColor(Color.rgb(115, 139, 160));
        number.setTextSize(28);
        number.setGravity(Gravity.CENTER_HORIZONTAL);
        number.setSingleLine(true);
        number.setInputType(InputType.TYPE_CLASS_PHONE);
        number.setContentDescription(getString(R.string.number_content_description));
        LinearLayout.LayoutParams numberParams = new LinearLayout.LayoutParams(-1, dp(64));
        numberParams.topMargin = dp(24);
        root.addView(number, numberParams);
        number.addTextChangedListener(new SimpleTextWatcher(this::refreshDialState));

        GridLayout keypad = new GridLayout(this);
        keypad.setColumnCount(3);
        keypad.setRowCount(4);
        String[] keys = getResources().getStringArray(R.array.dial_keys);
        for (String key : keys) keypad.addView(keyButton(key), gridCell());
        LinearLayout.LayoutParams keypadParams = new LinearLayout.LayoutParams(-1, 0, 1f);
        keypadParams.topMargin = dp(14);
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

        TextView safety = text(getString(R.string.handoff_notice), 13, Color.rgb(127, 151, 173));
        safety.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(safety, matchWrap());
        return root;
    }

    private Button keyButton(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(24);
        button.setTextColor(Color.WHITE);
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

    private void refreshDialState() {
        if (dial != null) dial.setEnabled(DialerPolicy.isDialable(number.getText().toString()));
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        view.setPadding(0, dp(5), 0, dp(5));
        return view;
    }

    private Button actionButton(int textRes) {
        Button button = new Button(this);
        button.setText(textRes);
        return button;
    }

    private LinearLayout.LayoutParams matchWrap() { return new LinearLayout.LayoutParams(-1, -2); }
    private LinearLayout.LayoutParams weighted() { return new LinearLayout.LayoutParams(0, -2, 1f); }
    private GridLayout.LayoutParams gridCell() {
        GridLayout.LayoutParams params = new GridLayout.LayoutParams();
        params.width = 0;
        params.height = dp(62);
        params.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        params.setMargins(dp(4), dp(4), dp(4), dp(4));
        return params;
    }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private static final class SimpleTextWatcher implements android.text.TextWatcher {
        private final Runnable callback;
        SimpleTextWatcher(Runnable callback) { this.callback = callback; }
        @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
        @Override public void onTextChanged(CharSequence s, int start, int before, int count) { callback.run(); }
        @Override public void afterTextChanged(android.text.Editable s) {}
    }
}
