package com.homecenter.operatoroverlay;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.util.Base64;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

final class OperatorState {
    static final String PREFS = "home_center_operator_state";
    static final String KEY_CONTROL_ENABLED = "control_enabled";
    static final String KEY_MUTED = "muted";
    static final String KEY_LATEST_TEXT = "latest_text";
    static final String KEY_LATEST_SOURCE = "latest_source";
    static final String KEY_LAST_UPDATE_MS = "last_update_ms";
    static final String KEY_LAST_HEARTBEAT_MS = "last_heartbeat_ms";
    static final String KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64 = "heartbeat_lights_payload_b64";
    static final String KEY_HEARTBEAT_LIGHTS_BYTES = "heartbeat_lights_bytes";
    static final String KEY_HEARTBEAT_LIGHTS_SHA256 = "heartbeat_lights_sha256";
    static final String KEY_HEARTBEAT_LIGHTS_UPDATED_MS = "heartbeat_lights_updated_ms";
    static final String KEY_SCREEN_ACTIVE_UNTIL_MS = "screen_active_until_ms";
    static final String KEY_SCREEN_YIELD_UNTIL_MS = "screen_yield_until_ms";
    static final String KEY_PANEL_COLLAPSED = "panel_collapsed";
    static final String KEY_OVERLAY_HIDDEN = "overlay_hidden";
    static final String KEY_OVERLAY_X = "overlay_x";
    static final String KEY_OVERLAY_Y = "overlay_y";
    static final String KEY_ADAM_REQUEST_ID = "adam_request_id";
    static final String KEY_ADAM_REQUEST_MODE = "adam_request_mode";
    static final String KEY_ADAM_REQUEST_PAYLOAD_B64 = "adam_request_payload_b64";
    static final String KEY_ADAM_REQUEST_BYTES = "adam_request_bytes";
    static final String KEY_ADAM_REQUEST_SHA256 = "adam_request_sha256";
    static final String KEY_SPOTIFY_REQUEST_ID = "spotify_request_id";
    static final String KEY_SPOTIFY_RECEIPT_B64 = "spotify_receipt_b64";
    static final String KEY_SPOTIFY_SUMMARY = "spotify_summary";
    static final String KEY_SPOTIFY_UPDATED_MS = "spotify_updated_ms";
    static final int MAX_HEARTBEAT_LIGHTS_BYTES = 32768;

    private OperatorState() {}

    static SharedPreferences prefs(Context context) { return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE); }
    static boolean controlEnabled(Context context) { return prefs(context).getBoolean(KEY_CONTROL_ENABLED, false); }
    static boolean muted(Context context) { return prefs(context).getBoolean(KEY_MUTED, false); }
    static String latestText(Context context) { return prefs(context).getString(KEY_LATEST_TEXT, "Home Center control ready."); }
    static String latestSource(Context context) { return prefs(context).getString(KEY_LATEST_SOURCE, "ChatGPT"); }
    static long lastUpdateMs(Context context) { return prefs(context).getLong(KEY_LAST_UPDATE_MS, 0L); }
    static long lastHeartbeatMs(Context context) { return prefs(context).getLong(KEY_LAST_HEARTBEAT_MS, 0L); }
    static String heartbeatLightsPayloadB64(Context context) { return prefs(context).getString(KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64, ""); }
    static long heartbeatLightsBytes(Context context) { return prefs(context).getLong(KEY_HEARTBEAT_LIGHTS_BYTES, 0L); }
    static String heartbeatLightsSha256(Context context) { return prefs(context).getString(KEY_HEARTBEAT_LIGHTS_SHA256, ""); }
    static long heartbeatLightsUpdatedMs(Context context) { return prefs(context).getLong(KEY_HEARTBEAT_LIGHTS_UPDATED_MS, 0L); }
    static long screenActiveUntilMs(Context context) { return prefs(context).getLong(KEY_SCREEN_ACTIVE_UNTIL_MS, 0L); }
    static long screenYieldUntilMs(Context context) { return prefs(context).getLong(KEY_SCREEN_YIELD_UNTIL_MS, 0L); }
    static boolean panelCollapsed(Context context) { return prefs(context).getBoolean(KEY_PANEL_COLLAPSED, true); }
    static boolean overlayHidden(Context context) { return prefs(context).getBoolean(KEY_OVERLAY_HIDDEN, false); }
    static int overlayX(Context context) { return prefs(context).getInt(KEY_OVERLAY_X, 8); }
    static int overlayY(Context context) { return prefs(context).getInt(KEY_OVERLAY_Y, 28); }
    static long adamRequestId(Context context) { return prefs(context).getLong(KEY_ADAM_REQUEST_ID, 0L); }
    static String adamRequestMode(Context context) { return prefs(context).getString(KEY_ADAM_REQUEST_MODE, "terminal"); }
    static String adamRequestPayloadB64(Context context) { return prefs(context).getString(KEY_ADAM_REQUEST_PAYLOAD_B64, ""); }
    static long adamRequestBytes(Context context) { return prefs(context).getLong(KEY_ADAM_REQUEST_BYTES, 0L); }
    static String adamRequestSha256(Context context) { return prefs(context).getString(KEY_ADAM_REQUEST_SHA256, ""); }
    static long spotifyRequestId(Context context) { return prefs(context).getLong(KEY_SPOTIFY_REQUEST_ID, 0L); }
    static String spotifyReceiptB64(Context context) { return prefs(context).getString(KEY_SPOTIFY_RECEIPT_B64, ""); }
    static String spotifySummary(Context context) { return prefs(context).getString(KEY_SPOTIFY_SUMMARY, "Spotify • waiting"); }
    static long spotifyUpdatedMs(Context context) { return prefs(context).getLong(KEY_SPOTIFY_UPDATED_MS, 0L); }

    static void setControlEnabled(Context context, boolean enabled) {
        SharedPreferences.Editor editor = prefs(context).edit().putBoolean(KEY_CONTROL_ENABLED, enabled);
        if (!enabled) editor.putLong(KEY_SCREEN_ACTIVE_UNTIL_MS, 0L).putLong(KEY_SCREEN_YIELD_UNTIL_MS, 0L);
        editor.commit();
    }

    static boolean restoreMigrationState(Context context, Bundle extras) {
        SharedPreferences.Editor editor = prefs(context).edit().putBoolean(KEY_CONTROL_ENABLED, false).putLong(KEY_SCREEN_ACTIVE_UNTIL_MS, 0L).putLong(KEY_SCREEN_YIELD_UNTIL_MS, 0L);
        if (extras != null && extras.containsKey(KEY_MUTED)) editor.putBoolean(KEY_MUTED, extras.getBoolean(KEY_MUTED));
        if (extras != null && extras.containsKey(KEY_LAST_HEARTBEAT_MS)) editor.putLong(KEY_LAST_HEARTBEAT_MS, extras.getLong(KEY_LAST_HEARTBEAT_MS));
        if (extras != null && extras.containsKey(KEY_LAST_UPDATE_MS)) editor.putLong(KEY_LAST_UPDATE_MS, extras.getLong(KEY_LAST_UPDATE_MS));
        if (extras != null && extras.containsKey(KEY_LATEST_SOURCE)) editor.putString(KEY_LATEST_SOURCE, sanitizeMigrationSource(extras.getString(KEY_LATEST_SOURCE)));
        if (extras != null && extras.containsKey(KEY_PANEL_COLLAPSED)) editor.putBoolean(KEY_PANEL_COLLAPSED, extras.getBoolean(KEY_PANEL_COLLAPSED));
        if (extras != null && extras.containsKey(KEY_OVERLAY_HIDDEN)) editor.putBoolean(KEY_OVERLAY_HIDDEN, extras.getBoolean(KEY_OVERLAY_HIDDEN));
        return editor.commit();
    }

    private static String sanitizeMigrationSource(String source) {
        String clean = source == null ? "ChatGPT" : source.trim();
        clean = clean.replace('\r', ' ').replace('\n', ' ').replace(',', ' ');
        if (clean.isEmpty()) clean = "ChatGPT";
        if (clean.length() > 80) clean = clean.substring(0, 80);
        return clean;
    }

    static void setMuted(Context context, boolean muted) { prefs(context).edit().putBoolean(KEY_MUTED, muted).apply(); }
    static void setPanelCollapsed(Context context, boolean collapsed) { prefs(context).edit().putBoolean(KEY_PANEL_COLLAPSED, collapsed).apply(); }
    static void setOverlayHidden(Context context, boolean hidden) { prefs(context).edit().putBoolean(KEY_OVERLAY_HIDDEN, hidden).commit(); }
    static void setOverlayPosition(Context context, int x, int y) { prefs(context).edit().putInt(KEY_OVERLAY_X, x).putInt(KEY_OVERLAY_Y, y).apply(); }

    private static String sha256(byte[] bytes) {
        try {
            java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(bytes);
            StringBuilder out = new StringBuilder(hash.length * 2);
            for (byte b : hash) out.append(String.format("%02x", b & 0xff));
            return out.toString();
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }

    private static String encodedUrlCommand(String operation, String url) {
        String exact = url == null ? "" : url.trim();
        String lower = exact.toLowerCase(Locale.ROOT);
        if (!(lower.startsWith("https://") || lower.startsWith("http://"))) return "";
        if (exact.length() > 2048) return "";
        String encoded = Base64.encodeToString(exact.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);
        return "bash tools/fortress_phone_ops.sh " + operation + "-b64 " + encoded;
    }

    private static String prefixedUrlAlias(String exact, String lower) {
        String[] openPrefixes = {"chrome ", "chromium ", "open chrome ", "open chromium "};
        for (String prefix : openPrefixes) {
            if (lower.startsWith(prefix)) {
                return encodedUrlCommand("chrome-open", exact.substring(prefix.length()));
            }
        }
        String[] navigatePrefixes = {"navigate ", "navigate chrome ", "navigate chromium ", "go ", "go chrome ", "go chromium "};
        for (String prefix : navigatePrefixes) {
            if (lower.startsWith(prefix)) {
                return encodedUrlCommand("chrome-navigate", exact.substring(prefix.length()));
            }
        }
        return "";
    }

    private static String deterministicTerminalAlias(String text) {
        String exact = text == null ? "" : text.trim();
        String key = exact.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
        String urlAlias = prefixedUrlAlias(exact, exact.toLowerCase(Locale.ROOT));
        if (!urlAlias.isEmpty()) return urlAlias;
        if (key.equals("restart") || key.equals("restart hc") || key.equals("restart home center") || key.equals("restart overlay") || key.equals("repair overlay")) {
            return "bash tools/fortress_phone_ops.sh overlay-restart";
        }
        if (key.equals("status") || key.equals("phone status") || key.equals("fortress status")) {
            return "bash tools/fortress_phone_ops.sh status";
        }
        if (key.equals("chrome") || key.equals("chromium") || key.equals("open chrome") || key.equals("open chromium")) {
            return "bash tools/fortress_phone_ops.sh chrome-open";
        }
        if (key.equals("reload") || key.equals("reload chrome") || key.equals("reload chromium")) {
            return "bash tools/fortress_phone_ops.sh chrome-reload";
        }
        if (key.equals("back") || key.equals("back chrome") || key.equals("chrome back")) {
            return "bash tools/fortress_phone_ops.sh chrome-back";
        }
        if (key.equals("canary") || key.equals("phone canary") || key.equals("test phone") || key.equals("test overlay") || key.equals("test chrome") || key.equals("chrome canary")) {
            return "bash tools/fortress_phone_ops.sh canary";
        }
        return exact;
    }

    static void submitAdamRequest(Context context, String mode, String text, long nowMs) {
        String cleanMode = mode == null ? "terminal" : mode.trim().toLowerCase();
        if (!(cleanMode.equals("terminal") || cleanMode.equals("chat") || cleanMode.equals("continue") || cleanMode.equals("vlad") || cleanMode.equals("radio"))) throw new IllegalArgumentException("unsupported Adam mode");
        String exact = text == null ? "" : text;
        if (exact.trim().isEmpty()) return;
        if (cleanMode.equals("terminal")) exact = deterministicTerminalAlias(exact);
        byte[] bytes = exact.getBytes(StandardCharsets.UTF_8);
        String payload = Base64.encodeToString(bytes, Base64.NO_WRAP);
        prefs(context).edit()
                .putLong(KEY_ADAM_REQUEST_ID, Math.max(1L, nowMs))
                .putString(KEY_ADAM_REQUEST_MODE, cleanMode)
                .putString(KEY_ADAM_REQUEST_PAYLOAD_B64, payload)
                .putLong(KEY_ADAM_REQUEST_BYTES, bytes.length)
                .putString(KEY_ADAM_REQUEST_SHA256, sha256(bytes))
                .commit();
    }

    static void updateSpotifyReceipt(Context context, long requestId, String receiptJson, String summary, long nowMs) {
        String cleanReceipt = receiptJson == null ? "{}" : receiptJson.trim();
        if (cleanReceipt.length() > 12000) cleanReceipt = cleanReceipt.substring(0, 12000);
        String encoded = Base64.encodeToString(cleanReceipt.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);
        String cleanSummary = sanitizeSpotifySummary(summary);
        prefs(context).edit().putLong(KEY_SPOTIFY_REQUEST_ID, Math.max(1L, requestId)).putString(KEY_SPOTIFY_RECEIPT_B64, encoded).putString(KEY_SPOTIFY_SUMMARY, cleanSummary).putLong(KEY_SPOTIFY_UPDATED_MS, Math.max(1L, nowMs)).commit();
    }
    static void updateSpotifySummary(Context context, String summary, long nowMs) { prefs(context).edit().putString(KEY_SPOTIFY_SUMMARY, sanitizeSpotifySummary(summary)).putLong(KEY_SPOTIFY_UPDATED_MS, Math.max(1L, nowMs)).commit(); }
    private static String sanitizeSpotifySummary(String summary) {
        String cleanSummary = summary == null ? "Spotify updated" : summary.trim();
        cleanSummary = cleanSummary.replace('\r', ' ').replace('\n', ' ').replace(',', ' ');
        if (cleanSummary.isEmpty()) cleanSummary = "Spotify updated";
        if (cleanSummary.length() > 240) cleanSummary = cleanSummary.substring(0, 240);
        return cleanSummary;
    }

    /**
     * Encode heartbeat JSON without replacement semantics. Standard String#getBytes
     * silently replaces unpaired UTF-16 surrogates, which would destroy evidence
     * before the persisted byte-count/SHA identity exists. This helper rejects that
     * input before SharedPreferences mutation while remaining byte-identical to
     * ordinary UTF-8 encoding for well-formed Unicode.
     */
    static byte[] strictHeartbeatLightsUtf8(String payloadJson) {
        String exact = payloadJson == null ? "" : payloadJson;
        try {
            ByteBuffer encoded = StandardCharsets.UTF_8
                    .newEncoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .encode(CharBuffer.wrap(exact));
            byte[] bytes = new byte[encoded.remaining()];
            encoded.get(bytes);
            return bytes;
        } catch (CharacterCodingException invalidEncoding) {
            throw new HeartbeatIngressPolicy.CallerInvalidPayloadException(
                    "heartbeat lights payload contains invalid Unicode",
                    invalidEncoding);
        }
    }

    static void updateHeartbeatLights(Context context, String payloadJson, long nowMs) {
        if (payloadJson == null || payloadJson.trim().isEmpty()) return;
        byte[] bytes = strictHeartbeatLightsUtf8(payloadJson);
        if (bytes.length > MAX_HEARTBEAT_LIGHTS_BYTES) {
            throw new HeartbeatIngressPolicy.CallerInvalidPayloadException(
                    "heartbeat lights payload exceeds " + MAX_HEARTBEAT_LIGHTS_BYTES + " bytes");
        }
        String encoded = Base64.encodeToString(bytes, Base64.NO_WRAP);
        boolean committed = prefs(context).edit()
                .putString(KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64, encoded)
                .putLong(KEY_HEARTBEAT_LIGHTS_BYTES, bytes.length)
                .putString(KEY_HEARTBEAT_LIGHTS_SHA256, sha256(bytes))
                .putLong(KEY_HEARTBEAT_LIGHTS_UPDATED_MS, Math.max(1L, nowMs))
                .commit();
        if (!committed) throw new IllegalStateException("heartbeat lights commit failed");
    }

    static void updateText(Context context, String source, String text, long nowMs) {
        String clean = text == null ? "" : text.trim(); if (clean.length() > 8000) clean = clean.substring(0, 8000);
        String cleanSource = source == null || source.trim().isEmpty() ? "ChatGPT" : source.trim(); if (cleanSource.length() > 80) cleanSource = cleanSource.substring(0, 80);
        prefs(context).edit().putString(KEY_LATEST_TEXT, clean).putString(KEY_LATEST_SOURCE, cleanSource).putLong(KEY_LAST_UPDATE_MS, nowMs).putLong(KEY_LAST_HEARTBEAT_MS, nowMs).apply();
    }
    static void heartbeat(Context context, long nowMs) { prefs(context).edit().putLong(KEY_LAST_HEARTBEAT_MS, nowMs).apply(); }
    static void setScreenActivity(Context context, long activeUntilMs, long yieldUntilMs) { prefs(context).edit().putLong(KEY_SCREEN_ACTIVE_UNTIL_MS, Math.max(0L, activeUntilMs)).putLong(KEY_SCREEN_YIELD_UNTIL_MS, Math.max(0L, yieldUntilMs)).apply(); }
    static void clearScreenActivity(Context context) { setScreenActivity(context, 0L, 0L); }
}
