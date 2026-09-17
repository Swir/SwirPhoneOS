package org.swir.phoneos.browser;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.CookieManager;
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
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(20, 20, 20, 20);
        root.setBackgroundColor(Color.rgb(7, 18, 34));
        root.addView(text(R.string.title, 26));
        root.addView(text(R.string.subtitle, 13));
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        address = new EditText(this);
        address.setHint(R.string.address_hint);
        address.setSingleLine(true);
        address.setTextColor(Color.WHITE);
        address.setHintTextColor(Color.rgb(130, 170, 190));
        Button go = button(R.string.go);
        bar.addView(address, new LinearLayout.LayoutParams(0, -2, 1));
        bar.addView(go);
        root.addView(bar);
        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        Button back = button(R.string.back);
        Button forward = button(R.string.forward);
        Button reload = button(R.string.reload);
        Button clear = button(R.string.clear_data);
        nav.addView(back, new LinearLayout.LayoutParams(0, -2, 1));
        nav.addView(forward, new LinearLayout.LayoutParams(0, -2, 1));
        nav.addView(reload, new LinearLayout.LayoutParams(0, -2, 1));
        nav.addView(clear, new LinearLayout.LayoutParams(0, -2, 1));
        root.addView(nav);
        javascript = new CheckBox(this);
        javascript.setText(R.string.javascript);
        javascript.setTextColor(Color.WHITE);
        root.addView(javascript);
        status = text(R.string.privacy_on, 12);
        root.addView(status);
        webView = new WebView(this);
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
        go.setOnClickListener(v -> openAddress());
        address.setOnEditorActionListener((v, actionId, event) -> { openAddress(); return true; });
        back.setOnClickListener(v -> { if (webView.canGoBack()) webView.goBack(); });
        forward.setOnClickListener(v -> { if (webView.canGoForward()) webView.goForward(); });
        reload.setOnClickListener(v -> webView.reload());
        clear.setOnClickListener(v -> clearData());
        javascript.setOnCheckedChangeListener((buttonView, checked) -> {
            webView.getSettings().setJavaScriptEnabled(checked);
            webView.getSettings().setDomStorageEnabled(checked);
            status.setText(checked ? R.string.privacy_off : R.string.privacy_on);
        });
    }

    private TextView text(int id, int sp) {
        TextView view = new TextView(this);
        view.setText(id);
        view.setTextSize(sp);
        view.setTextColor(Color.WHITE);
        view.setPadding(0, 4, 0, 8);
        return view;
    }

    private Button button(int id) {
        Button button = new Button(this);
        button.setText(id);
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
