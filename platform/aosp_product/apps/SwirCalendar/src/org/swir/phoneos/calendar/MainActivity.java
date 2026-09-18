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
import android.net.Uri;
import android.os.Bundle;
import android.provider.CalendarContract;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.text.DateFormat;
import java.util.Calendar;
import java.util.Date;

public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 51;
    private static final int IMPORT_REQUEST = 52;
    private EventDb db;
    private LinearLayout eventList;
    private EditText search;
    private String pendingExport;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        db = new EventDb(this);
        setTitle(R.string.app_name);
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_surface));
        setContentView(buildUi());
        reload();
    }

    private View buildUi() {
        int spaceXs = getResources().getDimensionPixelSize(R.dimen.swir_space_xs);
        int spaceSm = getResources().getDimensionPixelSize(R.dimen.swir_space_sm);
        int spaceMd = getResources().getDimensionPixelSize(R.dimen.swir_space_md);

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(getColor(R.color.swir_background));
        LinearLayout root = column(spaceMd);
        scroll.addView(root);

        TextView title = text(getString(R.string.app_name), 30, getColor(R.color.swir_text_primary));
        title.setPadding(0, spaceXs, 0, spaceXs);
        root.addView(title);
        TextView subtitle = text(getString(R.string.subtitle), 15, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, 0, 0, spaceSm);
        root.addView(subtitle);

        search = new EditText(this);
        search.setHint(R.string.search_hint);
        search.setTextColor(getColor(R.color.swir_text_primary));
        search.setHintTextColor(getColor(R.color.swir_text_secondary));
        search.setSingleLine(true);
        search.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
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

        Button importEvent = actionButton(getString(R.string.import_event));
        importEvent.setOnClickListener(v -> chooseImport());
        root.addView(importEvent);

        eventList = column(spaceSm);
        root.addView(eventList);
        return scroll;
    }

    private LinearLayout column(int paddingPx) {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(paddingPx, paddingPx, paddingPx, paddingPx);
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
        button.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
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
        if (shown == 0) {
            TextView empty = text(getString(R.string.empty_state), 15, getColor(R.color.swir_text_secondary));
            eventList.addView(empty);
        }
    }

    private void showEditor(Long id, String oldTitle, String oldLocation, long oldStart, long oldEnd) {
        int spaceSm = getResources().getDimensionPixelSize(R.dimen.swir_space_sm);
        LinearLayout form = column(spaceSm);
        EditText title = new EditText(this);
        title.setHint(R.string.title_hint);
        title.setText(oldTitle);
        title.setTextColor(getColor(R.color.swir_text_primary));
        title.setHintTextColor(getColor(R.color.swir_text_secondary));
        title.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        form.addView(title);
        EditText location = new EditText(this);
        location.setHint(R.string.location_hint);
        location.setText(oldLocation);
        location.setTextColor(getColor(R.color.swir_text_primary));
        location.setHintTextColor(getColor(R.color.swir_text_secondary));
        location.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
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
            ContentValues values = eventValues(nextTitle, nextLocation, times[0], nextEnd);
            SQLiteDatabase writable = db.getWritableDatabase();
            if (id == null) writable.insertOrThrow("events", null, values);
            else writable.update("events", values, "id=?", new String[]{Long.toString(id)});
            dialog.dismiss();
            reload();
        }));
        dialog.show();
    }

    private static ContentValues eventValues(String title, String location, long start, long end) {
        ContentValues values = new ContentValues();
        values.put("title", title);
        values.put("location", location);
        values.put("start_ms", start);
        values.put("end_ms", end);
        return values;
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
                .setItems(new String[]{
                        getString(R.string.share),
                        getString(R.string.export),
                        getString(R.string.add_to_device_calendar)
                }, (d, which) -> {
                    if (which == 0) share(id, title, location, start, end);
                    else if (which == 1) export(id, title, location, start, end);
                    else addToDeviceCalendar(title, location, start, end);
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

    private void chooseImport() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("text/calendar");
        startActivityForResult(intent, IMPORT_REQUEST);
    }

    private void importLocalEvent(Uri uri) {
        try {
            String source = readUtf8Bounded(uri, EventPolicy.MAX_ICS_BYTES);
            EventPolicy.ImportedEvent imported = EventPolicy.parseSingleEvent(source);
            if (imported == null) throw new IllegalArgumentException("unsupported calendar file");
            db.getWritableDatabase().insertOrThrow("events", null, eventValues(
                    imported.title(), imported.location(), imported.startMillis(), imported.endMillis()));
            Toast.makeText(this, R.string.imported_event, Toast.LENGTH_SHORT).show();
            reload();
        } catch (Exception error) {
            Toast.makeText(this, R.string.import_failed, Toast.LENGTH_LONG).show();
        }
    }

    private String readUtf8Bounded(Uri uri, int maxBytes) throws Exception {
        try (InputStream input = getContentResolver().openInputStream(uri);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            if (input == null) throw new IOException("no input stream");
            byte[] buffer = new byte[8192];
            int total = 0;
            int read;
            while ((read = input.read(buffer)) != -1) {
                total += read;
                if (total > maxBytes) throw new IOException("calendar file too large");
                output.write(buffer, 0, read);
            }
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(output.toByteArray()))
                    .toString();
        }
    }

    private void addToDeviceCalendar(String title, String location, long start, long end) {
        Intent intent = new Intent(Intent.ACTION_INSERT);
        intent.setData(CalendarContract.Events.CONTENT_URI);
        intent.putExtra(CalendarContract.Events.TITLE, title);
        intent.putExtra(CalendarContract.Events.EVENT_LOCATION, location);
        intent.putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, start);
        intent.putExtra(CalendarContract.EXTRA_EVENT_END_TIME, end);
        if (intent.resolveActivity(getPackageManager()) == null) {
            Toast.makeText(this, R.string.device_calendar_unavailable, Toast.LENGTH_LONG).show();
            return;
        }
        startActivity(intent);
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
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        if (requestCode == IMPORT_REQUEST) {
            importLocalEvent(uri);
            return;
        }
        if (requestCode != EXPORT_REQUEST || pendingExport == null) return;
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
