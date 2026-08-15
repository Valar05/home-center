package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import org.junit.Test;

/**
 * Regression source for persisted observation metadata. The current updatedMs
 * value comes from System.currentTimeMillis(), so positive presence is testable;
 * monotonic ordering is not part of the contract.
 */
public class HeartbeatPersistedEnvelopeFreshnessTest {
    @Test
    public void projectionUsesCanonicalIngressByteCeiling() {
        assertEquals(
                OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES,
                HeartbeatPersistedEnvelopeProjection.MAX_PAYLOAD_BYTES);
    }

    @Test
    public void anyPositiveWallClockTimestampMayReachSemanticProjection() {
        String payload = canonicalEnvelope("pulse-clock-witness");

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        1L,
                        null);

        assertTrue(result.storageAccepted);
        assertTrue(result.semanticAttempted);
        assertTrue(result.parserAccepted);
        assertTrue(result.presentationAccepted);
        assertEquals(1L, result.updatedMs);
        assertEquals("pulse-clock-witness", result.frame.visiblePulseId);
    }

    @Test
    public void wallClockMagnitudeDoesNotChangeContentIdentity() {
        String payload = canonicalEnvelope("pulse-same-content");

        HeartbeatPersistedEnvelopeProjection.Result early =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        2L,
                        null);
        HeartbeatPersistedEnvelopeProjection.Result later =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        Long.MAX_VALUE,
                        null);

        assertTrue(early.storageAccepted);
        assertTrue(later.storageAccepted);
        assertEquals(early.observedBytes, later.observedBytes);
        assertEquals(early.observedSha256, later.observedSha256);
        assertEquals(
                HeartbeatFrameCheckpoint.contactSha256(early.frame),
                HeartbeatFrameCheckpoint.contactSha256(later.frame));
    }

    private static String canonicalEnvelope(String pulseId) {
        return "{\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"" + pulseId + "\","
                + "\"complete\":true,"
                + "\"lights\":[{"
                + "\"id\":\"execution-truth\","
                + "\"label\":\"Execution Truth\","
                + "\"provenanceKind\":\"repository_skill\","
                + "\"provenanceLocator\":\"skills/execution-truth/SKILL.md\","
                + "\"activationReason\":\"Persisted content identity and wall-clock observation metadata must remain distinct.\","
                + "\"state\":\"active\","
                + "\"changedThisPulse\":true,"
                + "\"consequence\":\"Byte count and SHA define content identity; positive updatedMs records observation time only.\","
                + "\"evidenceBoundary\":\"Pure source wall-clock fixture.\""
                + "}]}";
    }

    private static int utf8Bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8).length;
    }

    private static String sha256(String value) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder(hash.length * 2);
            for (byte b : hash) out.append(String.format(Locale.ROOT, "%02x", b & 0xff));
            return out.toString();
        } catch (Exception impossible) {
            throw new AssertionError(impossible);
        }
    }
}