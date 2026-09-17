package org.swir.phoneos.device_care;

import android.app.Activity;
import android.app.ActivityManager;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.PowerManager;
import android.os.StatFs;
import android.text.format.Formatter;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Permission-free diagnostics dashboard backed by Android framework state. */
public final class MainActivity extends Activity {
    private LinearLayout cards;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(getColor(R.color.swir_background));
        getWindow().setNavigationBarColor(getColor(R.color.swir_background));
        setContentView(buildUi());
        refresh();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(18));
        root.setBackgroundColor(getColor(R.color.swir_background));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_LOCALE);

        TextView title = text(R.string.app_name, 26, getColor(R.color.swir_accent_cyan));
        root.addView(title, matchWrap());
        TextView subtitle = text(R.string.subtitle, 14, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, dp(4), 0, dp(10));
        root.addView(subtitle, matchWrap());

        Button refresh = new Button(this);
        refresh.setAllCaps(false);
        refresh.setText(R.string.refresh);
        refresh.setTextColor(getColor(R.color.swir_text_primary));
        refresh.setBackgroundColor(getColor(R.color.swir_surface_alt));
        refresh.setMinHeight(touchMin());
        refresh.setContentDescription(getString(R.string.refresh));
        refresh.setOnClickListener(v -> refresh());
        root.addView(refresh, matchWrap());

        ScrollView scroll = new ScrollView(this);
        cards = new LinearLayout(this);
        cards.setOrientation(LinearLayout.VERTICAL);
        cards.setPadding(0, dp(8), 0, dp(16));
        scroll.addView(cards, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return root;
    }

    private void refresh() {
        cards.removeAllViews();
        addCard(R.string.device, getString(
                R.string.device_value,
                Build.MANUFACTURER,
                Build.MODEL,
                Build.VERSION.RELEASE,
                Build.VERSION.SECURITY_PATCH));
        addBatteryCard();
        addStorageCard();
        addMemoryCard();
        addThermalCard();
    }

    private void addBatteryCard() {
        BatteryManager manager = getSystemService(BatteryManager.class);
        int level = manager == null ? -1 : manager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        Intent battery = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        int status = battery == null ? BatteryManager.BATTERY_STATUS_UNKNOWN
                : battery.getIntExtra(BatteryManager.EXTRA_STATUS, BatteryManager.BATTERY_STATUS_UNKNOWN);
        if (!HealthModel.batteryLevelValid(level) && battery != null) {
            int raw = battery.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int scale = battery.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
            level = scale > 0 && raw >= 0 ? Math.round(raw * 100f / scale) : -1;
        }
        String levelText = HealthModel.batteryLevelValid(level) ? getString(R.string.percent_value, level) : getString(R.string.unknown);
        String state = status == BatteryManager.BATTERY_STATUS_CHARGING
                ? getString(R.string.charging)
                : status == BatteryManager.BATTERY_STATUS_FULL
                ? getString(R.string.full)
                : getString(R.string.not_charging);
        addCard(R.string.battery, getString(R.string.battery_value, levelText, state));
    }

    private void addStorageCard() {
        StatFs stat = new StatFs(Environment.getDataDirectory().getAbsolutePath());
        long total = stat.getTotalBytes();
        long available = stat.getAvailableBytes();
        int used = HealthModel.percentUsed(available, total);
        String usedText = used < 0 ? getString(R.string.unknown) : getString(R.string.percent_value, used);
        addCard(R.string.storage, getString(
                R.string.storage_value,
                Formatter.formatFileSize(this, total - available),
                Formatter.formatFileSize(this, total),
                usedText));
    }

    private void addMemoryCard() {
        ActivityManager manager = getSystemService(ActivityManager.class);
        ActivityManager.MemoryInfo info = new ActivityManager.MemoryInfo();
        if (manager != null) manager.getMemoryInfo(info);
        int used = manager == null ? -1 : HealthModel.percentUsed(info.availMem, info.totalMem);
        String usedText = used < 0 ? getString(R.string.unknown) : getString(R.string.percent_value, used);
        String total = manager == null ? getString(R.string.unknown) : Formatter.formatFileSize(this, info.totalMem);
        String available = manager == null ? getString(R.string.unknown) : Formatter.formatFileSize(this, info.availMem);
        addCard(R.string.memory, getString(R.string.memory_value, available, total, usedText));
    }

    private void addThermalCard() {
        PowerManager manager = getSystemService(PowerManager.class);
        int status = manager == null ? -1 : manager.getCurrentThermalStatus();
        HealthModel.ThermalBand band = HealthModel.thermalBand(status);
        int label;
        switch (band) {
            case NOMINAL: label = R.string.thermal_nominal; break;
            case WARM: label = R.string.thermal_warm; break;
            case HOT: label = R.string.thermal_hot; break;
            case CRITICAL: label = R.string.thermal_critical; break;
            default: label = R.string.unknown;
        }
        addCard(R.string.thermal, getString(label));
    }

    private void addCard(int titleRes, String value) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(12), dp(14), dp(12));
        card.setBackgroundColor(getColor(R.color.swir_surface));
        TextView title = text(titleRes, 13, getColor(R.color.swir_accent_cyan));
        TextView body = text(value, 16, getColor(R.color.swir_text_primary));
        body.setPadding(0, dp(4), 0, 0);
        card.addView(title, matchWrap());
        card.addView(body, matchWrap());
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, dp(5), 0, dp(5));
        cards.addView(card, params);
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
