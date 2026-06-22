package com.dclar.homecenter;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public final class NetrunnerActivity extends Activity {
    private WebView webView;
    private EditText urlEdit;
    private Button backButton;
    private Button forwardButton;
    private Button reloadButton;
    private TextView browserStatus;
    private TextView focusLabel;
    private View focusBox;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        loadUrl("https://example.com");
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            syncNavButtons();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#0E1116"));
        root.setPadding(dp(14), dp(14), dp(14), dp(14));

        TextView title = new TextView(this);
        title.setText("Netrunner");
        title.setTextColor(Color.parseColor("#F6F0E3"));
        title.setTextSize(28);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, matchWrap());

        browserStatus = new TextView(this);
        browserStatus.setText("Loading example.com");
        browserStatus.setTextColor(Color.parseColor("#A8B0BC"));
        browserStatus.setTextSize(13);
        browserStatus.setGravity(Gravity.CENTER_HORIZONTAL);
        browserStatus.setPadding(0, dp(4), 0, dp(10));
        root.addView(browserStatus, matchWrap());

        LinearLayout urlRow = new LinearLayout(this);
        urlRow.setOrientation(LinearLayout.HORIZONTAL);
        urlRow.setGravity(Gravity.CENTER_VERTICAL);

        urlEdit = new EditText(this);
        urlEdit.setHint("Enter a URL");
        urlEdit.setSingleLine(true);
        urlEdit.setTextColor(Color.parseColor("#F6F0E3"));
        urlEdit.setHintTextColor(Color.parseColor("#8A93A3"));
        urlEdit.setBackgroundColor(Color.parseColor("#1A202A"));
        urlEdit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        urlEdit.setImeOptions(EditorInfo.IME_ACTION_GO);
        urlEdit.setSelectAllOnFocus(true);
        urlEdit.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        urlRow.addView(urlEdit);

        Button goButton = navButton("Go");
        LinearLayout.LayoutParams goParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        goParams.setMargins(dp(8), 0, 0, 0);
        goButton.setLayoutParams(goParams);
        urlRow.addView(goButton);
        root.addView(urlRow, matchWrap());

        LinearLayout navRow = new LinearLayout(this);
        navRow.setOrientation(LinearLayout.HORIZONTAL);
        navRow.setPadding(0, dp(10), 0, dp(10));

        backButton = navButton("Back");
        forwardButton = navButton("Forward");
        reloadButton = navButton("Reload");
        navRow.addView(backButton, weightedButton());
        navRow.addView(forwardButton, weightedButton());
        navRow.addView(reloadButton, weightedButton());
        root.addView(navRow, matchWrap());

        LinearLayout split = new LinearLayout(this);
        split.setOrientation(LinearLayout.VERTICAL);
        split.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f));

        LinearLayout browserPane = panel("#131922");
        browserPane.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                3f));

        FrameLayout browserFrame = new FrameLayout(this);
        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        webView.setBackgroundColor(Color.WHITE);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (request != null && request.getUrl() != null) {
                    loadUrl(request.getUrl().toString());
                    return true;
                }
                return false;
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                loadUrl(url);
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                syncUrlState(url);
            }
        });
        browserFrame.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        focusBox = new View(this);
        focusBox.setBackgroundColor(Color.TRANSPARENT);
        focusBox.setVisibility(View.GONE);
        browserFrame.addView(focusBox, new FrameLayout.LayoutParams(dp(140), dp(96), Gravity.CENTER));

        browserPane.addView(browserFrame, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f));

        split.addView(browserPane);

        LinearLayout chatPane = panel("#18202B");
        LinearLayout.LayoutParams chatParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                2f);
        chatParams.setMargins(0, dp(10), 0, 0);
        chatPane.setLayoutParams(chatParams);

        TextView chatTitle = new TextView(this);
        chatTitle.setText("Chat placeholder");
        chatTitle.setTextColor(Color.parseColor("#F6F0E3"));
        chatTitle.setTypeface(Typeface.DEFAULT_BOLD);
        chatTitle.setTextSize(18);
        chatPane.addView(chatTitle, matchWrap());

        TextView chatBody = new TextView(this);
        chatBody.setText(
                "This pane is reserved for the Netrunner chat layer.\n\n"
                        + "Browser remains active on the other side of the split.");
        chatBody.setTextColor(Color.parseColor("#C8D0DB"));
        chatBody.setTextSize(15);
        chatBody.setLineSpacing(0f, 1.15f);
        chatBody.setPadding(0, dp(10), 0, dp(12));
        ScrollView chatScroll = new ScrollView(this);
        chatScroll.addView(chatBody);
        chatPane.addView(chatScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f));

        LinearLayout toolRow = new LinearLayout(this);
        toolRow.setOrientation(LinearLayout.HORIZONTAL);
        toolRow.setGravity(Gravity.CENTER_VERTICAL);

        Button highlight = navButton("Highlight");
        Button pageTitle = navButton("Read title");
        Button homeCenter = navButton("Home Center");
        toolRow.addView(highlight, weightedButton());
        toolRow.addView(pageTitle, weightedButton());
        toolRow.addView(homeCenter, weightedButton());
        chatPane.addView(toolRow, matchWrap());

        focusLabel = new TextView(this);
        focusLabel.setText("Element tools: inspect mode placeholder. Long-press commands land next.");
        focusLabel.setTextColor(Color.parseColor("#C8D0DB"));
        focusLabel.setTextSize(13);
        focusLabel.setPadding(0, dp(10), 0, 0);
        chatPane.addView(focusLabel, matchWrap());

        split.addView(chatPane);
        root.addView(split);

        goButton.setOnClickListener(v -> loadFromField());
        urlEdit.setOnEditorActionListener((v, actionId, event) -> {
            boolean shouldGo = actionId == EditorInfo.IME_ACTION_GO
                    || (event != null
                    && event.getAction() == KeyEvent.ACTION_DOWN
                    && event.getKeyCode() == KeyEvent.KEYCODE_ENTER);
            if (shouldGo) {
                loadFromField();
                return true;
            }
            return false;
        });

        backButton.setOnClickListener(v -> {
            if (webView != null && webView.canGoBack()) {
                webView.goBack();
            }
            syncNavButtons();
        });
        forwardButton.setOnClickListener(v -> {
            if (webView != null && webView.canGoForward()) {
                webView.goForward();
            }
            syncNavButtons();
        });
        reloadButton.setOnClickListener(v -> {
            if (webView != null) {
                webView.reload();
            }
        });
        highlight.setOnClickListener(v -> toggleHighlight());
        pageTitle.setOnClickListener(v -> readPageTitle());
        homeCenter.setOnClickListener(v -> startActivity(new Intent(this, MainActivity.class)));

        setContentView(root);
        syncNavButtons();
    }

    private void loadFromField() {
        if (urlEdit == null) {
            return;
        }
        loadUrl(urlEdit.getText().toString());
    }

    private void loadUrl(String raw) {
        if (webView == null) {
            return;
        }
        String clean = normalizeUrl(raw);
        urlEdit.setText(clean);
        urlEdit.setSelection(urlEdit.length());
        browserStatus.setText("Loading " + clean);
        webView.loadUrl(clean);
        syncNavButtons();
    }

    private void syncUrlState(String url) {
        if (urlEdit != null && url != null && !url.isEmpty()) {
            urlEdit.setText(url);
            urlEdit.setSelection(urlEdit.length());
        }
        if (browserStatus != null) {
            browserStatus.setText(url == null || url.isEmpty() ? "Ready" : "Loaded " + url);
        }
        syncNavButtons();
    }

    private void syncNavButtons() {
        if (webView == null) {
            return;
        }
        backButton.setEnabled(webView.canGoBack());
        forwardButton.setEnabled(webView.canGoForward());
    }

    private void toggleHighlight() {
        if (focusBox == null || focusLabel == null) {
            return;
        }
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
        if (focusLabel != null) {
            focusLabel.setText("Page title: " + title);
        }
        if (browserStatus != null) {
            browserStatus.setText("Page title: " + title);
        }
    }

    private String normalizeUrl(String raw) {
        String clean = raw == null ? "" : raw.trim();
        if (clean.isEmpty()) {
            return "https://example.com";
        }
        Uri parsed = Uri.parse(clean);
        if (parsed.getScheme() == null || parsed.getScheme().isEmpty()) {
            clean = "https://" + clean;
        }
        return clean;
    }

    private Button navButton(String text) {
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

    private GradientDrawable makeFocusBorder() {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(Color.TRANSPARENT);
        drawable.setStroke(dp(3), Color.parseColor("#F4C542"));
        return drawable;
    }

    private LinearLayout panel(String color) {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(12), dp(12), dp(12), dp(12));
        panel.setBackgroundColor(Color.parseColor(color));
        return panel;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams weightedButton() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f);
        params.setMargins(0, 0, dp(8), 0);
        return params;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
