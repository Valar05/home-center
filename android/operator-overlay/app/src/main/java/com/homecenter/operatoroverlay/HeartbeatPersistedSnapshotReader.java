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
 * <p>The encoded payload declaration is bounded before the existing owner attempts
 * Base64 decode. The canonical writer cannot emit more than four characters per
 * three payload bytes, rounded up to a padded quartet. Accepting an arbitrarily
 * larger stored declaration would let corrupt persistence consume decode/allocation
 * work before the decoded-byte ceiling can reject it on the fast poll path. This
 * pre-decode ceiling is a resource bound only; exact Base64 canonicality remains a
 * separate later evidence gate.</p>
 *
 * <p>This class owns no poll loop, writer, cache, renderer, transport, phone surface,
 * queue, recovery coordinator, deployment, or P0 action. The existing
 * {@code OperatorOverlayService} remains the sole poll owner.</p>
 */
final class HeartbeatPersistedSnapshotReader {
    static final String STORAGE_READ_FAILURE_BOUNDARY =
            "Stored heartbeat snapshot could not be read coherently; last-good contact is preserved and the poll will retry.";
    static final int MAX_PAYLOAD_BASE64_CHARS =
            4 * ((OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES + 2) / 3);

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
                boundedPayloadBase64(exact),
                integralLongValue(exact, OperatorState.KEY_HEARTBEAT_LIGHTS_BYTES),
                stringValue(exact, OperatorState.KEY_HEARTBEAT_LIGHTS_SHA256),
                integralLongValue(exact, OperatorState.KEY_HEARTBEAT_LIGHTS_UPDATED_MS));
    }

    private static String boundedPayloadBase64(Map<String, ?> values) {
        String value = stringValue(values, OperatorState.KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64);
        if (value.length() > MAX_PAYLOAD_BASE64_CHARS) {
            throw new IllegalStateException(
                    "heartbeat persisted Base64 declaration exceeds canonical maximum: "
                            + value.length() + " > " + MAX_PAYLOAD_BASE64_CHARS);
        }
        return value;
    }

    private static String stringValue(Map<String, ?> values, String key) {
        if (!values.containsKey(key)) return "";
        Object value = values.get(key);
        if (value instanceof String) return (String) value;
        throw unexpectedType(key, value);
    }

    /**
     * SharedPreferences stores integers and longs as distinct integral types. Accept
     * those two legacy/canonical shapes, but reject floating-point Number values.
     * Calling Number.longValue() on a Float would silently truncate corrupt stored
     * metadata and turn type drift into counterfeit byte-count/timestamp evidence.
     */
    private static long integralLongValue(Map<String, ?> values, String key) {
        if (!values.containsKey(key)) return 0L;
        Object value = values.get(key);
        if (value instanceof Long) return (Long) value;
        if (value instanceof Integer) return ((Integer) value).longValue();
        throw unexpectedType(key, value);
    }

    private static IllegalStateException unexpectedType(String key, Object value) {
        String type = value == null ? "null" : value.getClass().getSimpleName();
        return new IllegalStateException(
                "heartbeat persisted field has unexpected type: " + key + " (" + type + ")");
    }
}
