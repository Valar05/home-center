package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/** RED source regression for the direct String compatibility adapter's pre-encode resource throat. */
public final class HeartbeatPersistedStringPreencodeResourceThroatTest {
    @Test
    public void sourceMaxPlusOneFailsBeforeUtf8Encoding() {
        String oversized = repeat('a', OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES + 1);

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        oversized,
                        0L,
                        "",
                        1L,
                        null);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertTrue(result.boundary.contains("pre-encode resource ceiling"));
        assertTrue(result.observedBytes == 0);
    }

    @Test
    public void exactAsciiSourceCeilingReachesExistingByteIntegrityPath() {
        String exact = repeat('a', OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES);

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        exact,
                        0L,
                        "",
                        1L,
                        null);

        assertFalse(result.storageAccepted);
        assertFalse(result.boundary.contains("pre-encode resource ceiling"));
        assertTrue(result.observedBytes == OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES);
    }

    @Test
    public void exactCodeUnitMultibyteTextStillHitsCanonicalByteCeilingAfterEncode() {
        String exactCodeUnits = repeat('\u00e9', OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES);

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        exactCodeUnits,
                        0L,
                        "",
                        1L,
                        null);

        assertFalse(result.storageAccepted);
        assertFalse(result.boundary.contains("pre-encode resource ceiling"));
        assertTrue(result.boundary.contains("payload exceeds"));
        assertTrue(result.observedBytes > OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES);
    }

    private static String repeat(char value, int count) {
        StringBuilder out = new StringBuilder(count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
