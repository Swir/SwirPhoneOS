package org.swir.phoneos.update;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.text.format.Formatter;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Read-only update status and local-package preflight UI. Install/recovery handoff remains disabled. */
public final class MainActivity extends Activity {
    private static final int REQUEST_LOCAL_PACKAGE = 410;

    private final ExecutorService inspectionExecutor = Executors.newSingleThreadExecutor();
    private LinearLayout cards;
    private volatile boolean destroyed;
    private boolean packageInspecting;
    private String packageDisplayName;
    private UpdatePolicy.PackageInspection packageInspection;

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

        TextView title = text(getString(R.string.app_name), 26, getColor(R.color.swir_accent_cyan));
        root.addView(title, matchWrap());
        TextView subtitle = text(getString(R.string.subtitle), 14, getColor(R.color.swir_text_secondary));
        subtitle.setPadding(0, dp(4), 0, dp(10));
        root.addView(subtitle, matchWrap());

        Button refresh = button(R.string.refresh);
        refresh.setOnClickListener(v -> refresh());
        root.addView(refresh, matchWrap());

        Button reviewPackage = button(R.string.review_local_package);
        reviewPackage.setOnClickListener(v -> chooseLocalPackage());
        LinearLayout.LayoutParams reviewParams = matchWrap();
        reviewParams.setMargins(0, dp(8), 0, 0);
        root.addView(reviewPackage, reviewParams);

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
        addCard(R.string.local_package, packageStatusLabel());
        if (packageDisplayName != null) addCard(R.string.package_name, packageDisplayName);
        if (packageInspection != null && packageInspection.sizeBytes() >= 0L) {
            addCard(R.string.package_size, Formatter.formatFileSize(this, packageInspection.sizeBytes()));
        }
        if (packageInspection != null && !packageInspection.sha256().isEmpty()) {
            addCard(R.string.package_sha256, packageInspection.sha256());
        }
    }

    private String packageStatusLabel() {
        if (packageInspecting) return getString(R.string.package_inspecting);
        if (packageInspection == null) return getString(R.string.package_none_selected);
        switch (packageInspection.state()) {
            case REVIEW_READY_UNTRUSTED: return getString(R.string.package_review_ready_untrusted);
            case REJECTED_NAME: return getString(R.string.package_rejected_name);
            case REJECTED_SIZE: return getString(R.string.package_rejected_size);
            case REJECTED_FORMAT: return getString(R.string.package_rejected_format);
            default: return getString(R.string.package_read_failed);
        }
    }

    private String channelLabel(UpdatePolicy.Channel channel) {
        switch (channel) {
            case STABLE: return getString(R.string.channel_stable);
            case BETA: return getString(R.string.channel_beta);
            case DEVELOPER: return getString(R.string.channel_developer);
            default: return getString(R.string.channel_unknown);
        }
    }

    private void chooseLocalPackage() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/zip");
        if (intent.resolveActivity(getPackageManager()) != null) startActivityForResult(intent, REQUEST_LOCAL_PACKAGE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_LOCAL_PACKAGE || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        inspectLocalPackage(data.getData());
    }

    private void inspectLocalPackage(Uri uri) {
        DocumentInfo info = documentInfo(uri);
        packageDisplayName = info.displayName;
        packageInspection = null;
        packageInspecting = true;
        refresh();
        inspectionExecutor.execute(() -> {
            UpdatePolicy.PackageInspection result;
            try (InputStream input = getContentResolver().openInputStream(uri)) {
                result = UpdatePolicy.inspectPackage(info.displayName, info.sizeBytes, input);
            } catch (Exception ignored) {
                result = UpdatePolicy.readFailure();
            }
            final UpdatePolicy.PackageInspection completed = result;
            runOnUiThread(() -> {
                if (destroyed) return;
                packageInspecting = false;
                packageInspection = completed;
                refresh();
            });
        });
    }

    private DocumentInfo documentInfo(Uri uri) {
        String displayName = null;
        long size = -1L;
        try (Cursor cursor = getContentResolver().query(
                uri,
                new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE},
                null,
                null,
                null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                int sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE);
                if (nameIndex >= 0 && !cursor.isNull(nameIndex)) displayName = cursor.getString(nameIndex);
                if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) size = cursor.getLong(sizeIndex);
            }
        } catch (Exception ignored) {
            // inspectPackage will fail closed if the provider cannot supply a safe name/read stream.
        }
        return new DocumentInfo(displayName, size);
    }

    private void openSystemUpdate() {
        Intent intent = new Intent(Settings.ACTION_SYSTEM_UPDATE_SETTINGS);
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private void addCard(int titleRes, String value) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(12), dp(14), dp(12));
        card.setBackgroundColor(getColor(R.color.swir_surface));
        TextView title = text(getString(titleRes), 13, getColor(R.color.swir_accent_cyan));
        TextView body = text(
                value == null || value.isEmpty() ? getString(R.string.unknown) : value,
                16,
                getColor(R.color.swir_text_primary));
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
        button.setTextColor(getColor(R.color.swir_text_primary));
        button.setBackgroundColor(getColor(R.color.swir_surface_alt));
        button.setMinHeight(touchMin());
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

    private int touchMin() {
        return getResources().getDimensionPixelSize(R.dimen.swir_touch_min);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        destroyed = true;
        inspectionExecutor.shutdownNow();
        super.onDestroy();
    }

    private static final class DocumentInfo {
        final String displayName;
        final long sizeBytes;

        DocumentInfo(String displayName, long sizeBytes) {
            this.displayName = displayName;
            this.sizeBytes = sizeBytes;
        }
    }
}
