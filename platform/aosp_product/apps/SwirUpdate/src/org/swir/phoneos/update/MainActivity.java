package org.swir.phoneos.update;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Read-only update status UI. Package staging/recovery handoff remains intentionally disabled. */
public final class MainActivity extends Activity {
    private LinearLayout cards;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(4, 11, 23));
        getWindow().setNavigationBarColor(Color.rgb(4, 11, 23));
        setContentView(buildUi());
        refresh();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(18));
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

        TextView title = text(getString(R.string.app_name), 26, Color.rgb(105, 216, 255));
        root.addView(title, matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, Color.rgb(180, 198, 217));
        subtitle.setPadding(0, dp(4), 0, dp(10));
        root.addView(subtitle, matchWrap());

        Button refresh = button(R.string.refresh);
        refresh.setOnClickListener(v -> refresh());
        root.addView(refresh, matchWrap());

        Button systemUpdate = button(R.string.open_system_update);
        systemUpdate.setOnClickListener(v -> openSystemUpdate());
        LinearLayout.LayoutParams updateParams = matchWrap();
        updateParams.setMargins(0, dp(8), 0, dp(4));
        root.addView(systemUpdate, updateParams);

        ScrollView scroll = new ScrollView(this);
        cards = new LinearLayout(this);
        cards.setOrientation(LinearLayout.VERTICAL);
        cards.setPadding(0, dp(8), 0, dp(16));
        scroll.addView(cards, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return root;
    }

    private void refresh() {
        cards.removeAllViews();
        UpdatePolicy.Channel channel = UpdatePolicy.channelForBuild(Build.TYPE, Build.TAGS);
        addCard(R.string.channel, channelLabel(channel));
        addCard(R.string.current_build, Build.DISPLAY == null ? Build.FINGERPRINT : Build.DISPLAY);
        addCard(R.string.fingerprint, Build.FINGERPRINT);
        addCard(R.string.security_patch, Build.VERSION.SECURITY_PATCH);
        addCard(R.string.signature_engine, getString(R.string.signature_engine_ready));
        addCard(R.string.install_state, getString(R.string.no_package_staged));
    }

    private String channelLabel(UpdatePolicy.Channel channel) {
        switch (channel) {
            case STABLE: return getString(R.string.channel_stable);
            case BETA: return getString(R.string.channel_beta);
            case DEVELOPER: return getString(R.string.channel_developer);
            default: return getString(R.string.channel_unknown);
        }
    }

    private void openSystemUpdate() {
        Intent intent = new Intent(Settings.ACTION_SYSTEM_UPDATE_SETTINGS);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private void addCard(int titleRes, String value) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(12), dp(14), dp(12));
        card.setBackgroundColor(Color.rgb(13, 34, 55));
        TextView title = text(getString(titleRes), 13, Color.rgb(105, 216, 255));
        TextView body = text(value == null || value.isEmpty() ? getString(R.string.unknown) : value, 16, Color.WHITE);
        body.setPadding(0, dp(4), 0, 0);
        card.addView(title, matchWrap());
        card.addView(body, matchWrap());
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, dp(5), 0, dp(5));
        cards.addView(card, params);
    }

    private Button button(int textRes) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(textRes);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(Color.rgb(17, 45, 71));
        button.setContentDescription(getString(textRes));
        return button;
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

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
