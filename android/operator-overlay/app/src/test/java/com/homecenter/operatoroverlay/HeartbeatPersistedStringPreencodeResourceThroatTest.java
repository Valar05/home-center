package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/** Source regression for the direct String compatibility adapter's pre-encode resource throat. */
public final class HeartbeatPersistedStringPreencodeResourceThroatTest {
    @Test
    public void publicSourceCeilingTracksCanonicalPayloadByteCeiling() {
        assertEquals(
                OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES,
                HeartbeatPersistedEnvelopeProjection.MAX_DIRECT_STRING_SOURCE_CODE_UNITS);
    }

    @Test
    public void sourceMaxPlusOneFailsBeforeUtf8Encoding() {
        String oversized = repeat(
                'a',
                HeartbeatPersistedEnvelopeProjection.MAX_DIRECT_STRING_SOURCE_CODE_UNITS + 1);

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
        assertEquals(0, result.observedBytes);
    }

    @Test
    public void exactAsciiSourceCeilingReachesExistingByteIntegrityPath() {
        String exact = repeat(
                'a',
                HeartbeatPersistedEnvelopeProjection.MAX_DIRECT_STRING_SOURCE_CODE_UNITS);

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        exact,
                        0L,
                        "",
                        1L,
                        null);

        assertFalse(result.storageAccepted);
        assertFalse(result.boundary.contains("pre-encode resource ceiling"));
        assertEquals(OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES, result.observedBytes);
    }

    @Test
    public void exactCodeUnitMultibyteTextStillHitsCanonicalByteCeilingAfterEncode() {
        String exactCodeUnits = repeat(
                '\u00e9',
                HeartbeatPersistedEnvelopeProjection.MAX_DIRECT_STRING_SOURCE_CODE_UNITS);

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
