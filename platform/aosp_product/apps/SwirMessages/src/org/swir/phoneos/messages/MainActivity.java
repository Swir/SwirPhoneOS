package org.swir.phoneos.messages;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DateFormat;
import java.util.Date;
import java.util.List;

public final class MainActivity extends Activity {
    private static final String PREFS = "compose_draft";
    private static final String KEY_RECIPIENTS = "recipients";
    private static final String KEY_BODY = "body";
    private static final String KEY_REMEMBER_HISTORY = "remember_handoff_history";
    private static final String KEY_HISTORY = "handoff_history";

    private EditText recipients;
    private EditText body;
    private TextView counter;
    private TextView history;
    private Button handoff;
    private CheckBox rememberHistory;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        setContentView(buildUi());
        restoreDraft();
        refreshState();
        renderHistory();
    }

    @Override protected void onPause() {
        super.onPause();
        saveDraft();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pagePadding = dim(R.dimen.swir_space_lg);
        root.setPadding(pagePadding, pagePadding, pagePadding, pagePadding);
        root.setBackgroundColor(getColor(R.color.swir_background));

        root.addView(text(getString(R.string.eyebrow), 13, getColor(R.color.swir_accent_cyan)), matchWrap());
        root.addView(text(getString(R.string.title), 30, getColor(R.color.swir_text_primary)), matchWrap());
        root.addView(text(getString(R.string.subtitle), 15, getColor(R.color.swir_text_secondary)), matchWrap());

        recipients = new EditText(this);
        recipients.setHint(R.string.recipients_hint);
        recipients.setTextColor(getColor(R.color.swir_text_primary));
        recipients.setHintTextColor(getColor(R.color.swir_text_secondary));
        recipients.setSingleLine(true);
        recipients.setInputType(InputType.TYPE_CLASS_PHONE);
        recipients.setContentDescription(getString(R.string.recipients_content_description));
        recipients.setMinHeight(dim(R.dimen.swir_touch_min));
        LinearLayout.LayoutParams recipientParams = new LinearLayout.LayoutParams(-1, dp(60));
        recipientParams.topMargin = dim(R.dimen.swir_space_lg);
        root.addView(recipients, recipientParams);

        body = new EditText(this);
        body.setHint(R.string.message_hint);
        body.setTextColor(getColor(R.color.swir_text_primary));
        body.setHintTextColor(getColor(R.color.swir_text_secondary));
        body.setGravity(Gravity.TOP | Gravity.START);
        body.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        body.setContentDescription(getString(R.string.message_content_description));
        body.setMinHeight(dim(R.dimen.swir_touch_min));
        LinearLayout.LayoutParams bodyParams = new LinearLayout.LayoutParams(-1, 0, 1f);
        bodyParams.topMargin = dim(R.dimen.swir_space_sm);
        root.addView(body, bodyParams);

        counter = text(getString(R.string.characters_remaining, MessagePolicy.MAX_BODY_LENGTH), 13, getColor(R.color.swir_text_secondary));
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

        rememberHistory = new CheckBox(this);
        rememberHistory.setText(R.string.remember_handoff_history);
        rememberHistory.setTextColor(getColor(R.color.swir_text_primary));
        rememberHistory.setContentDescription(getString(R.string.remember_handoff_history_description));
        rememberHistory.setMinHeight(dim(R.dimen.swir_touch_min));
        root.addView(rememberHistory, matchWrap());

        TextView notice = text(getString(R.string.handoff_notice), 13, getColor(R.color.swir_text_secondary));
        notice.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(notice, matchWrap());

        LinearLayout historyHeader = new LinearLayout(this);
        historyHeader.setOrientation(LinearLayout.HORIZONTAL);
        TextView historyTitle = text(getString(R.string.recent_handoffs), 16, getColor(R.color.swir_text_primary));
        historyHeader.addView(historyTitle, new LinearLayout.LayoutParams(0, -2, 1f));
        Button clearHistory = actionButton(R.string.clear_recent_handoffs);
        clearHistory.setOnClickListener(v -> clearHistory());
        historyHeader.addView(clearHistory, new LinearLayout.LayoutParams(-2, -2));
        root.addView(historyHeader, matchWrap());

        history = text(getString(R.string.recent_handoffs_empty), 13, getColor(R.color.swir_text_secondary));
        history.setContentDescription(getString(R.string.recent_handoffs_description));
        root.addView(history, matchWrap());

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
        if (rememberHistory != null && rememberHistory.isChecked()) {
            recordHandoff(normalizedRecipients, normalizedBody);
        }
    }

    private void recordHandoff(String normalizedRecipients, String normalizedBody) {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        try {
            String updated = MessageHandoffHistory.prepend(
                    prefs.getString(KEY_HISTORY, ""),
                    System.currentTimeMillis(),
                    normalizedRecipients,
                    normalizedBody);
            prefs.edit().putString(KEY_HISTORY, updated).apply();
            renderHistory();
        } catch (IllegalArgumentException | IllegalStateException ignored) {
            Toast.makeText(this, R.string.history_not_saved, Toast.LENGTH_SHORT).show();
        }
    }

    private void renderHistory() {
        if (history == null) return;
        List<MessageHandoffHistory.Entry> entries = MessageHandoffHistory.decode(
                getSharedPreferences(PREFS, MODE_PRIVATE).getString(KEY_HISTORY, ""));
        if (entries.isEmpty()) {
            history.setText(R.string.recent_handoffs_empty);
            return;
        }
        DateFormat format = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT);
        StringBuilder out = new StringBuilder();
        for (MessageHandoffHistory.Entry entry : entries) {
            if (out.length() > 0) out.append("\n\n");
            out.append(getString(
                    R.string.recent_handoff_item,
                    format.format(new Date(entry.timestampMillis)),
                    entry.recipients,
                    MessageHandoffHistory.preview(entry.body)));
        }
        history.setText(out.toString());
    }

    private void saveDraft() {
        if (recipients == null || body == null) return;
        SharedPreferences.Editor edit = getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(KEY_RECIPIENTS, recipients.getText().toString())
                .putString(KEY_BODY, MessagePolicy.normalizeBody(body.getText().toString()));
        if (rememberHistory != null) edit.putBoolean(KEY_REMEMBER_HISTORY, rememberHistory.isChecked());
        edit.apply();
    }

    private void restoreDraft() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        recipients.setText(prefs.getString(KEY_RECIPIENTS, ""));
        body.setText(prefs.getString(KEY_BODY, ""));
        rememberHistory.setChecked(prefs.getBoolean(KEY_REMEMBER_HISTORY, false));
    }

    private void clearDraft() {
        recipients.getText().clear();
        body.getText().clear();
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .remove(KEY_RECIPIENTS)
                .remove(KEY_BODY)
                .apply();
        Toast.makeText(this, R.string.draft_cleared, Toast.LENGTH_SHORT).show();
    }

    private void clearHistory() {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().remove(KEY_HISTORY).apply();
        renderHistory();
        Toast.makeText(this, R.string.recent_handoffs_cleared, Toast.LENGTH_SHORT).show();
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
