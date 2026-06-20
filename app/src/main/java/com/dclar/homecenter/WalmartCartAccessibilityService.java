package com.dclar.homecenter;

import android.accessibilityservice.AccessibilityService;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONObject;

import java.util.Locale;

public final class WalmartCartAccessibilityService extends AccessibilityService {
    private static final long PAGE_WAIT_MS = 20000L;
    private static final long CLICK_COOLDOWN_MS = 6000L;
    private long lastClickAt = 0L;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getPackageName() == null) {
            return;
        }
        if (!CartRunStore.WALMART_PACKAGE.contentEquals(event.getPackageName())) {
            return;
        }
        JSONObject item = CartRunStore.armedItem(this);
        if (item == null) {
            return;
        }
        String status = item.optString("status", "");
        if (!CartRunStore.STATUS_ARMED.equals(status) && !CartRunStore.STATUS_ADD_ATTEMPTED.equals(status)) {
            return;
        }
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) {
            return;
        }
        String visibleText = collectText(root).toLowerCase(Locale.US);
        if (CartRunStore.STATUS_ADD_ATTEMPTED.equals(status)) {
            if (looksAdded(visibleText)) {
                put(item, "status", CartRunStore.STATUS_ADDED);
                put(item, "result", "Walmart reported an added/cart state.");
                CartRunStore.updateArmedItem(this, item, "added");
            }
            return;
        }
        if (!visibleMatchesItem(visibleText, item)) {
            long armedAt = item.optLong("armedAtElapsed", SystemClock.elapsedRealtime());
            if (SystemClock.elapsedRealtime() - armedAt > PAGE_WAIT_MS) {
                put(item, "status", CartRunStore.STATUS_BLOCKED);
                put(item, "result", "Visible Walmart product text did not match verified brand/size.");
                CartRunStore.updateArmedItem(this, item, "blocked: product text mismatch");
            }
            return;
        }
        if (SystemClock.elapsedRealtime() - lastClickAt < CLICK_COOLDOWN_MS) {
            return;
        }
        AccessibilityNodeInfo addButton = findAddButton(root);
        if (addButton == null) {
            put(item, "status", CartRunStore.STATUS_BLOCKED);
            put(item, "result", "Verified product was visible, but no enabled Add to Cart button was found.");
            CartRunStore.updateArmedItem(this, item, "blocked: add button missing");
            return;
        }
        if (addButton.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
            lastClickAt = SystemClock.elapsedRealtime();
            put(item, "status", CartRunStore.STATUS_ADD_ATTEMPTED);
            put(item, "result", "Clicked one Add to Cart control for the verified product.");
            CartRunStore.updateArmedItem(this, item, "add_attempted");
        } else {
            put(item, "status", CartRunStore.STATUS_BLOCKED);
            put(item, "result", "Add to Cart control was found but Android refused the click.");
            CartRunStore.updateArmedItem(this, item, "blocked: click refused");
        }
    }

    @Override
    public void onInterrupt() {
        CartRunStore.recordEvent(this, "interrupted");
    }

    private boolean visibleMatchesItem(String visibleText, JSONObject item) {
        String brand = clean(item.optString("brand", ""));
        String size = clean(item.optString("size", ""));
        String productName = clean(item.optString("productName", ""));
        boolean brandMatches = brand.isEmpty() || visibleText.contains(brand);
        boolean sizeMatches = size.isEmpty() || visibleText.contains(size) || visibleText.contains(size.replace(" ", ""));
        boolean nameMatches = productName.isEmpty() || containsUsefulNameTokens(visibleText, productName);
        return brandMatches && (sizeMatches || nameMatches);
    }

    private boolean containsUsefulNameTokens(String visibleText, String productName) {
        String[] tokens = productName.split("\\s+");
        int matched = 0;
        for (String token : tokens) {
            String clean = clean(token);
            if (clean.length() >= 4 && visibleText.contains(clean)) {
                matched++;
            }
        }
        return matched >= 2;
    }

    private AccessibilityNodeInfo findAddButton(AccessibilityNodeInfo node) {
        if (node == null) {
            return null;
        }
        if (node.isEnabled() && node.isClickable() && looksLikeAddButton(nodeText(node))) {
            return node;
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo found = findAddButton(node.getChild(i));
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    private boolean looksLikeAddButton(String text) {
        String clean = clean(text);
        return (clean.equals("add") || clean.contains("add to cart") || clean.contains("add item"))
                && !clean.contains("added")
                && !clean.contains("address");
    }

    private boolean looksAdded(String text) {
        return text.contains("added") || text.contains("go to cart") || text.contains("view cart");
    }

    private String collectText(AccessibilityNodeInfo node) {
        if (node == null) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        append(builder, node.getText());
        append(builder, node.getContentDescription());
        for (int i = 0; i < node.getChildCount(); i++) {
            builder.append(' ').append(collectText(node.getChild(i)));
        }
        return builder.toString();
    }

    private String nodeText(AccessibilityNodeInfo node) {
        StringBuilder builder = new StringBuilder();
        append(builder, node.getText());
        append(builder, node.getContentDescription());
        return builder.toString();
    }

    private void append(StringBuilder builder, CharSequence value) {
        if (value != null) {
            builder.append(' ').append(value);
        }
    }

    private String clean(String value) {
        return value == null ? "" : value.toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
    }

    private void put(JSONObject item, String key, Object value) {
        try {
            item.put(key, value);
        } catch (Exception ignored) {
        }
    }
}
