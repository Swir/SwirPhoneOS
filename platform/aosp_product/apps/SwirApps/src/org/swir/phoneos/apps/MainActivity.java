package org.swir.phoneos.apps;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.InstallSourceInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.content.pm.Signature;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class MainActivity extends Activity {
    private final List<AppRow> all = new ArrayList<>();
    private final List<AppRow> shown = new ArrayList<>();
    private ArrayAdapter<String> adapter;
    private EditText search;

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
        search.setSingleLine(true);
        search.setTextColor(Color.WHITE);
        search.setHintTextColor(Color.rgb(130, 170, 190));
        root.addView(search);
        ListView list = new ListView(this);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, new ArrayList<>());
        list.setAdapter(adapter);
        root.addView(list, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        search.addTextChangedListener(new SimpleTextWatcher(this::filter));
        list.setOnItemClickListener((parent, view, position, id) -> {
            if (position < shown.size()) launch(shown.get(position));
        });
        list.setOnItemLongClickListener((parent, view, position, id) -> {
            if (position < shown.size()) details(shown.get(position));
            return true;
        });
        loadApps();
    }

    private TextView text(int id, int sp) {
        TextView view = new TextView(this);
        view.setText(id);
        view.setTextSize(sp);
        view.setTextColor(Color.WHITE);
        view.setPadding(0, 6, 0, 10);
        return view;
    }

    private void loadApps() {
        PackageManager packageManager = getPackageManager();
        Intent launcher = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> results = packageManager.queryIntentActivities(launcher, 0);
        Map<String, AppRow> unique = new LinkedHashMap<>();
        for (ResolveInfo info : results) {
            if (info.activityInfo == null || info.activityInfo.applicationInfo == null) continue;
            String packageName = info.activityInfo.packageName;
            if (!AppCatalogPolicy.validPackageName(packageName) || unique.containsKey(packageName)) continue;
            ApplicationInfo app = info.activityInfo.applicationInfo;
            String label = String.valueOf(packageManager.getApplicationLabel(app));
            unique.put(packageName, inspect(packageManager, app, label, packageName));
        }
        all.clear();
        all.addAll(unique.values());
        all.sort(Comparator.comparing(row -> row.label.toLowerCase(java.util.Locale.ROOT)));
        filter();
    }

    private AppRow inspect(PackageManager packageManager, ApplicationInfo app, String label, String packageName) {
        String version = "";
        String signature = "";
        String installerPackage = "";
        long lastUpdateTime = 0L;
        boolean updatedSystemApp = (app.flags & ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0;
        boolean systemImage = (app.flags & ApplicationInfo.FLAG_SYSTEM) != 0 || updatedSystemApp;
        try {
            PackageInfo info = packageManager.getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES);
            version = info.versionName == null ? Long.toString(info.getLongVersionCode()) : info.versionName;
            lastUpdateTime = AppCatalogPolicy.normalizeUpdateTime(info.lastUpdateTime);
            if (info.signingInfo != null) {
                Signature[] signers = info.signingInfo.getApkContentsSigners();
                if (signers != null && signers.length > 0) {
                    signature = AppCatalogPolicy.shortDigest(AppCatalogPolicy.sha256(signers[0].toByteArray()));
                }
            }
            InstallSourceInfo source = packageManager.getInstallSourceInfo(packageName);
            if (source != null && source.getInstallingPackageName() != null) {
                installerPackage = source.getInstallingPackageName();
            }
        } catch (PackageManager.NameNotFoundException ignored) {
        }
        AppCatalogPolicy.UpdateSource updateSource = AppCatalogPolicy.updateSource(systemImage, installerPackage);
        AppCatalogPolicy.UpdateState updateState = AppCatalogPolicy.updateState(systemImage, updatedSystemApp, installerPackage);
        return new AppRow(label, packageName, version, signature, updateSource, updateState, lastUpdateTime);
    }

    private void filter() {
        String query = search == null ? "" : search.getText().toString();
        shown.clear();
        ArrayList<String> labels = new ArrayList<>();
        for (AppRow row : all) {
            if (AppCatalogPolicy.matches(row.label, row.packageName, query)) {
                shown.add(row);
                String signer = row.signature.isEmpty() ? getString(R.string.signature_unavailable) : row.signature;
                String updated = row.lastUpdateTime == 0L
                        ? getString(R.string.last_updated_unknown)
                        : DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(new Date(row.lastUpdateTime));
                labels.add(row.label + "\n" + row.packageName
                        + "\n" + getString(R.string.version_format, row.version)
                        + "\n" + getString(R.string.signature_format, signer)
                        + "\n" + getString(R.string.update_source_format, updateSourceLabel(row.updateSource))
                        + "\n" + getString(R.string.update_status_format, updateStateLabel(row.updateState))
                        + "\n" + getString(R.string.last_updated_format, updated));
            }
        }
        if (labels.isEmpty()) labels.add(getString(R.string.no_apps));
        adapter.clear();
        adapter.addAll(labels);
        adapter.notifyDataSetChanged();
    }

    private String updateSourceLabel(AppCatalogPolicy.UpdateSource source) {
        switch (source) {
            case SYSTEM_IMAGE:
                return getString(R.string.update_source_system);
            case EXTERNAL_INSTALLER:
                return getString(R.string.update_source_external);
            case LOCAL_UNKNOWN:
            default:
                return getString(R.string.update_source_local);
        }
    }

    private String updateStateLabel(AppCatalogPolicy.UpdateState state) {
        switch (state) {
            case SYSTEM_BASELINE:
                return getString(R.string.update_status_system_baseline);
            case SYSTEM_UPDATED:
                return getString(R.string.update_status_system_updated);
            case EXTERNAL_MANAGED:
                return getString(R.string.update_status_external);
            case LOCAL_UNKNOWN:
            default:
                return getString(R.string.update_status_local);
        }
    }

    private void launch(AppRow row) {
        Intent intent = getPackageManager().getLaunchIntentForPackage(row.packageName);
        if (intent != null) startActivity(intent);
        else Toast.makeText(this, R.string.no_launch_activity, Toast.LENGTH_LONG).show();
    }

    private void details(AppRow row) {
        Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + row.packageName));
        if (intent.resolveActivity(getPackageManager()) != null) startActivity(intent);
    }

    private static final class AppRow {
        final String label;
        final String packageName;
        final String version;
        final String signature;
        final AppCatalogPolicy.UpdateSource updateSource;
        final AppCatalogPolicy.UpdateState updateState;
        final long lastUpdateTime;

        AppRow(String label, String packageName, String version, String signature,
               AppCatalogPolicy.UpdateSource updateSource, AppCatalogPolicy.UpdateState updateState,
               long lastUpdateTime) {
            this.label = label == null ? "" : label;
            this.packageName = packageName;
            this.version = version == null ? "" : version;
            this.signature = signature == null ? "" : signature;
            this.updateSource = updateSource == null ? AppCatalogPolicy.UpdateSource.LOCAL_UNKNOWN : updateSource;
            this.updateState = updateState == null ? AppCatalogPolicy.UpdateState.LOCAL_UNKNOWN : updateState;
            this.lastUpdateTime = AppCatalogPolicy.normalizeUpdateTime(lastUpdateTime);
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
