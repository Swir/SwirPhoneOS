package org.swir.phoneos.settings;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.os.Build;
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

import java.util.Locale;

/** SwirPhoneOS settings hub using public, authoritative Android settings intents. */
public final class MainActivity extends Activity {
    private LinearLayout results;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_background));
        setContentView(buildUi());
        render("");
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(18));
        root.setBackgroundColor(getColor(R.color.swir_background));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

        TextView title = text(R.string.app_name, 26, getColor(R.color.swir_accent_cyan));
        root.addView(title, matchWrap());

        TextView subtitle = text(R.string.subtitle, 15, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, dp(4), 0, dp(14));
        root.addView(subtitle, matchWrap());

        TextView deviceHeading = text(R.string.device_section, 13, getColor(R.color.swir_accent_cyan));
        root.addView(deviceHeading, matchWrap());

        TextView device = text(
                getString(R.string.device_summary, Build.MODEL, Build.VERSION.RELEASE, Build.VERSION.SDK_INT),
                16,
                getColor(R.color.swir_text_primary));
        device.setPadding(dp(14), dp(14), dp(14), dp(14));
        device.setBackgroundColor(getColor(R.color.swir_surface));
        root.addView(device, matchWrap());

        TextView note = text(R.string.security_note, 12, getColor(R.color.swir_text_secondary));
        note.setPadding(0, dp(10), 0, dp(14));
        root.addView(note, matchWrap());

        EditText search = new EditText(this);
        search.setSingleLine(true);
        search.setHint(R.string.search_hint);
        search.setTextColor(getColor(R.color.swir_text_primary));
        search.setHintTextColor(getColor(R.color.swir_text_secondary));
        search.setBackgroundColor(getColor(R.color.swir_surface));
        search.setPadding(dp(14), dp(12), dp(14), dp(12));
        search.setMinHeight(touchMin());
        search.setContentDescription(getString(R.string.search_hint));
        root.addView(search, matchWrap());

        ScrollView scroll = new ScrollView(this);
        results = new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        results.setPadding(0, dp(10), 0, dp(12));
        scroll.addView(results, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { render(s.toString()); }
            @Override public void afterTextChanged(Editable s) {}
        });
        return root;
    }

    private void render(String query) {
        results.removeAllViews();
        String localizedNeedle = query == null ? "" : query.trim().toLowerCase(Locale.getDefault());
        int shown = 0;
        for (SettingsCatalog.Entry entry : SettingsCatalog.entries()) {
            int labelRes = labelFor(entry.id());
            String label = getString(labelRes);
            if (!SettingsCatalog.matches(entry, query)
                    && !label.toLowerCase(Locale.getDefault()).contains(localizedNeedle)) {
                continue;
            }
            Button button = new Button(this);
            button.setAllCaps(false);
            button.setText(label);
            button.setTextSize(17);
            button.setTextColor(getColor(R.color.swir_text_primary));
            button.setGravity(android.view.Gravity.START | android.view.Gravity.CENTER_VERTICAL);
            button.setBackgroundColor(getColor(R.color.swir_surface_alt));
            button.setMinHeight(touchMin());
            button.setContentDescription(label);
            button.setOnClickListener(v -> open(entry));
            LinearLayout.LayoutParams params = matchWrap();
            params.setMargins(0, dp(5), 0, dp(5));
            results.addView(button, params);
            shown++;
        }
        if (shown == 0) {
            TextView empty = text(R.string.no_results, 15, getColor(R.color.swir_text_secondary));
            empty.setPadding(dp(4), dp(18), dp(4), dp(18));
            results.addView(empty, matchWrap());
        }
    }

    private void open(SettingsCatalog.Entry entry) {
        try {
            startActivity(new Intent(entry.action()));
        } catch (ActivityNotFoundException exception) {
            Toast.makeText(this, R.string.open_failed, Toast.LENGTH_SHORT).show();
        }
    }

    private int labelFor(String id) {
        switch (id) {
            case "wifi": return R.string.wifi;
            case "bluetooth": return R.string.bluetooth;
            case "display": return R.string.display;
            case "sound": return R.string.sound;
            case "security": return R.string.security;
            case "privacy": return R.string.privacy;
            case "accessibility": return R.string.accessibility;
            case "language_region": return R.string.language_region;
            case "storage": return R.string.storage;
            case "apps": return R.string.apps;
            default: throw new IllegalArgumentException("Unknown settings entry: " + id);
        }
    }

    private TextView text(int resId, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(resId);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private int touchMin() {
        return getResources().getDimensionPixelSize(R.dimen.swir_touch_min);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
