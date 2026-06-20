package com.dclar.homecenter;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

final class CartRunStore {
    static final String PREFS = "home_center";
    static final String KEY_CART_REVIEW_JSON = "cart_review_json";
    static final String KEY_CART_RUN_ARMED_ITEM = "cart_run_armed_item";
    static final String KEY_CART_RUN_LAST_EVENT = "cart_run_last_event";
    static final String STATUS_ARMED = "armed";
    static final String STATUS_ADD_ATTEMPTED = "add_attempted";
    static final String STATUS_ADDED = "added";
    static final String STATUS_BLOCKED = "blocked";
    static final String WALMART_PACKAGE = "com.walmart.android";

    private CartRunStore() { }

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static void saveReview(Context context, String jsonText) {
        prefs(context).edit().putString(KEY_CART_REVIEW_JSON, jsonText == null ? "" : jsonText).apply();
    }

    static void armItem(Context context, JSONObject item) {
        prefs(context).edit()
                .putString(KEY_CART_RUN_ARMED_ITEM, item == null ? "" : item.toString())
                .putString(KEY_CART_RUN_LAST_EVENT, "armed")
                .apply();
        CartEventBridge.record(context, "armed", item);
    }

    static JSONObject armedItem(Context context) {
        String raw = prefs(context).getString(KEY_CART_RUN_ARMED_ITEM, "");
        if (raw == null || raw.trim().isEmpty()) {
            return null;
        }
        try {
            return new JSONObject(raw);
        } catch (Exception ex) {
            return null;
        }
    }

    static void updateArmedItem(Context context, JSONObject item, String event) {
        prefs(context).edit()
                .putString(KEY_CART_RUN_ARMED_ITEM, item == null ? "" : item.toString())
                .putString(KEY_CART_RUN_LAST_EVENT, event == null ? "" : event)
                .apply();
        CartEventBridge.record(context, event, item);
    }

    static void recordEvent(Context context, String event) {
        recordEvent(context, event, null);
    }

    static void recordEvent(Context context, String event, JSONObject item) {
        prefs(context).edit().putString(KEY_CART_RUN_LAST_EVENT, event == null ? "" : event).apply();
        CartEventBridge.record(context, event, item);
    }

    static String lastEvent(Context context) {
        return prefs(context).getString(KEY_CART_RUN_LAST_EVENT, "");
    }
}
