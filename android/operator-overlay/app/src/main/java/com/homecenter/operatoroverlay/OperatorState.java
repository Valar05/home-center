package com.homecenter.operatoroverlay;

import android.content.Context;
import android.content.SharedPreferences;

final class OperatorState {
    static final String PREFS = "home_center_operator_state";
    static final String KEY_CONTROL_ENABLED = "control_enabled";
    static final String KEY_MUTED = "muted";
    static final String KEY_LATEST_TEXT = "latest_text";
    static final String KEY_LATEST_SOURCE = "latest_source";
    static final String KEY_LAST_UPDATE_MS = "last_update_ms";
    static final String KEY_LAST_HEARTBEAT_MS = "last_heartbeat_ms";

    private OperatorState() {}

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static boolean controlEnabled(Context context) {
        return prefs(context).getBoolean(KEY_CONTROL_ENABLED, true);
    }

    static boolean muted(Context context) {
        return prefs(context).getBoolean(KEY_MUTED, false);
    }

    static String latestText(Context context) {
        return prefs(context).getString(KEY_LATEST_TEXT, "Home Center control ready.");
    }

    static String latestSource(Context context) {
        return prefs(context).getString(KEY_LATEST_SOURCE, "ChatGPT");
    }

    static long lastUpdateMs(Context context) {
        return prefs(context).getLong(KEY_LAST_UPDATE_MS, 0L);
    }

    static long lastHeartbeatMs(Context context) {
        return prefs(context).getLong(KEY_LAST_HEARTBEAT_MS, 0L);
    }

    static void setControlEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(KEY_CONTROL_ENABLED, enabled).apply();
    }

    static void setMuted(Context context, boolean muted) {
        prefs(context).edit().putBoolean(KEY_MUTED, muted).apply();
    }

    static void updateText(Context context, String source, String text, long nowMs) {
        String clean = text == null ? "" : text.trim();
        if (clean.length() > 8000) clean = clean.substring(0, 8000);
        String cleanSource = source == null || source.trim().isEmpty() ? "ChatGPT" : source.trim();
        if (cleanSource.length() > 80) cleanSource = cleanSource.substring(0, 80);
        prefs(context).edit()
                .putString(KEY_LATEST_TEXT, clean)
                .putString(KEY_LATEST_SOURCE, cleanSource)
                .putLong(KEY_LAST_UPDATE_MS, nowMs)
                .putLong(KEY_LAST_HEARTBEAT_MS, nowMs)
                .apply();
    }

    static void heartbeat(Context context, long nowMs) {
        prefs(context).edit().putLong(KEY_LAST_HEARTBEAT_MS, nowMs).apply();
    }
}
