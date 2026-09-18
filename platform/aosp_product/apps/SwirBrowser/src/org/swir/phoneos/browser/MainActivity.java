package org.swir.phoneos.browser;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.CookieManager;
import android.webkit.URLUtil;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebStorage;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private EditText address;
    private TextView status;
    private WebView webView;
    private CheckBox javascript;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle(R.string.app_name);
        int spaceXs = getResources().getDimensionPixelSize(R.dimen.swir_space_xs);
        int spaceSm = getResources().getDimensionPixelSize(R.dimen.swir_space_sm);
        int spaceMd = getResources().getDimensionPixelSize(R.dimen.swir_space_md);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(spaceMd, spaceMd, spaceMd, spaceMd);
        root.setBackgroundColor(getColor(R.color.swir_background));
        root.addView(text(R.string.title, 26, spaceXs, spaceSm));
        root.addView(text(R.string.subtitle, 13, spaceXs, spaceSm));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        address = new EditText(this);
        address.setHint(R.string.address_hint);
        address.setSingleLine(true);
        address.setTextColor(getColor(R.color.swir_text_primary));
        address.setHintTextColor(getColor(R.color.swir_text_secondary));
        address.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        Button go = button(R.string.go);
        bar.addView(address, new LinearLayout.LayoutParams(0, -2, 1));
        bar.addView(go);
        root.addView(bar);

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        Button back = button(R.string.back);
        Button forward = button(R.string.forward);
        Button reload = button(R.string.reload);
        nav.addView(back, new LinearLayout.LayoutParams(0, -2, 1));
        nav.addView(forward, new LinearLayout.LayoutParams(0, -2, 1));
        nav.addView(reload, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(nav);

        LinearLayout utility = new LinearLayout(this);
        utility.setOrientation(LinearLayout.HORIZONTAL);
        Button clear = button(R.string.clear_data);
        Button downloads = button(R.string.downloads);
        utility.addView(clear, new LinearLayout.LayoutParams(0, -2, 1));
        utility.addView(downloads, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(utility);

        javascript = new CheckBox(this);
        javascript.setText(R.string.javascript);
        javascript.setTextColor(getColor(R.color.swir_text_primary));
        javascript.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        root.addView(javascript);
        status = text(R.string.privacy_on, 12, spaceXs, spaceSm);
        status.setTextColor(getColor(R.color.swir_text_secondary));
        root.addView(status);
        webView = new WebView(this);
        webView.setBackgroundColor(getColor(R.color.swir_surface));
        root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSafeBrowsingEnabled(true);
        settings.setDomStorageEnabled(false);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String target = request == null || request.getUrl() == null ? "" : request.getUrl().toString();
                if (!BrowserPolicy.isSafeUrl(target)) {
                    Toast.makeText(MainActivity.this, R.string.blocked_url, Toast.LENGTH_LONG).show();
                    return true;
                }
                return false;
            }
        });
        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) ->
                enqueueDownload(url, contentDisposition, mimeType));

        go.setOnClickListener(v -> openAddress());
        address.setOnEditorActionListener((v, actionId, event) -> { openAddress(); return true; });
        back.setOnClickListener(v -> { if (webView.canGoBack()) webView.goBack(); });
        forward.setOnClickListener(v -> { if (webView.canGoForward()) webView.goForward(); });
        reload.setOnClickListener(v -> webView.reload());
        clear.setOnClickListener(v -> clearData());
        downloads.setOnClickListener(v -> openDownloads());
        javascript.setOnCheckedChangeListener((buttonView, checked) -> {
            webView.getSettings().setJavaScriptEnabled(checked);
            webView.getSettings().setDomStorageEnabled(checked);
            status.setText(checked ? R.string.privacy_off : R.string.privacy_on);
        });
    }

    private TextView text(int id, int sp, int topPadding, int bottomPadding) {
        TextView view = new TextView(this);
        view.setText(id);
        view.setTextSize(sp);
        view.setTextColor(getColor(R.color.swir_text_primary));
        view.setPadding(0, topPadding, 0, bottomPadding);
        return view;
    }

    private Button button(int id) {
        Button button = new Button(this);
        button.setText(id);
        button.setMinHeight(getResources().getDimensionPixelSize(R.dimen.swir_touch_min));
        return button;
    }

    private void openAddress() {
        String raw = address.getText().toString();
        String target = BrowserPolicy.normalizeUrl(raw);
        if (target.isEmpty()) target = BrowserPolicy.searchUrl(raw);
        if (target.isEmpty()) {
            Toast.makeText(this, R.string.invalid_address, Toast.LENGTH_LONG).show();
            return;
        }
        address.setText(target);
        webView.loadUrl(target);
    }

    private void enqueueDownload(String url, String contentDisposition, String mimeType) {
        if (!BrowserPolicy.isSafeDownloadUrl(url)) {
            Toast.makeText(this, R.string.download_blocked, Toast.LENGTH_LONG).show();
            return;
        }
        String fileName = BrowserPolicy.safeDownloadFileName(URLUtil.guessFileName(url, contentDisposition, mimeType));
        String safeMime = BrowserPolicy.safeMimeType(mimeType);
        DownloadManager manager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
        if (manager == null) {
            Toast.makeText(this, R.string.downloads_unavailable, Toast.LENGTH_LONG).show();
            return;
        }
        try {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setTitle(fileName);
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setAllowedOverRoaming(false);
            if (!safeMime.isEmpty()) request.setMimeType(safeMime);
            request.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, fileName);
            manager.enqueue(request);
            Toast.makeText(this, R.string.download_started, Toast.LENGTH_SHORT).show();
        } catch (IllegalArgumentException | SecurityException ex) {
            Toast.makeText(this, R.string.download_blocked, Toast.LENGTH_LONG).show();
        }
    }

    private void openDownloads() {
        try {
            startActivity(new Intent(DownloadManager.ACTION_VIEW_DOWNLOADS));
        } catch (ActivityNotFoundException | SecurityException ex) {
            Toast.makeText(this, R.string.downloads_unavailable, Toast.LENGTH_LONG).show();
        }
    }

    private void clearData() {
        webView.clearHistory();
        webView.clearCache(true);
        WebStorage.getInstance().deleteAllData();
        CookieManager.getInstance().removeAllCookies(null);
        Toast.makeText(this, R.string.data_cleared, Toast.LENGTH_SHORT).show();
    }

    @Override protected void onDestroy() {
        if (webView != null) webView.destroy();
        super.onDestroy();
    }
}
