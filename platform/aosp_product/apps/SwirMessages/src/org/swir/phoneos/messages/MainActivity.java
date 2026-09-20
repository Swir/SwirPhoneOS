package org.swir.phoneos.messages;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.UriPermission;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
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
    private static final int REQUEST_MEDIA_ATTACHMENT = 421;
    private static final String PREFS = "compose_draft";
    private static final String KEY_RECIPIENTS = "recipients";
    private static final String KEY_BODY = "body";
    private static final String KEY_REMEMBER_HISTORY = "remember_handoff_history";
    private static final String KEY_HISTORY = "handoff_history";
    private static final String KEY_ATTACHMENT_URI = "attachment_uri";
    private static final String KEY_ATTACHMENT_MIME = "attachment_mime";
    private static final String KEY_ATTACHMENT_NAME = "attachment_name";
    private static final String KEY_ATTACHMENT_SIZE = "attachment_size";

    private EditText recipients;
    private EditText body;
    private TextView counter;
    private TextView history;
    private TextView attachmentSummary;
    private Button handoff;
    private Button removeAttachment;
    private CheckBox rememberHistory;
    private Uri attachmentUri;
    private String attachmentMime;
    private String attachmentName;
    private long attachmentSize = -1L;

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
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

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

        LinearLayout attachmentActions = new LinearLayout(this);
        attachmentActions.setOrientation(LinearLayout.HORIZONTAL);
        Button attach = actionButton(R.string.attach_media);
        attach.setOnClickListener(v -> chooseMediaAttachment());
        attachmentActions.addView(attach, weighted());
        removeAttachment = actionButton(R.string.remove_media);
        removeAttachment.setOnClickListener(v -> clearAttachment());
        removeAttachment.setVisibility(View.GONE);
        attachmentActions.addView(removeAttachment, weighted());
        root.addView(attachmentActions, matchWrap());

        attachmentSummary = text("", 13, getColor(R.color.swir_text_secondary));
        attachmentSummary.setVisibility(View.GONE);
        root.addView(attachmentSummary, matchWrap());

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

    private void chooseMediaAttachment() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"image/*", "video/*", "audio/*"});
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        if (intent.resolveActivity(getPackageManager()) == null) {
            Toast.makeText(this, R.string.media_picker_unavailable, Toast.LENGTH_SHORT).show();
            return;
        }
        startActivityForResult(intent, REQUEST_MEDIA_ATTACHMENT);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_MEDIA_ATTACHMENT || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        AttachmentInfo info = attachmentInfo(uri);
        String safeName = MessagePolicy.safeAttachmentName(info.displayName);
        if (!"content".equals(uri.getScheme()) || !MessagePolicy.attachmentReviewReady(info.mime, safeName, info.sizeBytes)) {
            Toast.makeText(this, R.string.invalid_media_attachment, Toast.LENGTH_SHORT).show();
            return;
        }

        int takeFlags = data.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION;
        if (takeFlags == 0 || !takePersistedReadPermission(uri, takeFlags)) {
            Toast.makeText(this, R.string.invalid_media_attachment, Toast.LENGTH_SHORT).show();
            return;
        }

        Uri previousUri = attachmentUri;
        attachmentUri = uri;
        attachmentMime = info.mime;
        attachmentName = safeName;
        attachmentSize = info.sizeBytes;
        if (previousUri != null && !previousUri.equals(uri)) releasePersistedReadPermission(previousUri);
        saveDraft();
        renderAttachment();
        refreshState();
    }

    private AttachmentInfo attachmentInfo(Uri uri) {
        String displayName = null;
        long sizeBytes = -1L;
        String mime = null;
        try {
            mime = getContentResolver().getType(uri);
        } catch (RuntimeException ignored) {
            // Revoked or malformed provider access fails closed below.
        }
        try (Cursor cursor = getContentResolver().query(
                uri,
                new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE},
                null,
                null,
                null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                int sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE);
                if (nameIndex >= 0 && !cursor.isNull(nameIndex)) displayName = cursor.getString(nameIndex);
                if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) sizeBytes = cursor.getLong(sizeIndex);
            }
        } catch (Exception ignored) {
            // The pure-Java attachment policy fails closed on missing/invalid provider metadata.
        }
        return new AttachmentInfo(displayName, mime, sizeBytes);
    }

    private boolean takePersistedReadPermission(Uri uri, int flags) {
        try {
            getContentResolver().takePersistableUriPermission(uri, flags);
            return hasPersistedReadPermission(uri);
        } catch (SecurityException | IllegalArgumentException ignored) {
            return false;
        }
    }

    private boolean hasPersistedReadPermission(Uri uri) {
        try {
            for (UriPermission permission : getContentResolver().getPersistedUriPermissions()) {
                if (permission.isReadPermission() && uri.equals(permission.getUri())) return true;
            }
        } catch (RuntimeException ignored) {
            return false;
        }
        return false;
    }

    private void releasePersistedReadPermission(Uri uri) {
        try {
            getContentResolver().releasePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (SecurityException | IllegalArgumentException ignored) {
            // Permission may already have been revoked by the provider or system.
        }
    }

    private boolean revalidateCurrentAttachment() {
        if (attachmentUri == null
                || !"content".equals(attachmentUri.getScheme())
                || !hasPersistedReadPermission(attachmentUri)
                || !MessagePolicy.attachmentReviewReady(attachmentMime, attachmentName, attachmentSize)) {
            return false;
        }
        AttachmentInfo fresh = attachmentInfo(attachmentUri);
        String freshName = MessagePolicy.safeAttachmentName(fresh.displayName);
        return MessagePolicy.attachmentReviewReady(fresh.mime, freshName, fresh.sizeBytes)
                && attachmentMime.equals(fresh.mime)
                && attachmentName.equals(freshName)
                && attachmentSize == fresh.sizeBytes;
    }

    private void openSystemMessagingApp() {
        String normalizedRecipients = MessagePolicy.normalizeRecipients(recipients.getText().toString());
        String normalizedBody = MessagePolicy.normalizeBody(body.getText().toString());
        boolean hasAttachment = attachmentUri != null;
        if (hasAttachment && !revalidateCurrentAttachment()) {
            clearAttachment();
            Toast.makeText(this, R.string.invalid_media_attachment, Toast.LENGTH_SHORT).show();
            return;
        }
        boolean mediaReady = hasAttachment && MessagePolicy.canMediaHandoff(
                normalizedRecipients, normalizedBody, attachmentMime, attachmentName, attachmentSize);
        if (!mediaReady && !MessagePolicy.canHandoff(normalizedRecipients, normalizedBody)) {
            Toast.makeText(this, R.string.invalid_message, Toast.LENGTH_SHORT).show();
            return;
        }

        Intent intent;
        if (mediaReady) {
            intent = new Intent(Intent.ACTION_SEND);
            intent.setType(attachmentMime);
            intent.putExtra(Intent.EXTRA_STREAM, attachmentUri);
            intent.putExtra(Intent.EXTRA_TEXT, normalizedBody);
            intent.putExtra("sms_body", normalizedBody);
            intent.putExtra("address", normalizedRecipients);
            intent.setClipData(ClipData.newUri(getContentResolver(), getString(R.string.app_name), attachmentUri));
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } else {
            intent = new Intent(Intent.ACTION_SENDTO, Uri.fromParts("smsto", normalizedRecipients, null));
            intent.putExtra("sms_body", normalizedBody);
        }
        if (intent.resolveActivity(getPackageManager()) == null) {
            Toast.makeText(this, R.string.no_messaging_app, Toast.LENGTH_SHORT).show();
            return;
        }
        saveDraft();
        if (mediaReady) {
            startActivity(Intent.createChooser(intent, getString(R.string.continue_to_messages)));
        } else {
            startActivity(intent);
        }
        if (!mediaReady && rememberHistory != null && rememberHistory.isChecked() && !normalizedBody.trim().isEmpty()) {
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
        persistAttachmentDraft(edit);
        edit.apply();
    }

    private void persistAttachmentDraft(SharedPreferences.Editor edit) {
        if (attachmentUri != null
                && hasPersistedReadPermission(attachmentUri)
                && MessagePolicy.attachmentReviewReady(attachmentMime, attachmentName, attachmentSize)) {
            edit.putString(KEY_ATTACHMENT_URI, attachmentUri.toString())
                    .putString(KEY_ATTACHMENT_MIME, attachmentMime)
                    .putString(KEY_ATTACHMENT_NAME, attachmentName)
                    .putLong(KEY_ATTACHMENT_SIZE, attachmentSize);
        } else {
            removeAttachmentDraftKeys(edit);
        }
    }

    private void restoreDraft() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        recipients.setText(prefs.getString(KEY_RECIPIENTS, ""));
        body.setText(prefs.getString(KEY_BODY, ""));
        rememberHistory.setChecked(prefs.getBoolean(KEY_REMEMBER_HISTORY, false));
        restoreAttachmentDraft(prefs);
    }

    private void restoreAttachmentDraft(SharedPreferences prefs) {
        String rawUri = prefs.getString(KEY_ATTACHMENT_URI, "");
        if (rawUri == null || rawUri.trim().isEmpty()) return;

        Uri uri;
        try {
            uri = Uri.parse(rawUri);
        } catch (RuntimeException ignored) {
            clearStoredAttachmentDraft(prefs, null);
            return;
        }
        String storedMime = prefs.getString(KEY_ATTACHMENT_MIME, null);
        String storedName = prefs.getString(KEY_ATTACHMENT_NAME, null);
        long storedSize = prefs.getLong(KEY_ATTACHMENT_SIZE, -1L);
        if (!"content".equals(uri.getScheme())
                || !hasPersistedReadPermission(uri)
                || !MessagePolicy.attachmentReviewReady(storedMime, storedName, storedSize)) {
            clearStoredAttachmentDraft(prefs, uri);
            return;
        }

        AttachmentInfo fresh = attachmentInfo(uri);
        String freshName = MessagePolicy.safeAttachmentName(fresh.displayName);
        if (!MessagePolicy.attachmentReviewReady(fresh.mime, freshName, fresh.sizeBytes)
                || !storedMime.equals(fresh.mime)
                || !storedName.equals(freshName)
                || storedSize != fresh.sizeBytes) {
            clearStoredAttachmentDraft(prefs, uri);
            return;
        }

        attachmentUri = uri;
        attachmentMime = fresh.mime;
        attachmentName = freshName;
        attachmentSize = fresh.sizeBytes;
        renderAttachment();
    }

    private void clearDraft() {
        recipients.getText().clear();
        body.getText().clear();
        clearAttachment();
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .remove(KEY_RECIPIENTS)
                .remove(KEY_BODY)
                .apply();
        Toast.makeText(this, R.string.draft_cleared, Toast.LENGTH_SHORT).show();
    }

    private void clearAttachment() {
        Uri previousUri = attachmentUri;
        attachmentUri = null;
        attachmentMime = null;
        attachmentName = null;
        attachmentSize = -1L;
        removeAttachmentDraftKeys(getSharedPreferences(PREFS, MODE_PRIVATE).edit()).apply();
        if (previousUri != null) releasePersistedReadPermission(previousUri);
        renderAttachment();
        refreshState();
    }

    private void clearStoredAttachmentDraft(SharedPreferences prefs, Uri uri) {
        removeAttachmentDraftKeys(prefs.edit()).apply();
        if (uri != null) releasePersistedReadPermission(uri);
        attachmentUri = null;
        attachmentMime = null;
        attachmentName = null;
        attachmentSize = -1L;
        renderAttachment();
        refreshState();
    }

    private SharedPreferences.Editor removeAttachmentDraftKeys(SharedPreferences.Editor edit) {
        return edit.remove(KEY_ATTACHMENT_URI)
                .remove(KEY_ATTACHMENT_MIME)
                .remove(KEY_ATTACHMENT_NAME)
                .remove(KEY_ATTACHMENT_SIZE);
    }

    private void renderAttachment() {
        if (attachmentSummary == null || removeAttachment == null) return;
        if (attachmentUri == null || attachmentName == null) {
            attachmentSummary.setText("");
            attachmentSummary.setVisibility(View.GONE);
            removeAttachment.setVisibility(View.GONE);
            return;
        }
        attachmentSummary.setText(getString(R.string.media_attachment_selected, attachmentName));
        attachmentSummary.setVisibility(View.VISIBLE);
        removeAttachment.setVisibility(View.VISIBLE);
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
            String recipientText = recipients.getText().toString();
            String bodyText = body.getText().toString();
            boolean textReady = MessagePolicy.canHandoff(recipientText, bodyText);
            boolean mediaReady = attachmentUri != null && MessagePolicy.canMediaHandoff(
                    recipientText, bodyText, attachmentMime, attachmentName, attachmentSize);
            handoff.setEnabled(textReady || mediaReady);
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

    private static final class AttachmentInfo {
        final String displayName;
        final String mime;
        final long sizeBytes;

        AttachmentInfo(String displayName, String mime, long sizeBytes) {
            this.displayName = displayName;
            this.mime = mime;
            this.sizeBytes = sizeBytes;
        }
    }

    private static final class SimpleTextWatcher implements android.text.TextWatcher {
        private final Runnable callback;
        SimpleTextWatcher(Runnable callback) { this.callback = callback; }
        @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
        @Override public void onTextChanged(CharSequence s, int start, int before, int count) { callback.run(); }
        @Override public void afterTextChanged(android.text.Editable s) {}
    }
}
