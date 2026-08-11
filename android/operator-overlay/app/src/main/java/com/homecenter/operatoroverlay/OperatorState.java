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
    static final String KEY_SCREEN_ACTIVE_UNTIL_MS = "screen_active_until_ms";
    static final String KEY_SCREEN_YIELD_UNTIL_MS = "screen_yield_until_ms";
    static final String KEY_PANEL_COLLAPSED = "panel_collapsed";

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

    static long screenActiveUntilMs(Context context) {
        return prefs(context).getLong(KEY_SCREEN_ACTIVE_UNTIL_MS, 0L);
    }

    static long screenYieldUntilMs(Context context) {
        return prefs(context).getLong(KEY_SCREEN_YIELD_UNTIL_MS, 0L);
    }

    static boolean panelCollapsed(Context context) {
        return prefs(context).getBoolean(KEY_PANEL_COLLAPSED, false);
    }

    static void setControlEnabled(Context context, boolean enabled) {
        SharedPreferences.Editor editor = prefs(context).edit()
                .putBoolean(KEY_CONTROL_ENABLED, enabled);
        if (!enabled) {
            editor.putLong(KEY_SCREEN_ACTIVE_UNTIL_MS, 0L)
                    .putLong(KEY_SCREEN_YIELD_UNTIL_MS, 0L);
        }
        editor.apply();
    }

    static void setMuted(Context context, boolean muted) {
        prefs(context).edit().putBoolean(KEY_MUTED, muted).apply();
    }

    static void setPanelCollapsed(Context context, boolean collapsed) {
        prefs(context).edit().putBoolean(KEY_PANEL_COLLAPSED, collapsed).apply();
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

    static void setScreenActivity(Context context, long activeUntilMs, long yieldUntilMs) {
        prefs(context).edit()
                .putLong(KEY_SCREEN_ACTIVE_UNTIL_MS, Math.max(0L, activeUntilMs))
                .putLong(KEY_SCREEN_YIELD_UNTIL_MS, Math.max(0L, yieldUntilMs))
                .apply();
    }

    static void clearScreenActivity(Context context) {
        setScreenActivity(context, 0L, 0L);
    }
}
