package com.dclar.homecenter;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

public final class NetrunnerActivity extends Activity {
    private EditText urlEdit;
    private WebView webView;
    private TextView statusView;
    private TextView focusLabel;
    private View focusBox;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        loadUrl("https://example.com");
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#111111"));

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setPadding(dp(12), dp(10), dp(12), dp(8));
        header.setBackgroundColor(Color.parseColor("#1B1B1B"));

        TextView title = new TextView(this);
        title.setText("Netrunner");
        title.setTextColor(Color.WHITE);
        title.setTextSize(26);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        header.addView(title, matchWrap());

        statusView = new TextView(this);
        statusView.setText("Training wheels browser. Navigate first; learn and automate later.");
        statusView.setTextColor(Color.parseColor("#D6D6D6"));
        statusView.setTextSize(13);
        statusView.setGravity(Gravity.CENTER_HORIZONTAL);
        header.addView(statusView, matchWrap());

        LinearLayout navRow = new LinearLayout(this);
        navRow.setOrientation(LinearLayout.HORIZONTAL);
        navRow.setGravity(Gravity.CENTER_VERTICAL);
        navRow.setPadding(0, dp(8), 0, 0);

        Button back = smallButton("Back");
        back.setOnClickListener(v -> {
            if (webView != null && webView.canGoBack()) {
                webView.goBack();
            }
        });
        navRow.addView(back);

        Button forward = smallButton("Forward");
        forward.setOnClickListener(v -> {
            if (webView != null && webView.canGoForward()) {
                webView.goForward();
            }
        });
        navRow.addView(forward);

        Button reload = smallButton("Reload");
        reload.setOnClickListener(v -> {
            if (webView != null) {
                webView.reload();
            }
        });
        navRow.addView(reload);

        urlEdit = new EditText(this);
        urlEdit.setSingleLine(true);
        urlEdit.setTextColor(Color.WHITE);
        urlEdit.setHintTextColor(Color.parseColor("#9A9A9A"));
        urlEdit.setText("https://example.com");
        urlEdit.setHint("https://example.com");
        urlEdit.setImeOptions(EditorInfo.IME_ACTION_GO);
        urlEdit.setSelectAllOnFocus(true);
        LinearLayout.LayoutParams urlParams = new LinearLayout.LayoutParams(0, dp(52), 1f);
        urlParams.setMargins(dp(8), 0, dp(8), 0);
        navRow.addView(urlEdit, urlParams);

        Button go = smallButton("Go");
        go.setOnClickListener(v -> loadUrl(urlEdit.getText().toString()));
        navRow.addView(go);

        urlEdit.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_GO) {
                loadUrl(urlEdit.getText().toString());
                return true;
            }
            return false;
        });

        header.addView(navRow, matchWrap());
        root.addView(header, matchWrap());

        FrameLayout browserFrame = new FrameLayout(this);
        webView = new WebView(this);
        configureWebView(webView);
        browserFrame.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        focusBox = new View(this);
        focusBox.setBackgroundColor(Color.TRANSPARENT);
        focusBox.setVisibility(View.GONE);
        browserFrame.addView(focusBox, new FrameLayout.LayoutParams(dp(140), dp(96), Gravity.CENTER));

        root.addView(browserFrame, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f));

        LinearLayout commandPanel = new LinearLayout(this);
        commandPanel.setOrientation(LinearLayout.VERTICAL);
        commandPanel.setPadding(dp(12), dp(10), dp(12), dp(12));
        commandPanel.setBackgroundColor(Color.parseColor("#202020"));

        focusLabel = new TextView(this);
        focusLabel.setText("Element tools: inspect mode placeholder. Long-press commands land next.");
        focusLabel.setTextColor(Color.parseColor("#EFEFEF"));
        focusLabel.setTextSize(14);
        commandPanel.addView(focusLabel, matchWrap());

        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setOrientation(LinearLayout.HORIZONTAL);
        actionRow.setGravity(Gravity.CENTER_VERTICAL);
        actionRow.setPadding(0, dp(8), 0, 0);

        Button inspect = smallButton("Highlight");
        inspect.setOnClickListener(v -> toggleHighlight());
        actionRow.addView(inspect);

        Button read = smallButton("Read page title");
        read.setOnClickListener(v -> readPageTitle());
        actionRow.addView(read);

        Button homeCenter = smallButton("Home Center");
        homeCenter.setOnClickListener(v -> startActivity(new Intent(this, MainActivity.class)));
        actionRow.addView(homeCenter);

        commandPanel.addView(actionRow, matchWrap());
        root.addView(commandPanel, matchWrap());

        setContentView(root);
    }

    private void configureWebView(WebView view) {
        WebSettings settings = view.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        view.setWebChromeClient(new WebChromeClient());
        view.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                urlEdit.setText(url);
                statusView.setText("Loaded: " + url);
            }
        });
    }

    private void loadUrl(String raw) {
        String url = raw == null ? "" : raw.trim();
        if (url.isEmpty()) {
            url = "https://example.com";
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "https://" + url;
        }
        statusView.setText("Loading: " + url);
        urlEdit.setText(url);
        webView.loadUrl(url);
    }

    private void toggleHighlight() {
        if (focusBox.getVisibility() == View.VISIBLE) {
            focusBox.setVisibility(View.GONE);
            focusLabel.setText("Highlight hidden.");
        } else {
            focusBox.setVisibility(View.VISIBLE);
            focusBox.setBackground(makeFocusBorder());
            focusLabel.setText("DevTools-style focus highlight placeholder enabled.");
        }
    }

    private void readPageTitle() {
        String title = webView == null ? "" : webView.getTitle();
        if (title == null || title.trim().isEmpty()) {
            title = "No page title available yet.";
        }
        focusLabel.setText("Page title: " + title);
        statusView.setText("Page title: " + title);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    private Button smallButton(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setAllCaps(false);
        button.setTextSize(12);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(Color.parseColor("#3B3B3B"));
        button.setMinHeight(0);
        button.setMinWidth(0);
        button.setPadding(dp(8), dp(6), dp(8), dp(6));
        return button;
    }

    private android.graphics.drawable.GradientDrawable makeFocusBorder() {
        android.graphics.drawable.GradientDrawable drawable = new android.graphics.drawable.GradientDrawable();
        drawable.setColor(Color.TRANSPARENT);
        drawable.setStroke(dp(3), Color.parseColor("#F4C542"));
        return drawable;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
