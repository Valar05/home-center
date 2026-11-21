package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.SystemClock;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.UUID;

/** Bounded local metadata-only receipt ledger; NEVER stores audio, transcripts,
 * paths, tokens, or network addresses. Future Home Center adapter can read this
 * only through an explicitly authenticated boundary, not an exported provider. */
final class ControlReceipts {
    private static final String PREF = "ritsu_local_mic_receipts_v1";
    private static final int KEEP = 64;
    private final String sessionId = UUID.randomUUID().toString();
    private long sequence;
    private final Context app;
    ControlReceipts(Context context) { this.app = context.getApplicationContext(); }

    synchronized void append(String event, ListeningPolicy.Mode prior,
                             ListeningPolicy.Mode next, String reason) {
        SharedPreferences prefs = app.getSharedPreferences(PREF, Context.MODE_PRIVATE);
        JSONArray old;
        try { old = new JSONArray(prefs.getString("receipts", "[]")); }
        catch (JSONException ignored) { old = new JSONArray(); }
        JSONArray kept = new JSONArray();
        for (int i = Math.max(0, old.length() - KEEP + 1); i < old.length(); i++)
            kept.put(old.optJSONObject(i));
        JSONObject row = new JSONObject();
        try {
            row.put("sessionId", sessionId);
            row.put("seq", ++sequence);
            row.put("elapsedMs", SystemClock.elapsedRealtime());
            row.put("event", event);
            row.put("from", prior.name());
            row.put("to", next.name());
            row.put("reason", reason);
        } catch (JSONException ignored) { return; }
        kept.put(row);
        prefs.edit().putString("receipts", kept.toString()).apply();
    }
}
