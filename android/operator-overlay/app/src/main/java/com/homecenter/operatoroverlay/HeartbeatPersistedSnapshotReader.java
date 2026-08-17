package com.homecenter.operatoroverlay;

import android.content.Context;
import java.util.Collections;
import java.util.Map;

/**
 * One-read projection of the existing OperatorState SharedPreferences map into the
 * persisted heartbeat poll policy.
 *
 * <p>The heartbeat writer commits payload, byte count, SHA, and update metadata in
 * one editor transaction. Reading those keys through four independent preference
 * getter calls can nevertheless observe two committed maps if a writer lands
 * between calls. That transient mixture would look like a false integrity wound.
 * This helper takes one {@code getAll()} map snapshot, then extracts all four fields
 * from that same observation.</p>
 *
 * <p>Missing keys retain the existing canonical defaults. A present key with an
 * unexpected stored type is not rewritten into "missing": it throws so owner
 * wiring can preserve an explicit storage-read wound and retry rather than silently
 * laundering corrupted persistence into WAITING or CONTACT LOST.</p>
 *
 * <p>This class owns no poll loop, writer, cache, renderer, transport, phone surface,
 * queue, recovery coordinator, deployment, or P0 action. The existing
 * {@code OperatorOverlayService} remains the sole poll owner.</p>
 */
final class HeartbeatPersistedSnapshotReader {
    static final String STORAGE_READ_FAILURE_BOUNDARY =
            "Stored heartbeat snapshot could not be read coherently; last-good contact is preserved and the poll will retry.";

    private HeartbeatPersistedSnapshotReader() {
    }

    static HeartbeatPersistedPollPolicy.Snapshot read(Context context) {
        if (context == null) {
            throw new IllegalArgumentException("heartbeat persisted snapshot context is required");
        }
        return fromValues(OperatorState.prefs(context).getAll());
    }

    static HeartbeatPersistedPollPolicy.Snapshot fromValues(Map<String, ?> values) {
        Map<String, ?> exact = values == null ? Collections.emptyMap() : values;
        return new HeartbeatPersistedPollPolicy.Snapshot(
                stringValue(exact, OperatorState.KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64),
                longValue(exact, OperatorState.KEY_HEARTBEAT_LIGHTS_BYTES),
                stringValue(exact, OperatorState.KEY_HEARTBEAT_LIGHTS_SHA256),
                longValue(exact, OperatorState.KEY_HEARTBEAT_LIGHTS_UPDATED_MS));
    }

    private static String stringValue(Map<String, ?> values, String key) {
        if (!values.containsKey(key)) return "";
        Object value = values.get(key);
        if (value instanceof String) return (String) value;
        throw unexpectedType(key, value);
    }

    private static long longValue(Map<String, ?> values, String key) {
        if (!values.containsKey(key)) return 0L;
        Object value = values.get(key);
        if (value instanceof Number) return ((Number) value).longValue();
        throw unexpectedType(key, value);
    }

    private static IllegalStateException unexpectedType(String key, Object value) {
        String type = value == null ? "null" : value.getClass().getSimpleName();
        return new IllegalStateException(
                "heartbeat persisted field has unexpected type: " + key + " (" + type + ")");
    }
}
