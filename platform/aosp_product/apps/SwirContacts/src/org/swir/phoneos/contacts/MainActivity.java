package org.swir.phoneos.contacts;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.Editable;
import android.text.InputType;
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
import java.util.ArrayList;

/** App-private contacts with explicit dial/email handoffs and owner-selected vCard export. */
public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 6201;
    private final ArrayList<ContactItem> contacts = new ArrayList<>();
    private ContactsDb db;
    private LinearLayout contactList;
    private EditText search;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(4, 11, 23));
        getWindow().setNavigationBarColor(Color.rgb(4, 11, 23));
        db = new ContactsDb();
        setContentView(buildUi());
        refreshContacts();
    }

    @Override protected void onDestroy() {
        if (db != null) db.close();
        super.onDestroy();
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != EXPORT_REQUEST || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        try (OutputStream out = getContentResolver().openOutputStream(data.getData())) {
            if (out == null) throw new IOException();
            out.write(exportAll().getBytes(StandardCharsets.UTF_8));
            Toast.makeText(this, R.string.export_complete, Toast.LENGTH_SHORT).show();
        } catch (IOException error) {
            Toast.makeText(this, R.string.export_failed, Toast.LENGTH_LONG).show();
        }
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(28));
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(text(getString(R.string.app_name), 28, Color.rgb(105, 216, 255)), matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, Color.rgb(180, 198, 217));
        subtitle.setPadding(0, dp(4), 0, dp(12));
        root.addView(subtitle, matchWrap());
        search = new EditText(this);
        search.setHint(R.string.search_hint);
        search.setHintTextColor(Color.rgb(140, 160, 181));
        search.setTextColor(Color.WHITE);
        search.setSingleLine(true);
        search.setContentDescription(getString(R.string.search_hint));
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { renderContacts(); }
            @Override public void afterTextChanged(Editable s) {}
        });
        root.addView(search, spaced());
        LinearLayout actions = row();
        Button add = button(R.string.new_contact);
        add.setOnClickListener(v -> showCreateDialog());
        Button export = button(R.string.export_vcard);
        export.setOnClickListener(v -> requestExport());
        actions.addView(add, weighted()); actions.addView(export, weighted());
        root.addView(actions, spaced());
        contactList = new LinearLayout(this);
        contactList.setOrientation(LinearLayout.VERTICAL);
        root.addView(contactList, matchWrap());
        TextView footer = text(getString(R.string.footer), 12, Color.rgb(140, 160, 181));
        footer.setPadding(0, dp(16), 0, 0);
        footer.setOnClickListener(v -> openGitHub());
        root.addView(footer, matchWrap());
        return scroll;
    }

    private void refreshContacts() {
        contacts.clear();
        try (Cursor cursor = db.getReadableDatabase().query("contacts", new String[]{"id","name","phone","email"}, null, null, null, null, "name COLLATE NOCASE ASC")) {
            while (cursor.moveToNext()) contacts.add(new ContactItem(cursor.getLong(0), cursor.getString(1), cursor.getString(2), cursor.getString(3)));
        }
        renderContacts();
    }

    private void renderContacts() {
        if (contactList == null) return;
        contactList.removeAllViews();
        String query = search == null ? "" : search.getText().toString();
        int shown = 0;
        for (ContactItem item : contacts) {
            if (!ContactPolicy.matches(query, item.name, item.phone, item.email)) continue;
            contactList.addView(contactCard(item), spaced()); shown++;
        }
        if (shown == 0) contactList.addView(text(getString(R.string.empty), 14, Color.rgb(180, 198, 217)), spaced());
    }

    private View contactCard(ContactItem item) {
        LinearLayout card = card();
        card.addView(text(item.name, 17, Color.WHITE), matchWrap());
        if (!item.phone.isEmpty()) card.addView(text(item.phone, 13, Color.rgb(180, 198, 217)), matchWrap());
        if (!item.email.isEmpty()) card.addView(text(item.email, 13, Color.rgb(180, 198, 217)), matchWrap());
        LinearLayout actions = row();
        Button call = button(R.string.call); call.setEnabled(!item.phone.isEmpty()); call.setOnClickListener(v -> dial(item.phone));
        Button email = button(R.string.email); email.setEnabled(!item.email.isEmpty()); email.setOnClickListener(v -> email(item.email));
        Button delete = button(R.string.delete); delete.setOnClickListener(v -> confirmDelete(item));
        actions.addView(call, weighted()); actions.addView(email, weighted()); actions.addView(delete, weighted());
        card.addView(actions, matchWrap());
        return card;
    }

    private void showCreateDialog() {
        LinearLayout body = new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL); body.setPadding(dp(18), 0, dp(18), 0);
        EditText name = field(R.string.name_hint, InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_WORDS);
        EditText phone = field(R.string.phone_hint, InputType.TYPE_CLASS_PHONE);
        EditText email = field(R.string.email_hint, InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        body.addView(name); body.addView(phone); body.addView(email);
        new AlertDialog.Builder(this).setTitle(R.string.new_contact).setView(body).setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.save, (dialog, which) -> saveContact(name.getText().toString(), phone.getText().toString(), email.getText().toString())).show();
    }

    private void saveContact(String nameRaw, String phoneRaw, String emailRaw) {
        String name = ContactPolicy.normalizeName(nameRaw), phone = ContactPolicy.normalizePhone(phoneRaw), email = ContactPolicy.normalizeEmail(emailRaw);
        if (!ContactPolicy.validContact(name, phone, email)) { Toast.makeText(this, R.string.invalid_contact, Toast.LENGTH_SHORT).show(); return; }
        ContentValues values = new ContentValues(); values.put("name", name); values.put("phone", phone); values.put("email", email);
        long id = db.getWritableDatabase().insert("contacts", null, values);
        Toast.makeText(this, id >= 0 ? R.string.saved : R.string.save_failed, Toast.LENGTH_SHORT).show(); refreshContacts();
    }

    private void confirmDelete(ContactItem item) {
        new AlertDialog.Builder(this).setTitle(R.string.delete_title).setMessage(R.string.delete_message).setNegativeButton(R.string.cancel, null)
                .setPositiveButton(R.string.delete, (dialog, which) -> {
                    int changed = db.getWritableDatabase().delete("contacts", "id=?", new String[]{Long.toString(item.id)});
                    Toast.makeText(this, changed > 0 ? R.string.delete_complete : R.string.delete_failed, Toast.LENGTH_SHORT).show(); refreshContacts();
                }).show();
    }

    private void requestExport() {
        if (contacts.isEmpty()) { Toast.makeText(this, R.string.empty, Toast.LENGTH_SHORT).show(); return; }
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("text/vcard").putExtra(Intent.EXTRA_TITLE, getString(R.string.export_filename));
        startActivityForResult(intent, EXPORT_REQUEST);
    }

    private String exportAll() { StringBuilder out = new StringBuilder(); for (ContactItem item : contacts) out.append(ContactPolicy.toVCard(item.name, item.phone, item.email)); return out.toString(); }
    private void dial(String phone) { startIfAvailable(new Intent(Intent.ACTION_DIAL, Uri.fromParts("tel", ContactPolicy.normalizePhone(phone), null))); }
    private void email(String address) { startIfAvailable(new Intent(Intent.ACTION_SENDTO, Uri.fromParts("mailto", ContactPolicy.normalizeEmail(address), null))); }
    private void startIfAvailable(Intent intent) { if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent); else Toast.makeText(this, R.string.action_unavailable, Toast.LENGTH_SHORT).show(); }
    private void openGitHub() { startIfAvailable(new Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/Swir"))); }
    private EditText field(int hint, int inputType) { EditText value = new EditText(this); value.setHint(hint); value.setInputType(inputType); value.setSingleLine(true); return value; }
    private LinearLayout card() { LinearLayout value = new LinearLayout(this); value.setOrientation(LinearLayout.VERTICAL); value.setPadding(dp(14), dp(14), dp(14), dp(14)); value.setBackgroundColor(Color.rgb(13, 34, 55)); return value; }
    private LinearLayout row() { LinearLayout value = new LinearLayout(this); value.setOrientation(LinearLayout.HORIZONTAL); return value; }
    private Button button(int label) { Button value = new Button(this); value.setAllCaps(false); value.setText(label); value.setTextColor(Color.WHITE); value.setBackgroundColor(Color.rgb(17, 61, 92)); value.setMinHeight(dp(48)); return value; }
    private TextView text(String value, int sp, int color) { TextView view = new TextView(this); view.setText(value); view.setTextSize(sp); view.setTextColor(color); return view; }
    private LinearLayout.LayoutParams matchWrap() { return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT); }
    private LinearLayout.LayoutParams spaced() { LinearLayout.LayoutParams params = matchWrap(); params.setMargins(0, 0, 0, dp(12)); return params; }
    private LinearLayout.LayoutParams weighted() { LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f); params.setMargins(dp(3), dp(6), dp(3), 0); return params; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private final class ContactsDb extends SQLiteOpenHelper {
        ContactsDb() { super(MainActivity.this, "swir_contacts.db", null, 1); }
        @Override public void onCreate(SQLiteDatabase database) { database.execSQL("CREATE TABLE contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '')"); }
        @Override public void onUpgrade(SQLiteDatabase database, int oldVersion, int newVersion) {}
    }
    private static final class ContactItem { final long id; final String name, phone, email; ContactItem(long id, String name, String phone, String email) { this.id=id; this.name=name; this.phone=phone; this.email=email; } }
}
