package org.swir.phoneos.contacts;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentResolver;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.ContactsContract;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;

public final class MainActivity extends Activity {
    private static final int PERMISSION_CONTACTS = 40;
    private static final int IMPORT_VCARD = 41;
    private static final int EXPORT_VCARD = 42;
    private final List<ContactRow> all = new ArrayList<>();
    private final List<ContactRow> shown = new ArrayList<>();
    private ArrayAdapter<String> adapter;
    private EditText search;
    private ContactRow pendingExport;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 28, 28, 28);
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.addView(text(R.string.title, 28));
        root.addView(text(R.string.subtitle, 15));
        search = new EditText(this);
        search.setHint(R.string.search_hint);
        search.setTextColor(Color.WHITE);
        search.setHintTextColor(Color.rgb(130, 170, 190));
        search.setSingleLine(true);
        root.addView(search);
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        Button add = button(R.string.add_contact);
        Button imported = button(R.string.import_vcard);
        actions.addView(add, new LinearLayout.LayoutParams(0, -2, 1));
        actions.addView(imported, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(actions);
        ListView list = new ListView(this);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, new ArrayList<>());
        list.setAdapter(adapter);
        root.addView(list, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        search.addTextChangedListener(new SimpleTextWatcher(this::filter));
        add.setOnClickListener(v -> createContact());
        imported.setOnClickListener(v -> pickVcard());
        list.setOnItemClickListener((parent, view, position, id) -> {
            if (position < shown.size()) editContact(shown.get(position));
        });
        list.setOnItemLongClickListener((parent, view, position, id) -> {
            if (position < shown.size()) confirmExport(shown.get(position));
            return true;
        });
        ensurePermission();
    }

    private TextView text(int id, int sp) {
        TextView view = new TextView(this);
        view.setText(id);
        view.setTextSize(sp);
        view.setTextColor(Color.WHITE);
        view.setPadding(0, 6, 0, 10);
        return view;
    }

    private Button button(int id) {
        Button button = new Button(this);
        button.setText(id);
        return button;
    }

    private void ensurePermission() {
        if (checkSelfPermission(Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED) {
            loadContacts();
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle(R.string.permission_title)
                .setMessage(R.string.permission_body)
                .setPositiveButton(R.string.permission_grant, (dialog, which) ->
                        requestPermissions(new String[]{Manifest.permission.READ_CONTACTS}, PERMISSION_CONTACTS))
                .setNegativeButton(android.R.string.cancel, null)
                .show();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == PERMISSION_CONTACTS && results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) loadContacts();
    }

    private void loadContacts() {
        all.clear();
        ContentResolver resolver = getContentResolver();
        String[] columns = {ContactsContract.Contacts._ID, ContactsContract.Contacts.LOOKUP_KEY, ContactsContract.Contacts.DISPLAY_NAME_PRIMARY};
        try (Cursor cursor = resolver.query(ContactsContract.Contacts.CONTENT_URI, columns, null, null,
                ContactsContract.Contacts.DISPLAY_NAME_PRIMARY + " COLLATE LOCALIZED ASC")) {
            if (cursor != null) {
                while (cursor.moveToNext()) {
                    long id = cursor.getLong(0);
                    String lookup = cursor.getString(1);
                    String name = cursor.getString(2);
                    String phone = firstPhone(resolver, id);
                    if (ContactPolicy.validLookupKey(lookup)) all.add(new ContactRow(id, lookup, name == null ? "" : name, phone));
                }
            }
        }
        filter();
    }

    private String firstPhone(ContentResolver resolver, long contactId) {
        String selection = ContactsContract.CommonDataKinds.Phone.CONTACT_ID + "=?";
        try (Cursor cursor = resolver.query(ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                new String[]{ContactsContract.CommonDataKinds.Phone.NUMBER}, selection,
                new String[]{Long.toString(contactId)}, null)) {
            return cursor != null && cursor.moveToFirst() ? cursor.getString(0) : "";
        }
    }

    private void filter() {
        String query = search == null ? "" : search.getText().toString();
        shown.clear();
        ArrayList<String> labels = new ArrayList<>();
        for (ContactRow row : all) {
            if (ContactPolicy.matches(row.name, row.phone, query)) {
                shown.add(row);
                labels.add(row.phone.isEmpty() ? row.name : row.name + "\n" + row.phone);
            }
        }
        if (labels.isEmpty()) labels.add(getString(R.string.no_contacts));
        adapter.clear();
        adapter.addAll(labels);
        adapter.notifyDataSetChanged();
    }

    private Uri contactUri(ContactRow row) {
        return ContactsContract.Contacts.getLookupUri(row.id, row.lookupKey);
    }

    private void createContact() {
        Intent intent = new Intent(Intent.ACTION_INSERT);
        intent.setType(ContactsContract.RawContacts.CONTENT_TYPE);
        launch(intent);
    }

    private void editContact(ContactRow row) {
        Intent intent = new Intent(Intent.ACTION_EDIT, contactUri(row));
        intent.putExtra("finishActivityOnSaveCompleted", true);
        launch(intent);
    }

    private void pickVcard() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("text/vcard");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(intent, IMPORT_VCARD);
    }

    private void confirmExport(ContactRow row) {
        pendingExport = row;
        new AlertDialog.Builder(this)
                .setTitle(R.string.export_contact)
                .setMessage(row.name)
                .setPositiveButton(R.string.export_contact, (dialog, which) -> pickExportTarget())
                .setNegativeButton(android.R.string.cancel, null)
                .show();
    }

    private void pickExportTarget() {
        if (pendingExport == null) return;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType("text/vcard");
        intent.putExtra(Intent.EXTRA_TITLE, ContactPolicy.vcardFileName(pendingExport.name));
        startActivityForResult(intent, EXPORT_VCARD);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        if (requestCode == IMPORT_VCARD) {
            Intent view = new Intent(Intent.ACTION_VIEW, data.getData());
            view.setDataAndType(data.getData(), "text/vcard");
            view.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            launch(view);
        } else if (requestCode == EXPORT_VCARD && pendingExport != null) {
            exportVcard(pendingExport, data.getData());
        }
    }

    private void exportVcard(ContactRow row, Uri destination) {
        Uri source = Uri.withAppendedPath(ContactsContract.Contacts.CONTENT_VCARD_URI, row.lookupKey);
        try (InputStream input = getContentResolver().openInputStream(source);
             OutputStream output = getContentResolver().openOutputStream(destination, "w")) {
            if (input == null || output == null) throw new IllegalStateException();
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
            output.flush();
        } catch (Exception error) {
            Toast.makeText(this, R.string.error_export, Toast.LENGTH_LONG).show();
        } finally {
            pendingExport = null;
        }
    }

    private void launch(Intent intent) {
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.error_no_handler, Toast.LENGTH_LONG).show();
    }

    @Override protected void onResume() {
        super.onResume();
        if (search != null && checkSelfPermission(Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED) loadContacts();
    }

    private static final class ContactRow {
        final long id;
        final String lookupKey;
        final String name;
        final String phone;
        ContactRow(long id, String lookupKey, String name, String phone) {
            this.id = id;
            this.lookupKey = lookupKey;
            this.name = name;
            this.phone = phone == null ? "" : phone;
        }
    }

    private static final class SimpleTextWatcher implements android.text.TextWatcher {
        private final Runnable action;
        SimpleTextWatcher(Runnable action) { this.action = action; }
        public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
        public void onTextChanged(CharSequence s, int start, int before, int count) { action.run(); }
        public void afterTextChanged(android.text.Editable editable) {}
    }
}
