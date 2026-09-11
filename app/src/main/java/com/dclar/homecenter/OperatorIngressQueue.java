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
 *
 * Persistence is fail-closed: no method reports a durable state transition when the synchronous
 * SharedPreferences commit failed, and malformed stored queue state is surfaced rather than
 * silently overwritten as an empty queue.
 */
final class OperatorIngressQueue {
    static final String SCHEMA = "home-center.operator-ingress-queue.v1";
    static final int MAX_ITEMS = 64;

    private static final String PREFS = "home_center_operator_ingress_queue_v1";
    private static final String KEY_QUEUE = "queue_json";
    private static final String KEY_INFLIGHT = "inflight_json";
    private static final String KEY_DRAFT = "draft_text";

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
            String schema = json.optString("schema", SCHEMA).trim();
            if (!schema.isEmpty() && !SCHEMA.equals(schema)) return null;
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
        int occupied = items.size() + (readInflight() == null ? 0 : 1);
        if (occupied >= MAX_ITEMS) return null;
        Item item = new Item(
                UUID.randomUUID().toString(),
                exactText,
                conversationId == null ? "" : conversationId,
                source == null ? "" : source,
                System.currentTimeMillis());
        items.add(item);
        requireCommit(
                prefs.edit()
                        .putString(KEY_QUEUE, encode(items))
                        .remove(KEY_DRAFT)
                        .commit(),
                "enqueue");
        return item;
    }

    synchronized String draft() {
        String value = prefs.getString(KEY_DRAFT, "");
        return value == null ? "" : value;
    }

    synchronized void saveDraft(String exactText) {
        String value = exactText == null ? "" : exactText;
        SharedPreferences.Editor editor = prefs.edit();
        if (value.isEmpty()) editor.remove(KEY_DRAFT);
        else editor.putString(KEY_DRAFT, value);
        requireCommit(editor.commit(), "save_draft");
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
        requireCommit(
                prefs.edit()
                        .putString(KEY_QUEUE, encode(items))
                        .putString(KEY_INFLIGHT, item.toJson().toString())
                        .commit(),
                "begin_dispatch");
        return item;
    }

    synchronized void completeDispatch(String id) {
        Item inflight = readInflight();
        if (inflight == null) return;
        if (id != null && !id.isEmpty() && !id.equals(inflight.id)) return;
        requireCommit(prefs.edit().remove(KEY_INFLIGHT).commit(), "complete_dispatch");
    }

    synchronized void retryInflight(String id) {
        Item inflight = readInflight();
        if (inflight == null) return;
        if (id != null && !id.isEmpty() && !id.equals(inflight.id)) return;
        restoreInflightToHead(inflight, "retry_inflight");
    }

    synchronized void recoverInflight() {
        Item inflight = readInflight();
        if (inflight == null) return;
        restoreInflightToHead(inflight, "recover_inflight");
    }

    private void restoreInflightToHead(Item inflight, String operation) {
        List<Item> items = readQueue();
        if (!containsId(items, inflight.id)) {
            if (items.size() >= MAX_ITEMS) {
                throw new IllegalStateException("operator ingress cannot restore in-flight item: queue is at capacity");
            }
            items.add(0, inflight);
        }
        requireCommit(
                prefs.edit()
                        .putString(KEY_QUEUE, encode(items))
                        .remove(KEY_INFLIGHT)
                        .commit(),
                operation);
    }

    private List<Item> readQueue() {
        List<Item> out = new ArrayList<>();
        String raw = prefs.getString(KEY_QUEUE, "");
        if (raw == null || raw.trim().isEmpty()) return out;
        try {
            JSONArray array = new JSONArray(raw);
            if (array.length() > MAX_ITEMS) {
                throw new IllegalStateException("operator ingress queue exceeds capacity");
            }
            for (int i = 0; i < array.length(); i++) {
                JSONObject encoded = array.optJSONObject(i);
                Item item = Item.fromJson(encoded);
                if (item == null) {
                    throw new IllegalStateException("operator ingress queue contains an invalid item at index " + i);
                }
                if (containsId(out, item.id)) {
                    throw new IllegalStateException("operator ingress queue contains duplicate id " + item.id);
                }
                out.add(item);
            }
            return out;
        } catch (IllegalStateException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new IllegalStateException("operator ingress queue state is unreadable", ex);
        }
    }

    private Item readInflight() {
        String raw = prefs.getString(KEY_INFLIGHT, "");
        if (raw == null || raw.trim().isEmpty()) return null;
        try {
            Item item = Item.fromJson(new JSONObject(raw));
            if (item == null) {
                throw new IllegalStateException("operator ingress in-flight state is invalid");
            }
            return item;
        } catch (IllegalStateException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new IllegalStateException("operator ingress in-flight state is unreadable", ex);
        }
    }

    private static void requireCommit(boolean committed, String operation) {
        if (!committed) {
            throw new IllegalStateException("operator ingress persistence failed during " + operation);
        }
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
