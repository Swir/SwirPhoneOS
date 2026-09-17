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
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/** Owner-visible dial pad. Source stage deliberately hands calls to Android's dialer UI. */
public final class MainActivity extends Activity {
    private EditText number;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(4, 11, 23));
        getWindow().setNavigationBarColor(Color.rgb(4, 11, 23));
        setContentView(buildUi());
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

        number = new EditText(this);
        number.setHint(R.string.number_hint);
        number.setHintTextColor(Color.rgb(140, 160, 181));
        number.setTextColor(Color.WHITE);
        number.setTextSize(24);
        number.setGravity(Gravity.CENTER);
        number.setSingleLine(true);
        number.setInputType(InputType.TYPE_CLASS_PHONE);
        number.setContentDescription(getString(R.string.number_hint));
        root.addView(number, spaced());

        GridLayout keypad = new GridLayout(this);
        keypad.setColumnCount(3);
        keypad.setRowCount(4);
        String[] keys = {"1","2","3","4","5","6","7","8","9","*","0","#"};
        for (String key : keys) {
            Button value = buttonText(key);
            value.setOnClickListener(v -> number.setText(DialPolicy.append(number.getText().toString(), key)));
            GridLayout.LayoutParams params = new GridLayout.LayoutParams();
            params.width = 0;
            params.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
            params.setMargins(dp(4), dp(4), dp(4), dp(4));
            keypad.addView(value, params);
        }
        root.addView(keypad, spaced());

        LinearLayout editActions = row();
        Button backspace = button(R.string.backspace);
        backspace.setOnClickListener(v -> number.setText(DialPolicy.backspace(number.getText().toString())));
        Button clear = button(R.string.clear);
        clear.setOnClickListener(v -> number.setText(""));
        editActions.addView(backspace, weighted());
        editActions.addView(clear, weighted());
        root.addView(editActions, matchWrap());

        Button dial = button(R.string.dial);
        dial.setOnClickListener(v -> openDialer());
        root.addView(dial, spaced());

        Button contacts = button(R.string.open_contacts);
        contacts.setOnClickListener(v -> openContacts());
        root.addView(contacts, spaced());

        TextView note = text(getString(R.string.handoff_note), 13, Color.rgb(180, 198, 217));
        root.addView(note, spaced());
        TextView footer = text(getString(R.string.footer), 12, Color.rgb(140, 160, 181));
        footer.setOnClickListener(v -> openGitHub());
        root.addView(footer, matchWrap());
        return scroll;
    }

    private void openDialer() {
        String value = DialPolicy.normalize(number.getText().toString());
        if (!DialPolicy.valid(value)) {
            Toast.makeText(this, R.string.invalid_number, Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(Intent.ACTION_DIAL, Uri.fromParts("tel", value, null));
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.dial_unavailable, Toast.LENGTH_SHORT).show();
    }

    private void openContacts() {
        Intent intent = new Intent();
        intent.setClassName("org.swir.phoneos.contacts", "org.swir.phoneos.contacts.MainActivity");
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
        else Toast.makeText(this, R.string.contacts_unavailable, Toast.LENGTH_SHORT).show();
    }

    private void openGitHub() {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/Swir"));
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private LinearLayout row() { LinearLayout value = new LinearLayout(this); value.setOrientation(LinearLayout.HORIZONTAL); return value; }
    private Button button(int label) { Button value = buttonText(getString(label)); value.setAllCaps(false); return value; }
    private Button buttonText(String label) { Button value = new Button(this); value.setText(label); value.setTextColor(Color.WHITE); value.setBackgroundColor(Color.rgb(17, 61, 92)); value.setMinHeight(dp(52)); return value; }
    private TextView text(String value, int sp, int color) { TextView view = new TextView(this); view.setText(value); view.setTextSize(sp); view.setTextColor(color); return view; }
    private LinearLayout.LayoutParams matchWrap() { return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT); }
    private LinearLayout.LayoutParams spaced() { LinearLayout.LayoutParams params = matchWrap(); params.setMargins(0, 0, 0, dp(12)); return params; }
    private LinearLayout.LayoutParams weighted() { LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f); params.setMargins(dp(3), dp(6), dp(3), 0); return params; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
