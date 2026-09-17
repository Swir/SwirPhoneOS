package org.swir.phoneos.files;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.text.Editable;
import android.text.TextWatcher;
import android.text.format.Formatter;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.FileNotFoundException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

/** Permission-free file manager built on user-granted Storage Access Framework trees. */
public final class MainActivity extends Activity {
    private static final int REQUEST_TREE = 4101;
    private static final String PREF_TREE = "tree_uri";

    private final ArrayDeque<Uri> parents = new ArrayDeque<>();
    private final List<DocumentEntry> visibleEntries = new ArrayList<>();
    private LinearLayout rows;
    private TextView location;
    private TextView clipboardState;
    private EditText search;
    private Uri treeUri;
    private Uri currentDirUri;
    private ClipboardItem clipboard;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_background));
        setContentView(buildUi());
        String persisted = getPreferences(MODE_PRIVATE).getString(PREF_TREE, null);
        if (persisted != null) {
            try {
                setTree(Uri.parse(persisted));
            } catch (RuntimeException ignored) {
                clearTree();
            }
        }
        renderCurrent();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(18));
        root.setBackgroundColor(getColor(R.color.swir_background));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

        TextView title = text(R.string.app_name, 26, getColor(R.color.swir_accent_cyan));
        root.addView(title, matchWrap());
        TextView subtitle = text(R.string.subtitle, 14, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, dp(4), 0, dp(10));
        root.addView(subtitle, matchWrap());

        location = text(R.string.no_folder, 13, getColor(R.color.swir_text_secondary));
        root.addView(location, matchWrap());

        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setOrientation(LinearLayout.HORIZONTAL);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setPadding(0, dp(10), 0, dp(8));
        toolbar.addView(actionButton(R.string.choose_folder, v -> chooseTree()), weighted());
        toolbar.addView(actionButton(R.string.up, v -> goUp()), weighted());
        toolbar.addView(actionButton(R.string.new_folder, v -> createFolder()), weighted());
        root.addView(toolbar, matchWrap());

        clipboardState = text(R.string.clipboard_empty, 12, getColor(R.color.swir_text_secondary));
        root.addView(clipboardState, matchWrap());
        Button paste = actionButton(R.string.paste_here, v -> pasteHere());
        paste.setContentDescription(getString(R.string.paste_here));
        root.addView(paste, matchWrap());

        search = new EditText(this);
        search.setSingleLine(true);
        search.setHint(R.string.search_hint);
        search.setTextColor(getColor(R.color.swir_text_primary));
        search.setHintTextColor(getColor(R.color.swir_text_secondary));
        search.setBackgroundColor(getColor(R.color.swir_surface));
        search.setPadding(dp(14), dp(12), dp(14), dp(12));
        search.setMinHeight(touchMin());
        search.setContentDescription(getString(R.string.search_hint));
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { renderRows(); }
            @Override public void afterTextChanged(Editable s) {}
        });
        root.addView(search, matchWrap());

        ScrollView scroll = new ScrollView(this);
        rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        rows.setPadding(0, dp(8), 0, dp(16));
        scroll.addView(rows, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return root;
    }

    private void chooseTree() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION
                | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        startActivityForResult(intent, REQUEST_TREE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_TREE || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri selected = data.getData();
        int takeFlags = data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        try {
            getContentResolver().takePersistableUriPermission(selected, takeFlags);
            getPreferences(MODE_PRIVATE).edit().putString(PREF_TREE, selected.toString()).apply();
            setTree(selected);
            renderCurrent();
        } catch (SecurityException exception) {
            Toast.makeText(this, R.string.access_failed, Toast.LENGTH_LONG).show();
        }
    }

    private void setTree(Uri selected) {
        treeUri = selected;
        String rootId = DocumentsContract.getTreeDocumentId(selected);
        currentDirUri = DocumentsContract.buildDocumentUriUsingTree(selected, rootId);
        parents.clear();
        location.setText(getString(R.string.location_selected));
    }

    private void clearTree() {
        treeUri = null;
        currentDirUri = null;
        parents.clear();
        visibleEntries.clear();
    }

    private void goUp() {
        if (!parents.isEmpty()) {
            currentDirUri = parents.pop();
            renderCurrent();
        }
    }

    private void openDirectory(DocumentEntry entry) {
        if (!entry.directory) return;
        parents.push(currentDirUri);
        currentDirUri = entry.uri;
        location.setText(getString(R.string.location_format, entry.name));
        renderCurrent();
    }

    private void renderCurrent() {
        visibleEntries.clear();
        if (currentDirUri == null || treeUri == null) {
            location.setText(R.string.no_folder);
            renderRows();
            updateClipboardLabel();
            return;
        }
        try {
            String documentId = DocumentsContract.getDocumentId(currentDirUri);
            Uri children = DocumentsContract.buildChildDocumentsUriUsingTree(treeUri, documentId);
            String[] projection = {
                    DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                    DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                    DocumentsContract.Document.COLUMN_MIME_TYPE,
                    DocumentsContract.Document.COLUMN_SIZE,
                    DocumentsContract.Document.COLUMN_FLAGS
            };
            try (Cursor cursor = getContentResolver().query(children, projection, null, null, null)) {
                if (cursor != null) {
                    while (cursor.moveToNext()) {
                        String childId = cursor.getString(0);
                        String name = cursor.getString(1);
                        String mime = cursor.getString(2);
                        long size = cursor.isNull(3) ? -1L : cursor.getLong(3);
                        long flags = cursor.isNull(4) ? 0L : cursor.getLong(4);
                        Uri uri = DocumentsContract.buildDocumentUriUsingTree(treeUri, childId);
                        visibleEntries.add(new DocumentEntry(uri, name, mime, size, flags));
                    }
                }
            }
        } catch (RuntimeException exception) {
            Toast.makeText(this, R.string.read_failed, Toast.LENGTH_LONG).show();
        }
        renderRows();
        updateClipboardLabel();
    }

    private void renderRows() {
        if (rows == null) return;
        rows.removeAllViews();
        String query = search == null ? "" : search.getText().toString();
        int shown = 0;
        for (DocumentEntry entry : visibleEntries) {
            if (!FilePolicy.matches(entry.name, query)) continue;
            String detail = entry.directory || entry.size < 0 ? entry.name : getString(
                    R.string.file_with_size, entry.name, Formatter.formatFileSize(this, entry.size));
            Button row = actionButtonText(detail, v -> {
                if (entry.directory) openDirectory(entry); else openDocument(entry);
            });
            row.setOnLongClickListener(v -> {
                showActions(entry);
                return true;
            });
            row.setContentDescription(getString(
                    entry.directory ? R.string.folder_item_description : R.string.file_item_description,
                    entry.name));
            LinearLayout.LayoutParams params = matchWrap();
            params.setMargins(0, dp(4), 0, dp(4));
            rows.addView(row, params);
            shown++;
        }
        if (shown == 0) {
            TextView empty = text(
                    currentDirUri == null ? R.string.choose_folder_prompt : R.string.no_results,
                    15,
                    getColor(R.color.swir_text_secondary));
            empty.setPadding(dp(4), dp(18), dp(4), dp(18));
            rows.addView(empty, matchWrap());
        }
    }

    private void showActions(DocumentEntry entry) {
        List<String> labels = new ArrayList<>();
        List<Runnable> actions = new ArrayList<>();
        if (!entry.directory) {
            labels.add(getString(R.string.open));
            actions.add(() -> openDocument(entry));
            labels.add(getString(R.string.share));
            actions.add(() -> shareDocument(entry));
        }
        if ((entry.flags & DocumentsContract.Document.FLAG_SUPPORTS_RENAME) != 0) {
            labels.add(getString(R.string.rename));
            actions.add(() -> rename(entry));
        }
        if ((entry.flags & DocumentsContract.Document.FLAG_SUPPORTS_COPY) != 0) {
            labels.add(getString(R.string.copy));
            actions.add(() -> setClipboard(entry, false));
        }
        if ((entry.flags & DocumentsContract.Document.FLAG_SUPPORTS_MOVE) != 0) {
            labels.add(getString(R.string.move));
            actions.add(() -> setClipboard(entry, true));
        }
        if ((entry.flags & DocumentsContract.Document.FLAG_SUPPORTS_DELETE) != 0) {
            labels.add(getString(R.string.delete));
            actions.add(() -> confirmDelete(entry));
        }
        new AlertDialog.Builder(this)
                .setTitle(entry.name)
                .setItems(labels.toArray(new String[0]), (dialog, which) -> actions.get(which).run())
                .setNegativeButton(R.string.cancel, null)
                .show();
    }

    private void setClipboard(DocumentEntry entry, boolean move) {
        clipboard = new ClipboardItem(entry.uri, currentDirUri, entry.name, move);
        updateClipboardLabel();
    }

    private void updateClipboardLabel() {
        if (clipboard == null) {
            clipboardState.setText(R.string.clipboard_empty);
        } else {
            clipboardState.setText(getString(
                    clipboard.move ? R.string.clipboard_move : R.string.clipboard_copy,
                    clipboard.name));
        }
    }

    private void pasteHere() {
        if (clipboard == null || currentDirUri == null) {
            Toast.makeText(this, R.string.clipboard_empty, Toast.LENGTH_SHORT).show();
            return;
        }
        try {
            Uri result = clipboard.move
                    ? DocumentsContract.moveDocument(getContentResolver(), clipboard.uri, clipboard.parentUri, currentDirUri)
                    : DocumentsContract.copyDocument(getContentResolver(), clipboard.uri, currentDirUri);
            if (result == null) throw new IllegalStateException("Provider returned no destination document");
            clipboard = null;
            Toast.makeText(this, R.string.operation_complete, Toast.LENGTH_SHORT).show();
            renderCurrent();
        } catch (FileNotFoundException | RuntimeException exception) {
            Toast.makeText(this, R.string.operation_failed, Toast.LENGTH_LONG).show();
        }
    }

    private void createFolder() {
        if (currentDirUri == null) {
            Toast.makeText(this, R.string.choose_folder_prompt, Toast.LENGTH_SHORT).show();
            return;
        }
        promptForName(R.string.new_folder, "", name -> {
            try {
                Uri created = DocumentsContract.createDocument(
                        getContentResolver(), currentDirUri, DocumentsContract.Document.MIME_TYPE_DIR, name);
                if (created == null) throw new IllegalStateException("Provider returned no created folder");
                renderCurrent();
            } catch (FileNotFoundException | RuntimeException exception) {
                Toast.makeText(this, R.string.operation_failed, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void rename(DocumentEntry entry) {
        promptForName(R.string.rename, entry.name, name -> {
            try {
                Uri renamed = DocumentsContract.renameDocument(getContentResolver(), entry.uri, name);
                if (renamed == null) throw new IllegalStateException("Provider returned no renamed document");
                renderCurrent();
            } catch (FileNotFoundException | RuntimeException exception) {
                Toast.makeText(this, R.string.operation_failed, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void promptForName(int title, String initial, NameAction action) {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(initial);
        input.setSelection(input.length());
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setView(input)
                .setPositiveButton(R.string.confirm, (dialog, which) -> {
                    String name = input.getText().toString().trim();
                    if (!FilePolicy.validName(name)) {
                        Toast.makeText(this, R.string.invalid_name, Toast.LENGTH_LONG).show();
                        return;
                    }
                    action.run(name);
                })
                .setNegativeButton(R.string.cancel, null)
                .show();
    }

    private void confirmDelete(DocumentEntry entry) {
        new AlertDialog.Builder(this)
                .setTitle(R.string.delete)
                .setMessage(getString(R.string.delete_confirm, entry.name))
                .setPositiveButton(R.string.delete, (dialog, which) -> {
                    try {
                        if (!DocumentsContract.deleteDocument(getContentResolver(), entry.uri)) {
                            throw new IllegalStateException("Provider rejected delete");
                        }
                        renderCurrent();
                    } catch (FileNotFoundException | RuntimeException exception) {
                        Toast.makeText(this, R.string.operation_failed, Toast.LENGTH_LONG).show();
                    }
                })
                .setNegativeButton(R.string.cancel, null)
                .show();
    }

    private void openDocument(DocumentEntry entry) {
        Intent intent = new Intent(Intent.ACTION_VIEW)
                .setDataAndType(entry.uri, entry.mime)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            startActivity(intent);
        } catch (ActivityNotFoundException exception) {
            Toast.makeText(this, R.string.open_failed, Toast.LENGTH_LONG).show();
        }
    }

    private void shareDocument(DocumentEntry entry) {
        Intent intent = new Intent(Intent.ACTION_SEND)
                .setType(entry.mime)
                .putExtra(Intent.EXTRA_STREAM, entry.uri)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            startActivity(Intent.createChooser(intent, getString(R.string.share)));
        } catch (ActivityNotFoundException exception) {
            Toast.makeText(this, R.string.share_failed, Toast.LENGTH_LONG).show();
        }
    }

    private Button actionButton(int stringId, View.OnClickListener listener) {
        Button button = actionButtonText(getString(stringId), listener);
        button.setContentDescription(getString(stringId));
        return button;
    }

    private Button actionButtonText(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(15);
        button.setTextColor(getColor(R.color.swir_text_primary));
        button.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        button.setBackgroundColor(getColor(R.color.swir_surface_alt));
        button.setMinHeight(touchMin());
        button.setOnClickListener(listener);
        return button;
    }

    private TextView text(int resId, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(resId);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams weighted() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        params.setMargins(dp(2), 0, dp(2), 0);
        return params;
    }

    private int touchMin() {
        return getResources().getDimensionPixelSize(R.dimen.swir_touch_min);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private interface NameAction { void run(String name); }

    private static final class ClipboardItem {
        final Uri uri;
        final Uri parentUri;
        final String name;
        final boolean move;

        ClipboardItem(Uri uri, Uri parentUri, String name, boolean move) {
            this.uri = uri;
            this.parentUri = parentUri;
            this.name = name;
            this.move = move;
        }
    }

    private static final class DocumentEntry {
        final Uri uri;
        final String name;
        final String mime;
        final long size;
        final long flags;
        final boolean directory;

        DocumentEntry(Uri uri, String name, String mime, long size, long flags) {
            this.uri = uri;
            this.name = name == null ? "" : name;
            this.mime = mime == null ? "application/octet-stream" : mime;
            this.size = size;
            this.flags = flags;
            this.directory = DocumentsContract.Document.MIME_TYPE_DIR.equals(mime);
        }
    }
}
