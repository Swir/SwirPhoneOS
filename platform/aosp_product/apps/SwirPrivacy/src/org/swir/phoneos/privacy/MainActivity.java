package org.swir.phoneos.privacy;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Permission-free privacy center that routes only to reviewed Android settings surfaces. */
public final class MainActivity extends Activity {
    private LinearLayout cards;
    private EditText search;

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

        root.addView(text(getString(R.string.app_name), 26, getColor(R.color.swir_accent_cyan)), matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, dp(4), 0, dp(10));
        root.addView(subtitle, matchWrap());

        search = new EditText(this);
        search.setHint(R.string.search_hint);
        search.setTextColor(getColor(R.color.swir_text_primary));
        search.setHintTextColor(getColor(R.color.swir_text_secondary));
        search.setBackgroundColor(getColor(R.color.swir_surface));
        search.setSingleLine(true);
        search.setMinHeight(touchMin());
        search.setContentDescription(getString(R.string.search_hint));
        root.addView(search, matchWrap());

        Button searchButton = new Button(this);
        searchButton.setAllCaps(false);
        searchButton.setText(R.string.search);
        searchButton.setTextColor(getColor(R.color.swir_text_primary));
        searchButton.setBackgroundColor(getColor(R.color.swir_surface_alt));
        searchButton.setMinHeight(touchMin());
        searchButton.setOnClickListener(v -> render(search.getText().toString()));
        root.addView(searchButton, matchWrap());

        ScrollView scroll = new ScrollView(this);
        cards = new LinearLayout(this);
        cards.setOrientation(LinearLayout.VERTICAL);
        cards.setPadding(0, dp(8), 0, dp(16));
        scroll.addView(cards, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return root;
    }

    private void render(String query) {
        cards.removeAllViews();
        for (PrivacyCatalog.Entry entry : PrivacyCatalog.search(query)) addRoute(entry);
        addInfoCard();
    }

    private void addRoute(PrivacyCatalog.Entry entry) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(labelFor(entry.id()));
        button.setTextColor(getColor(R.color.swir_text_primary));
        button.setBackgroundColor(getColor(R.color.swir_surface));
        button.setMinHeight(touchMin());
        button.setContentDescription(labelFor(entry.id()));
        button.setOnClickListener(v -> open(entry.action()));
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, dp(5), 0, dp(5));
        cards.addView(button, params);
    }

    private void addInfoCard() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(12), dp(14), dp(12));
        card.setBackgroundColor(getColor(R.color.swir_surface));
        card.addView(text(getString(R.string.scope_title), 13, getColor(R.color.swir_accent_cyan)), matchWrap());
        TextView body = text(getString(R.string.scope_body), 15, getColor(R.color.swir_text_primary));
        body.setPadding(0, dp(4), 0, 0);
        card.addView(body, matchWrap());
        cards.addView(card, matchWrap());
    }

    private String labelFor(String id) {
        if ("privacy".equals(id)) return getString(R.string.route_privacy);
        if ("permissions".equals(id)) return getString(R.string.route_permissions);
        if ("location".equals(id)) return getString(R.string.route_location);
        if ("apps".equals(id)) return getString(R.string.route_apps);
        if ("special_access".equals(id)) return getString(R.string.route_special_access);
        return id;
    }

    private void open(String action) {
        Intent intent = new Intent(action);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private int touchMin() {
        return getResources().getDimensionPixelSize(R.dimen.swir_touch_min);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
