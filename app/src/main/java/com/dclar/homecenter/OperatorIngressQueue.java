package com.dclar.homecenter;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

/**
 * Durable, owner-local FIFO for messages authored while an agent turn is already in flight.
 *
 * The queue is transport only. Enqueueing text is not permission to execute it concurrently,
 * does not bypass confirmation gates, and does not reinterpret the text. The ordinary chat
 * submission path receives the exact queued text later, one item at a time.
 */
final class OperatorIngressQueue {
    static final String SCHEMA = "home-center.operator-ingress-queue.v1";
    static final int MAX_ITEMS = 64;

    private static final String PREFS = "home_center_operator_ingress_queue_v1";
    private static final String KEY_QUEUE = "queue_json";
    private static final String KEY_INFLIGHT = "inflight_json";

    static final class Item {
        final String id;
        final String text;
        final String conversationId;
        final String source;
        final long enqueuedAtMs;

        Item(String id, String text, String conversationId, String source, long enqueuedAtMs) {
            this.id = id == null ? "" : id;
            this.text = text == null ? "" : text;
            this.conversationId = conversationId == null ? "" : conversationId;
            this.source = source == null ? "" : source;
            this.enqueuedAtMs = Math.max(0L, enqueuedAtMs);
        }

        JSONObject toJson() {
            JSONObject json = new JSONObject();
            try {
                json.put("schema", SCHEMA);
                json.put("id", id);
                json.put("text", text);
                json.put("conversationId", conversationId);
                json.put("source", source);
                json.put("enqueuedAtMs", enqueuedAtMs);
            } catch (Exception ignored) {
            }
            return json;
        }

        static Item fromJson(JSONObject json) {
            if (json == null) return null;
            String id = json.optString("id", "").trim();
            String text = json.optString("text", "");
            if (id.isEmpty() || text.trim().isEmpty()) return null;
            return new Item(
                    id,
                    text,
                    json.optString("conversationId", ""),
                    json.optString("source", ""),
                    json.optLong("enqueuedAtMs", 0L));
        }
    }

    private final SharedPreferences prefs;

    OperatorIngressQueue(Context context) {
        Context app = context == null ? null : context.getApplicationContext();
        if (app == null) throw new IllegalArgumentException("context is required");
        prefs = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    synchronized Item enqueue(String exactText, String conversationId, String source) {
        if (exactText == null || exactText.trim().isEmpty()) return null;
        List<Item> items = readQueue();
        if (items.size() >= MAX_ITEMS) return null;
        Item item = new Item(
                UUID.randomUUID().toString(),
                exactText,
                conversationId == null ? "" : conversationId,
                source == null ? "" : source,
                System.currentTimeMillis());
        items.add(item);
        writeQueue(items);
        return item;
    }

    synchronized int size() {
        return readQueue().size();
    }

    synchronized List<Item> snapshot() {
        return Collections.unmodifiableList(new ArrayList<>(readQueue()));
    }

    /**
     * Moves the head to an explicit in-flight slot before dispatch. If the process dies between
     * this step and completeDispatch(), recoverInflight() restores the item to the head. That
     * favors a possible duplicate conversational turn over silently losing operator input.
     */
    synchronized Item beginDispatch() {
        if (readInflight() != null) return null;
        List<Item> items = readQueue();
        if (items.isEmpty()) return null;
        Item item = items.remove(0);
        boolean ok = prefs.edit()
                .putString(KEY_QUEUE, encode(items))
                .putString(KEY_INFLIGHT, item.toJson().toString())
                .commit();
        return ok ? item : null;
    }

    synchronized void completeDispatch(String id) {
        Item inflight = readInflight();
        if (inflight == null) return;
        if (id != null && !id.isEmpty() && !id.equals(inflight.id)) return;
        prefs.edit().remove(KEY_INFLIGHT).commit();
    }

    synchronized void retryInflight(String id) {
        Item inflight = readInflight();
        if (inflight == null) return;
        if (id != null && !id.isEmpty() && !id.equals(inflight.id)) return;
        List<Item> items = readQueue();
        if (!containsId(items, inflight.id)) items.add(0, inflight);
        prefs.edit()
                .putString(KEY_QUEUE, encode(items))
                .remove(KEY_INFLIGHT)
                .commit();
    }

    synchronized void recoverInflight() {
        Item inflight = readInflight();
        if (inflight == null) return;
        List<Item> items = readQueue();
        if (!containsId(items, inflight.id)) items.add(0, inflight);
        prefs.edit()
                .putString(KEY_QUEUE, encode(items))
                .remove(KEY_INFLIGHT)
                .commit();
    }

    private List<Item> readQueue() {
        List<Item> out = new ArrayList<>();
        String raw = prefs.getString(KEY_QUEUE, "");
        if (raw == null || raw.trim().isEmpty()) return out;
        try {
            JSONArray array = new JSONArray(raw);
            for (int i = 0; i < array.length(); i++) {
                Item item = Item.fromJson(array.optJSONObject(i));
                if (item != null && !containsId(out, item.id)) out.add(item);
                if (out.size() >= MAX_ITEMS) break;
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    private Item readInflight() {
        String raw = prefs.getString(KEY_INFLIGHT, "");
        if (raw == null || raw.trim().isEmpty()) return null;
        try {
            return Item.fromJson(new JSONObject(raw));
        } catch (Exception ignored) {
            return null;
        }
    }

    private void writeQueue(List<Item> items) {
        prefs.edit().putString(KEY_QUEUE, encode(items)).commit();
    }

    private String encode(List<Item> items) {
        JSONArray array = new JSONArray();
        if (items != null) {
            for (Item item : items) {
                if (item != null) array.put(item.toJson());
            }
        }
        return array.toString();
    }

    private static boolean containsId(List<Item> items, String id) {
        if (items == null || id == null || id.isEmpty()) return false;
        for (Item item : items) {
            if (item != null && id.equals(item.id)) return true;
        }
        return false;
    }
}