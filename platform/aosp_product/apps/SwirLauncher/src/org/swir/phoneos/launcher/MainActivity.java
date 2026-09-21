package org.swir.phoneos.launcher;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.text.Collator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/** Minimal first-beta HOME surface with a safe first-run setup flow. */
public final class MainActivity extends Activity {
    private static final String PREFS = "swir_launcher_state";
    private static final String SETUP_COMPLETE = "setup_complete";
    private static final String SETTINGS_PACKAGE = "org.swir.phoneos.settings";
    private static final String FILES_PACKAGE = "org.swir.phoneos.files";
    private static final String UPDATE_PACKAGE = "org.swir.phoneos.update";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_background));
        setContentView(buildUi());
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (isFinishing()) {
            return;
        }
        setContentView(buildUi());
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(getColor(R.color.swir_background));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(24));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));

        TextView title = text(R.string.launcher_title, 28, getColor(R.color.swir_accent_cyan));
        root.addView(title, matchWrap());

        TextView subtitle = text(R.string.launcher_subtitle, 14, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, dp(4), 0, dp(14));
        root.addView(subtitle, matchWrap());

        if (!prefs().getBoolean(SETUP_COMPLETE, false)) {
            addSetupCard(root);
        }

        TextView essentials = text(R.string.essentials, 15, getColor(R.color.swir_accent_cyan));
        essentials.setPadding(0, dp(12), 0, dp(4));
        root.addView(essentials, matchWrap());
        addPackageButton(root, R.string.settings, SETTINGS_PACKAGE);
        addPackageButton(root, R.string.files, FILES_PACKAGE);
        addPackageButton(root, R.string.update, UPDATE_PACKAGE);

        TextView apps = text(R.string.apps, 15, getColor(R.color.swir_accent_cyan));
        apps.setPadding(0, dp(18), 0, dp(6));
        root.addView(apps, matchWrap());
        addLaunchableApps(root);
        return scroll;
    }

    private void addSetupCard(LinearLayout root) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(14), dp(14), dp(14));
        card.setBackgroundColor(getColor(R.color.swir_surface));
        card.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

        TextView heading = text(R.string.setup_title, 20, getColor(R.color.swir_text_primary));
        card.addView(heading, matchWrap());
        TextView body = text(R.string.setup_body, 14, getColor(R.color.swir_text_secondary));
        body.setPadding(0, dp(6), 0, dp(8));
        card.addView(body, matchWrap());

        card.addView(actionButton(R.string.language_region, () -> openSystem(Settings.ACTION_LOCALE_SETTINGS)), matchWrap());
        card.addView(actionButton(R.string.privacy, () -> openSystem(Settings.ACTION_PRIVACY_SETTINGS)), matchWrap());
        card.addView(actionButton(R.string.finish_setup, this::finishSetup), matchWrap());

        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, 0, 0, dp(8));
        root.addView(card, params);
    }

    private void finishSetup() {
        prefs().edit().putBoolean(SETUP_COMPLETE, true).apply();
        Toast.makeText(this, R.string.setup_done, Toast.LENGTH_SHORT).show();
        setContentView(buildUi());
    }

    private void addPackageButton(LinearLayout root, int labelRes, String packageName) {
        Button button = actionButton(labelRes, () -> launchPackage(packageName));
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, dp(4), 0, dp(4));
        root.addView(button, params);
    }

    private void addLaunchableApps(LinearLayout root) {
        PackageManager pm = getPackageManager();
        Intent query = new Intent(Intent.ACTION_MAIN);
        query.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> resolved = pm.queryIntentActivities(query, 0);
        List<AppEntry> entries = new ArrayList<>();
        for (ResolveInfo info : resolved) {
            if (info.activityInfo == null || !LauncherPolicy.showPackage(getPackageName(), info.activityInfo.packageName)) {
                continue;
            }
            String label = LauncherPolicy.normalizeLabel(String.valueOf(info.loadLabel(pm)));
            if (label.isEmpty()) {
                label = getString(R.string.unknown_app);
            }
            entries.add(new AppEntry(label, info.activityInfo.packageName));
        }
        final Collator collator = Collator.getInstance();
        Collections.sort(entries, new Comparator<AppEntry>() {
            @Override
            public int compare(AppEntry left, AppEntry right) {
                int byLabel = collator.compare(left.label, right.label);
                return byLabel != 0 ? byLabel : left.packageName.compareTo(right.packageName);
            }
        });

        if (entries.isEmpty()) {
            TextView empty = text(R.string.no_apps, 14, getColor(R.color.swir_text_secondary));
            root.addView(empty, matchWrap());
            return;
        }
        for (AppEntry entry : entries) {
            Button button = actionButton(entry.label, () -> launchPackage(entry.packageName));
            LinearLayout.LayoutParams params = matchWrap();
            params.setMargins(0, dp(3), 0, dp(3));
            root.addView(button, params);
        }
    }

    private void launchPackage(String packageName) {
        Intent intent = getPackageManager().getLaunchIntentForPackage(packageName);
        if (intent == null) {
            Toast.makeText(this, R.string.open_failed, Toast.LENGTH_SHORT).show();
            return;
        }
        try {
            startActivity(intent);
        } catch (ActivityNotFoundException | SecurityException exception) {
            Toast.makeText(this, R.string.open_failed, Toast.LENGTH_SHORT).show();
        }
    }

    private void openSystem(String action) {
        try {
            startActivity(new Intent(action));
        } catch (ActivityNotFoundException | SecurityException exception) {
            Toast.makeText(this, R.string.open_failed, Toast.LENGTH_SHORT).show();
        }
    }

    private SharedPreferences prefs() {
        return getSharedPreferences(PREFS, MODE_PRIVATE);
    }

    private Button actionButton(int labelRes, Runnable action) {
        return actionButton(getString(labelRes), action);
    }

    private Button actionButton(String label, Runnable action) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(16);
        button.setTextColor(getColor(R.color.swir_text_primary));
        button.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        button.setBackgroundColor(getColor(R.color.swir_surface_alt));
        button.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        button.setContentDescription(label);
        button.setOnClickListener(v -> action.run());
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
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static final class AppEntry {
        final String label;
        final String packageName;

        AppEntry(String label, String packageName) {
            this.label = label;
            this.packageName = packageName;
        }
    }
}
