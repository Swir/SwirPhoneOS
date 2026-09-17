package org.swir.phoneos.messages;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final String PREFS = "compose_draft";
    private static final String KEY_RECIPIENTS = "recipients";
    private static final String KEY_BODY = "body";

    private EditText recipients;
    private EditText body;
    private TextView counter;
    private Button handoff;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        setContentView(buildUi());
        restoreDraft();
        refreshState();
    }

    @Override protected void onPause() {
        super.onPause();
        saveDraft();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(24), dp(24), dp(24), dp(24));
        root.setBackgroundColor(Color.rgb(5, 13, 24));

        root.addView(text(getString(R.string.eyebrow), 13, Color.rgb(74, 222, 255)), matchWrap());
        root.addView(text(getString(R.string.title), 30, Color.WHITE), matchWrap());
        root.addView(text(getString(R.string.subtitle), 15, Color.rgb(170, 191, 211)), matchWrap());

        recipients = new EditText(this);
        recipients.setHint(R.string.recipients_hint);
        recipients.setTextColor(Color.WHITE);
        recipients.setHintTextColor(Color.rgb(115, 139, 160));
        recipients.setSingleLine(true);
        recipients.setInputType(InputType.TYPE_CLASS_PHONE);
        recipients.setContentDescription(getString(R.string.recipients_content_description));
        LinearLayout.LayoutParams recipientParams = new LinearLayout.LayoutParams(-1, dp(60));
        recipientParams.topMargin = dp(22);
        root.addView(recipients, recipientParams);

        body = new EditText(this);
        body.setHint(R.string.message_hint);
        body.setTextColor(Color.WHITE);
        body.setHintTextColor(Color.rgb(115, 139, 160));
        body.setGravity(Gravity.TOP | Gravity.START);
        body.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        body.setContentDescription(getString(R.string.message_content_description));
        LinearLayout.LayoutParams bodyParams = new LinearLayout.LayoutParams(-1, 0, 1f);
        bodyParams.topMargin = dp(12);
        root.addView(body, bodyParams);

        counter = text(getString(R.string.characters_remaining, MessagePolicy.MAX_BODY_LENGTH), 13, Color.rgb(127, 151, 173));
        counter.setGravity(Gravity.END);
        root.addView(counter, matchWrap());

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        Button clear = actionButton(R.string.clear_draft);
        clear.setOnClickListener(v -> clearDraft());
        actions.addView(clear, weighted());
        handoff = actionButton(R.string.continue_to_messages);
        handoff.setOnClickListener(v -> openSystemMessagingApp());
        actions.addView(handoff, weighted());
        root.addView(actions, matchWrap());

        TextView notice = text(getString(R.string.handoff_notice), 13, Color.rgb(127, 151, 173));
        notice.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(notice, matchWrap());

        SimpleTextWatcher watcher = new SimpleTextWatcher(this::refreshState);
        recipients.addTextChangedListener(watcher);
        body.addTextChangedListener(watcher);
        return root;
    }

    private void openSystemMessagingApp() {
        String normalizedRecipients = MessagePolicy.normalizeRecipients(recipients.getText().toString());
        String normalizedBody = MessagePolicy.normalizeBody(body.getText().toString());
        if (!MessagePolicy.canHandoff(normalizedRecipients, normalizedBody)) {
            Toast.makeText(this, R.string.invalid_message, Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(Intent.ACTION_SENDTO, Uri.fromParts("smsto", normalizedRecipients, null));
        intent.putExtra("sms_body", normalizedBody);
        if (intent.resolveActivity(getPackageManager()) == null) {
            Toast.makeText(this, R.string.no_messaging_app, Toast.LENGTH_SHORT).show();
            return;
        }
        saveDraft();
        startActivity(intent);
    }

    private void saveDraft() {
        if (recipients == null || body == null) return;
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(KEY_RECIPIENTS, recipients.getText().toString())
                .putString(KEY_BODY, MessagePolicy.normalizeBody(body.getText().toString()))
                .apply();
    }

    private void restoreDraft() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        recipients.setText(prefs.getString(KEY_RECIPIENTS, ""));
        body.setText(prefs.getString(KEY_BODY, ""));
    }

    private void clearDraft() {
        recipients.getText().clear();
        body.getText().clear();
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().clear().apply();
        Toast.makeText(this, R.string.draft_cleared, Toast.LENGTH_SHORT).show();
    }

    private void refreshState() {
        if (counter != null && body != null) {
            counter.setText(getString(R.string.characters_remaining, MessagePolicy.remainingCharacters(body.getText().toString())));
        }
        if (handoff != null && recipients != null && body != null) {
            handoff.setEnabled(MessagePolicy.canHandoff(recipients.getText().toString(), body.getText().toString()));
        }
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
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private static final class SimpleTextWatcher implements android.text.TextWatcher {
        private final Runnable callback;
        SimpleTextWatcher(Runnable callback) { this.callback = callback; }
        @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
        @Override public void onTextChanged(CharSequence s, int start, int before, int count) { callback.run(); }
        @Override public void afterTextChanged(android.text.Editable s) {}
    }
}
