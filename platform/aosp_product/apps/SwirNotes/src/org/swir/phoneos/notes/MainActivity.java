package org.swir.phoneos.notes;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.DateFormat;
import java.util.Date;

public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 41;
    private NoteDb db;
    private LinearLayout notesList;
    private EditText search;
    private String pendingExport;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        db = new NoteDb(this);
        setContentView(buildUi());
        reload();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Color.rgb(7, 16, 29));
        LinearLayout root = column(24);
        scroll.addView(root);
        root.addView(text(getString(R.string.app_name), 30, Color.WHITE));
        root.addView(text(getString(R.string.subtitle), 15, Color.rgb(122, 214, 255)));
        search = new EditText(this);
        search.setHint(R.string.search_hint);
        search.setTextColor(Color.WHITE);
        search.setHintTextColor(Color.rgb(125, 143, 161));
        search.setSingleLine(true);
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) { reload(); }
            public void afterTextChanged(Editable s) {}
        });
        root.addView(search);
        Button add = actionButton(getString(R.string.add_note));
        add.setOnClickListener(v -> showEditor(null, "", ""));
        root.addView(add);
        notesList = column(10);
        root.addView(notesList);
        return scroll;
    }

    private LinearLayout column(int padding) {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(padding, padding, padding, padding);
        return layout;
    }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private Button actionButton(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        return button;
    }

    private void reload() {
        if (notesList == null) return;
        notesList.removeAllViews();
        String query = search == null ? "" : search.getText().toString();
        int shown = 0;
        try (Cursor cursor = db.getReadableDatabase().query("notes",
                new String[]{"id", "title", "body", "updated_at"}, null, null, null, null, "updated_at DESC")) {
            while (cursor.moveToNext()) {
                long id = cursor.getLong(0);
                String title = cursor.getString(1);
                String body = cursor.getString(2);
                long updated = cursor.getLong(3);
                if (!NotePolicy.matches(query, title, body)) continue;
                String display = NotePolicy.normalizedTitle(title);
                if (display.isEmpty()) display = getString(R.string.untitled);
                String stamp = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(new Date(updated));
                Button row = actionButton(display + "\n" + stamp);
                row.setContentDescription(getString(R.string.open_note, display));
                row.setOnClickListener(v -> showEditor(id, title, body));
                row.setOnLongClickListener(v -> { showActions(title, body); return true; });
                notesList.addView(row);
                shown++;
            }
        }
        if (shown == 0) notesList.addView(text(getString(R.string.empty_state), 15, Color.LTGRAY));
    }

    private void showEditor(Long id, String oldTitle, String oldBody) {
        LinearLayout form = column(12);
        EditText title = new EditText(this);
        title.setHint(R.string.title_hint);
        title.setSingleLine(true);
        title.setText(oldTitle);
        form.addView(title);
        EditText body = new EditText(this);
        body.setHint(R.string.body_hint);
        body.setMinLines(7);
        body.setText(oldBody);
        form.addView(body);
        if (id != null) {
            Button actions = actionButton(getString(R.string.note_actions));
            actions.setOnClickListener(v -> showActions(title.getText().toString(), body.getText().toString()));
            form.addView(actions);
        }

        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setTitle(id == null ? R.string.add_note : R.string.edit_note)
                .setView(form)
                .setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.save, null);
        if (id != null) builder.setNeutralButton(R.string.delete, (dialog, which) -> confirmDelete(id));
        AlertDialog dialog = builder.create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String nextTitle = title.getText().toString();
            String nextBody = body.getText().toString();
            if (!NotePolicy.validNote(nextTitle, nextBody)) {
                Toast.makeText(this, R.string.invalid_note, Toast.LENGTH_SHORT).show();
                return;
            }
            ContentValues values = new ContentValues();
            values.put("title", NotePolicy.normalizedTitle(nextTitle));
            values.put("body", nextBody);
            values.put("updated_at", System.currentTimeMillis());
            SQLiteDatabase writable = db.getWritableDatabase();
            if (id == null) writable.insertOrThrow("notes", null, values);
            else writable.update("notes", values, "id=?", new String[]{Long.toString(id)});
            dialog.dismiss();
            reload();
        }));
        dialog.show();
    }

    private void showActions(String title, String body) {
        new AlertDialog.Builder(this)
                .setTitle(R.string.note_actions)
                .setItems(new String[]{getString(R.string.share), getString(R.string.export)}, (d, which) -> {
                    if (which == 0) share(title, body); else export(title, body);
                }).show();
    }

    private void confirmDelete(long id) {
        new AlertDialog.Builder(this)
                .setTitle(R.string.delete_title)
                .setMessage(R.string.delete_message)
                .setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.delete, (d, w) -> {
                    db.getWritableDatabase().delete("notes", "id=?", new String[]{Long.toString(id)});
                    reload();
                }).show();
    }

    private void share(String title, String body) {
        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("text/plain");
        intent.putExtra(Intent.EXTRA_SUBJECT, NotePolicy.normalizedTitle(title));
        intent.putExtra(Intent.EXTRA_TEXT, NotePolicy.exportMarkdown(title, body));
        startActivity(Intent.createChooser(intent, getString(R.string.share)));
    }

    private void export(String title, String body) {
        pendingExport = NotePolicy.exportMarkdown(title, body);
        String base = NotePolicy.safeExportBase(title);
        if (base.isEmpty()) base = getString(R.string.untitled);
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType("text/markdown");
        intent.putExtra(Intent.EXTRA_TITLE, base + ".md");
        startActivityForResult(intent, EXPORT_REQUEST);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != EXPORT_REQUEST || resultCode != RESULT_OK || data == null || data.getData() == null || pendingExport == null) return;
        Uri uri = data.getData();
        try (OutputStream out = getContentResolver().openOutputStream(uri, "w")) {
            if (out == null) throw new IOException("no output stream");
            out.write(pendingExport.getBytes(StandardCharsets.UTF_8));
            Toast.makeText(this, R.string.exported, Toast.LENGTH_SHORT).show();
        } catch (IOException exc) {
            Toast.makeText(this, R.string.export_failed, Toast.LENGTH_SHORT).show();
        } finally {
            pendingExport = null;
        }
    }

    @Override
    protected void onDestroy() {
        db.close();
        super.onDestroy();
    }

    private static final class NoteDb extends SQLiteOpenHelper {
        NoteDb(Context context) { super(context, "swir_notes.db", null, 1); }
        public void onCreate(SQLiteDatabase db) {
            db.execSQL("CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL, updated_at INTEGER NOT NULL)");
        }
        public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {}
    }
}
