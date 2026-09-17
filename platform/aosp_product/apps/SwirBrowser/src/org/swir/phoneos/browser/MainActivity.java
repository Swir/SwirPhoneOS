package org.swir.phoneos.browser;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebStorage;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(7, 14, 24);
    private static final int PANEL = Color.rgb(15, 29, 44);
    private static final int ACCENT = Color.rgb(64, 211, 255);
    private WebView webView;
    private EditText address;
    private TextView status;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BG);
        setContentView(buildUi());
        configureWebView();
        open(BrowserPolicy.normalizeAddress(""));
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(12));
        root.setBackgroundColor(BG);

        TextView title = text(R.string.title, 28, Color.WHITE);
        title.setTypeface(title.getTypeface(), 1);
        root.addView(title);
        TextView subtitle = text(R.string.subtitle, 14, Color.LTGRAY);
        subtitle.setPadding(0, dp(4), 0, dp(14));
        root.addView(subtitle);

        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        address = new EditText(this);
        address.setSingleLine(true);
        address.setHint(R.string.address_hint);
        address.setTextColor(Color.WHITE);
        address.setHintTextColor(Color.GRAY);
        address.setBackgroundColor(PANEL);
        address.setPadding(dp(12), 0, dp(12), 0);
        address.setOnEditorActionListener((view, actionId, event) -> { navigateFromAddress(); return true; });
        bar.addView(address, new LinearLayout.LayoutParams(0, dp(48), 1f));
        Button go = button(R.string.go);
        go.setOnClickListener(v -> navigateFromAddress());
        bar.addView(go, new LinearLayout.LayoutParams(dp(72), dp(48)));
        root.addView(bar);

        LinearLayout actions = new LinearLayout(this);
        actions.setPadding(0, dp(8), 0, dp(8));
        Button back = button(R.string.back); back.setOnClickListener(v -> { if (webView.canGoBack()) webView.goBack(); });
        Button forward = button(R.string.forward); forward.setOnClickListener(v -> { if (webView.canGoForward()) webView.goForward(); });
        Button reload = button(R.string.reload); reload.setOnClickListener(v -> webView.reload());
        Button share = button(R.string.share); share.setOnClickListener(v -> shareCurrent());
        Button privacy = button(R.string.clear_data); privacy.setOnClickListener(v -> confirmClearData());
        for (Button button : new Button[]{back, forward, reload, share, privacy}) actions.addView(button, new LinearLayout.LayoutParams(0, dp(44), 1f));
        root.addView(actions);

        status = text(R.string.status_ready, 12, ACCENT);
        status.setPadding(dp(2), 0, 0, dp(6));
        root.addView(status);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.WHITE);
        root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1f));
        return root;
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String target = request.getUrl().toString();
                if (!BrowserPolicy.isAllowedUri(target)) {
                    status.setText(R.string.status_blocked);
                    return true;
                }
                return false;
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                status.setText(R.string.status_loading);
                if (url != null) address.setText(url);
            }
            @Override public void onPageFinished(WebView view, String url) {
                status.setText(R.string.status_ready);
                if (url != null) address.setText(url);
            }
        });
    }

    private void navigateFromAddress() {
        String target = BrowserPolicy.normalizeAddress(address.getText().toString());
        if (!BrowserPolicy.isAllowedUri(target)) {
            Toast.makeText(this, R.string.error_invalid, Toast.LENGTH_SHORT).show();
            return;
        }
        open(target);
    }

    private void open(String target) {
        if (!BrowserPolicy.isAllowedUri(target)) {
            status.setText(R.string.status_blocked);
            return;
        }
        address.setText(target);
        webView.loadUrl(target);
    }

    private void shareCurrent() {
        String current = webView.getUrl();
        if (!BrowserPolicy.canShare(current)) {
            Toast.makeText(this, R.string.error_invalid, Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("text/plain");
        intent.putExtra(Intent.EXTRA_TEXT, current);
        startActivity(Intent.createChooser(intent, getString(R.string.share)));
    }

    private void confirmClearData() {
        new AlertDialog.Builder(this)
            .setTitle(R.string.clear_confirm_title)
            .setMessage(R.string.clear_confirm_message)
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.clear_confirm, (dialog, which) -> clearData())
            .show();
    }

    private void clearData() {
        CookieManager.getInstance().removeAllCookies(null);
        CookieManager.getInstance().flush();
        WebStorage.getInstance().deleteAllData();
        webView.clearCache(true);
        webView.clearHistory();
        Toast.makeText(this, R.string.toast_cleared, Toast.LENGTH_SHORT).show();
    }

    private Button button(int label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(PANEL);
        button.setAllCaps(false);
        return button;
    }

    private TextView text(int value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.destroy();
        }
        super.onDestroy();
    }
}
