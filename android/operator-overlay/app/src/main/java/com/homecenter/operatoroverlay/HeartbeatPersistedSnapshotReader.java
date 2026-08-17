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
 * <p>This class owns no poll loop, writer, cache, renderer, transport, phone surface,
 * queue, recovery coordinator, deployment, or P0 action. The existing
 * {@code OperatorOverlayService} remains the sole poll owner.</p>
 */
final class HeartbeatPersistedSnapshotReader {
    private HeartbeatPersistedSnapshotReader() {
    }

    static HeartbeatPersistedPollPolicy.Snapshot read(Context context) {
        Map<String, ?> values = context == null
                ? Collections.emptyMap()
                : OperatorState.prefs(context).getAll();
        return fromValues(values);
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
        Object value = values.get(key);
        return value instanceof String ? (String) value : "";
    }

    private static long longValue(Map<String, ?> values, String key) {
        Object value = values.get(key);
        return value instanceof Number ? ((Number) value).longValue() : 0L;
    }
}
