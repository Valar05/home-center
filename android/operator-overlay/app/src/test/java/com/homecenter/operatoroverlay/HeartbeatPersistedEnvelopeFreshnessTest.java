package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import org.junit.Test;

public class HeartbeatPersistedEnvelopeFreshnessTest {
    @Test
    public void projectionUsesCanonicalIngressByteCeiling() {
        assertEquals(
                OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES,
                HeartbeatPersistedEnvelopeProjection.MAX_PAYLOAD_BYTES);
    }

    @Test
    public void olderPersistedUpdateRejectsBeforeSemanticParsingAndPreservesContact() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-last-good");
        String payload = canonicalEnvelope("pulse-older", "Older payload remains inert.");

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        7000L,
                        8000L,
                        sha256(canonicalEnvelope("pulse-last-good", "Last-good contact.")),
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertFalse(result.presentationAccepted);
        assertTrue(result.frame.refreshInterrupted);
        assertFalse(result.frame.transitionMotionAllowed);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertEquals(
                "Stored heartbeat update identity rolled back: observed 7000 last accepted 8000.",
                result.boundary);
    }

    @Test
    public void equalUpdateIdentityWithDifferentShaRejectsAsCollision() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-collision-base");
        String prior = canonicalEnvelope("pulse-collision-base", "Prior contact.");
        String conflicting = canonicalEnvelope("pulse-collision-new", "Conflicting contact.");

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        conflicting,
                        utf8Bytes(conflicting),
                        sha256(conflicting),
                        9000L,
                        9000L,
                        sha256(prior),
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertTrue(result.frame.refreshInterrupted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertEquals(
                "Stored heartbeat update identity collision: equal update identity carries different payload SHA-256.",
                result.boundary);
    }

    @Test
    public void equalUpdateIdentityWithSameShaIsIdempotentAndMayReachSemanticScene() {
        String payload = canonicalEnvelope("pulse-exact-retry", "Exact retry contact.");
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                HeartbeatEnvelopeParser.parse(payload),
                null);

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        10000L,
                        10000L,
                        sha256(payload),
                        lastGood);

        assertTrue(result.storageAccepted);
        assertTrue(result.semanticAttempted);
        assertTrue(result.parserAccepted);
        assertTrue(result.presentationAccepted);
        assertFalse(result.frame.transitionMotionAllowed);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
    }

    @Test
    public void priorUpdateIdentityRequiresCanonicalShaBeforeSemanticParsing() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-prior-hash");
        String payload = canonicalEnvelope("pulse-next", "Next contact.");

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        12000L,
                        11000L,
                        "NOT-A-CANONICAL-HASH",
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertEquals(
                "Last-accepted heartbeat SHA-256 identity is not canonical lowercase hex.",
                result.boundary);
    }

    private static HeartbeatSceneGraph.Frame goodFrame(String pulseId) {
        return HeartbeatSceneGraph.build(
                HeartbeatEnvelopeParser.parse(canonicalEnvelope(pulseId, "Last-good contact.")),
                null);
    }

    private static String canonicalEnvelope(String pulseId, String consequence) {
        return "{\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"" + pulseId + "\","
                + "\"complete\":true,"
                + "\"lights\":[{"
                + "\"id\":\"execution-truth\","
                + "\"label\":\"Execution Truth\","
                + "\"provenanceKind\":\"repository_skill\","
                + "\"provenanceLocator\":\"skills/execution-truth/SKILL.md\","
                + "\"activationReason\":\"Persisted identity must remain monotonic and collision-safe.\","
                + "\"state\":\"active\","
                + "\"changedThisPulse\":true,"
                + "\"consequence\":\"" + consequence + "\","
                + "\"evidenceBoundary\":\"Pure source freshness fixture.\""
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