package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/** Source-only regression for finite persisted-poll dedup work. */
public final class HeartbeatPersistedPollSourceResourceThroatTest {
    @Test
    public void exactPayloadBase64CeilingRemainsEligibleForDedup() {
        String payload = repeat('A', HeartbeatPersistedPollPolicy.MAX_PAYLOAD_B64_CHARS);
        HeartbeatPersistedPollPolicy.Snapshot first = snapshot(payload, 1L, repeat('a', 64));
        HeartbeatPersistedPollPolicy.Snapshot same = snapshot(payload, 1L, repeat('a', 64));

        assertTrue(first.sourceWithinResourceBounds());
        assertTrue(first.sameProjectionInputs(same));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.SKIP_UNCHANGED,
                HeartbeatPersistedPollPolicy.decide(first, same, true));
    }

    @Test
    public void payloadBase64MaxPlusOneNeverBecomesDedupAuthority() {
        String payload = repeat('A', HeartbeatPersistedPollPolicy.MAX_PAYLOAD_B64_CHARS + 1);
        HeartbeatPersistedPollPolicy.Snapshot first = snapshot(payload, 1L, repeat('a', 64));
        HeartbeatPersistedPollPolicy.Snapshot same = snapshot(payload, 1L, repeat('a', 64));

        assertFalse(first.sourceWithinResourceBounds());
        assertFalse(first.sameProjectionInputs(same));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(first, same, true));
    }

    @Test
    public void shaMetadataMaxPlusOneNeverBecomesDedupAuthority() {
        String oversizedSha = repeat('a', HeartbeatPersistedPollPolicy.MAX_SHA_METADATA_CHARS + 1);
        HeartbeatPersistedPollPolicy.Snapshot first = snapshot("payload", 7L, oversizedSha);
        HeartbeatPersistedPollPolicy.Snapshot same = snapshot("payload", 7L, oversizedSha);

        assertFalse(first.sourceWithinResourceBounds());
        assertFalse(first.sameProjectionInputs(same));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(first, same, true));
    }

    @Test
    public void oversizedPreviousSnapshotCannotCauseCurrentSnapshotToSkip() {
        HeartbeatPersistedPollPolicy.Snapshot previous = snapshot(
                repeat('A', HeartbeatPersistedPollPolicy.MAX_PAYLOAD_B64_CHARS + 1),
                1L,
                repeat('a', 64));
        HeartbeatPersistedPollPolicy.Snapshot current = snapshot(
                "payload",
                7L,
                repeat('b', 64));

        assertTrue(current.sourceWithinResourceBounds());
        assertFalse(current.sameProjectionInputs(previous));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(previous, current, true));
    }

    private static HeartbeatPersistedPollPolicy.Snapshot snapshot(
            String payloadB64,
            long declaredBytes,
            String sha256) {
        return new HeartbeatPersistedPollPolicy.Snapshot(
                payloadB64,
                declaredBytes,
                sha256,
                1L);
    }

    private static String repeat(char value, int count) {
        StringBuilder out = new StringBuilder(count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
