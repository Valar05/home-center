package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.HashMap;
import java.util.Map;
import org.junit.Test;

public final class HeartbeatPersistedSnapshotReaderTest {
    @Test
    public void extractsHeartbeatFieldsFromOneMap() {
        Map<String, Object> values = new HashMap<>();
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64, "payload-a");
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_BYTES, 9L);
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_SHA256, "  sha-a  ");
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_UPDATED_MS, 101L);

        HeartbeatPersistedPollPolicy.Snapshot snapshot =
                HeartbeatPersistedSnapshotReader.fromValues(values);

        assertEquals("payload-a", snapshot.payloadB64);
        assertEquals(9L, snapshot.declaredBytes);
        assertEquals("sha-a", snapshot.declaredSha256);
        assertEquals(101L, snapshot.updatedMs);
    }

    @Test
    public void missingFieldsProduceCanonicalAbsentSnapshot() {
        HeartbeatPersistedPollPolicy.Snapshot snapshot =
                HeartbeatPersistedSnapshotReader.fromValues(new HashMap<>());

        assertTrue(snapshot.fullyAbsent());
    }

    @Test
    public void numericMapValuesConvertToLongs() {
        Map<String, Object> values = new HashMap<>();
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64, "payload-b");
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_BYTES, Integer.valueOf(11));
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_SHA256, "sha-b");
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_UPDATED_MS, Integer.valueOf(202));

        HeartbeatPersistedPollPolicy.Snapshot snapshot =
                HeartbeatPersistedSnapshotReader.fromValues(values);

        assertEquals(11L, snapshot.declaredBytes);
        assertEquals(202L, snapshot.updatedMs);
    }

    @Test
    public void presentFieldWithUnexpectedTypeIsNotRewrittenAsMissing() {
        Map<String, Object> values = new HashMap<>();
        values.put(OperatorState.KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64, Long.valueOf(7L));

        try {
            HeartbeatPersistedSnapshotReader.fromValues(values);
            fail("Expected persisted type drift to be rejected.");
        } catch (IllegalStateException expected) {
            assertTrue(expected.getMessage().contains(
                    OperatorState.KEY_HEARTBEAT_LIGHTS_PAYLOAD_B64));
        }
    }
}
