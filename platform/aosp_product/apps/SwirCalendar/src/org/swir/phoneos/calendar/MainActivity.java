package org.swir.phoneos.calendar;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DatePickerDialog;
import android.app.TimePickerDialog;
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
import java.util.Calendar;
import java.util.Date;

public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 51;
    private EventDb db;
    private LinearLayout eventList;
    private EditText search;
    private String pendingExport;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        db = new EventDb(this);
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
        Button add = actionButton(getString(R.string.add_event));
        add.setOnClickListener(v -> {
            long start = System.currentTimeMillis() + 60L * 60L * 1000L;
            showEditor(null, "", "", start, start + EventPolicy.DEFAULT_DURATION_MS);
        });
        root.addView(add);
        eventList = column(10);
        root.addView(eventList);
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

    private String formatWhen(long start, long end) {
        DateFormat date = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT);
        return date.format(new Date(start)) + " — " + date.format(new Date(end));
    }

    private void reload() {
        if (eventList == null) return;
        eventList.removeAllViews();
        String query = search == null ? "" : search.getText().toString();
        int shown = 0;
        try (Cursor cursor = db.getReadableDatabase().query("events",
                new String[]{"id", "title", "location", "start_ms", "end_ms"}, null, null, null, null, "start_ms ASC")) {
            while (cursor.moveToNext()) {
                long id = cursor.getLong(0);
                String title = cursor.getString(1);
                String location = cursor.getString(2);
                long start = cursor.getLong(3);
                long end = cursor.getLong(4);
                if (!EventPolicy.matches(query, title, location)) continue;
                String line = title + "\n" + formatWhen(start, end);
                if (!location.trim().isEmpty()) line += "\n" + location;
                Button row = actionButton(line);
                row.setContentDescription(getString(R.string.open_event, title));
                row.setOnClickListener(v -> showEditor(id, title, location, start, end));
                row.setOnLongClickListener(v -> { showActions(id, title, location, start, end); return true; });
                eventList.addView(row);
                shown++;
            }
        }
        if (shown == 0) eventList.addView(text(getString(R.string.empty_state), 15, Color.LTGRAY));
    }

    private void showEditor(Long id, String oldTitle, String oldLocation, long oldStart, long oldEnd) {
        LinearLayout form = column(12);
        EditText title = new EditText(this);
        title.setHint(R.string.title_hint);
        title.setText(oldTitle);
        form.addView(title);
        EditText location = new EditText(this);
        location.setHint(R.string.location_hint);
        location.setText(oldLocation);
        form.addView(location);
        long[] times = {oldStart, oldEnd};
        Button start = actionButton(getString(R.string.start) + ": " + formatPoint(times[0]));
        Button end = actionButton(getString(R.string.end) + ": " + formatPoint(times[1]));
        start.setOnClickListener(v -> pickDateTime(start, times, 0));
        end.setOnClickListener(v -> pickDateTime(end, times, 1));
        form.addView(start);
        form.addView(end);

        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setTitle(id == null ? R.string.add_event : R.string.edit_event)
                .setView(form)
                .setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.save, null);
        if (id != null) builder.setNeutralButton(R.string.delete, (d, w) -> confirmDelete(id));
        AlertDialog dialog = builder.create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String nextTitle = title.getText().toString().trim();
            String nextLocation = location.getText().toString().trim();
            long nextEnd = EventPolicy.normalizeEnd(times[0], times[1]);
            if (!EventPolicy.validTitle(nextTitle) || !EventPolicy.validLocation(nextLocation) || nextEnd < 0) {
                Toast.makeText(this, R.string.invalid_event, Toast.LENGTH_SHORT).show();
                return;
            }
            ContentValues values = new ContentValues();
            values.put("title", nextTitle);
            values.put("location", nextLocation);
            values.put("start_ms", times[0]);
            values.put("end_ms", nextEnd);
            SQLiteDatabase writable = db.getWritableDatabase();
            if (id == null) writable.insertOrThrow("events", null, values);
            else writable.update("events", values, "id=?", new String[]{Long.toString(id)});
            dialog.dismiss();
            reload();
        }));
        dialog.show();
    }

    private String formatPoint(long millis) {
        return DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(new Date(millis));
    }

    private void pickDateTime(Button button, long[] times, int index) {
        Calendar value = Calendar.getInstance();
        value.setTimeInMillis(times[index]);
        new DatePickerDialog(this, (datePicker, year, month, day) -> {
            Calendar picked = Calendar.getInstance();
            picked.setTimeInMillis(times[index]);
            picked.set(year, month, day);
            new TimePickerDialog(this, (timePicker, hour, minute) -> {
                picked.set(Calendar.HOUR_OF_DAY, hour);
                picked.set(Calendar.MINUTE, minute);
                picked.set(Calendar.SECOND, 0);
                picked.set(Calendar.MILLISECOND, 0);
                times[index] = picked.getTimeInMillis();
                button.setText(getString(index == 0 ? R.string.start : R.string.end) + ": " + formatPoint(times[index]));
            }, value.get(Calendar.HOUR_OF_DAY), value.get(Calendar.MINUTE), android.text.format.DateFormat.is24HourFormat(this)).show();
        }, value.get(Calendar.YEAR), value.get(Calendar.MONTH), value.get(Calendar.DAY_OF_MONTH)).show();
    }

    private void showActions(long id, String title, String location, long start, long end) {
        new AlertDialog.Builder(this).setTitle(R.string.event_actions)
                .setItems(new String[]{getString(R.string.share), getString(R.string.export)}, (d, which) -> {
                    if (which == 0) share(id, title, location, start, end); else export(id, title, location, start, end);
                }).show();
    }

    private String ics(long id, String title, String location, long start, long end) {
        return EventPolicy.toIcs(id + "@swirphoneos.local", title, location, start, end);
    }

    private void share(long id, String title, String location, long start, long end) {
        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("text/calendar");
        intent.putExtra(Intent.EXTRA_SUBJECT, title);
        intent.putExtra(Intent.EXTRA_TEXT, ics(id, title, location, start, end));
        startActivity(Intent.createChooser(intent, getString(R.string.share)));
    }

    private void export(long id, String title, String location, long start, long end) {
        pendingExport = ics(id, title, location, start, end);
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType("text/calendar");
        intent.putExtra(Intent.EXTRA_TITLE, "event-" + id + ".ics");
        startActivityForResult(intent, EXPORT_REQUEST);
    }

    private void confirmDelete(long id) {
        new AlertDialog.Builder(this).setTitle(R.string.delete_title).setMessage(R.string.delete_message)
                .setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.delete, (d, w) -> {
                    db.getWritableDatabase().delete("events", "id=?", new String[]{Long.toString(id)});
                    reload();
                }).show();
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

    private static final class EventDb extends SQLiteOpenHelper {
        EventDb(Context context) { super(context, "swir_calendar.db", null, 1); }
        public void onCreate(SQLiteDatabase db) {
            db.execSQL("CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, location TEXT NOT NULL, start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL)");
        }
        public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {}
    }
}
