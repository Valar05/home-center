package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import org.junit.Test;

public class HeartbeatPersistedShaMetadataCanonicalityTest {
    @Test
    public void whitespacePoisonedShaIsAChangedProjectionInput() {
        String payloadB64 = "eyJmb28iOiJiYXIifQ==";
        String canonicalSha = "a".repeat(64);
        HeartbeatPersistedPollPolicy.Snapshot previous =
                new HeartbeatPersistedPollPolicy.Snapshot(
                        payloadB64,
                        13L,
                        canonicalSha,
                        1000L);
        HeartbeatPersistedPollPolicy.Snapshot poisoned =
                new HeartbeatPersistedPollPolicy.Snapshot(
                        payloadB64,
                        13L,
                        " " + canonicalSha + " ",
                        1001L);

        assertFalse(previous.sameProjectionInputs(poisoned));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(previous, poisoned, false));
    }

    @Test
    public void whitespacePoisonedShaRejectsBeforeSemanticParser() {
        String payload = canonicalEnvelope("pulse-sha-whitespace", "true");
        String canonicalSha = sha256(payload);

        HeartbeatPersistedEnvelopeProjection.Result leading =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        " " + canonicalSha,
                        2000L,
                        null);
        HeartbeatPersistedEnvelopeProjection.Result trailing =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        canonicalSha + " ",
                        2000L,
                        null);

        assertFalse(leading.storageAccepted);
        assertFalse(leading.semanticAttempted);
        assertEquals(
                "Stored heartbeat SHA-256 metadata is not canonical lowercase hex.",
                leading.boundary);
        assertFalse(trailing.storageAccepted);
        assertFalse(trailing.semanticAttempted);
        assertEquals(leading.boundary, trailing.boundary);
    }

    @Test
    public void whitespacePoisonedShaPreservesLastGoodContactAndClampsMotion() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-last-good-before-sha-poison");
        String payload = canonicalEnvelope("pulse-would-have-replaced", "true");

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload) + "\n",
                        3000L,
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertTrue(result.frame.refreshInterrupted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(lastGood, result.frame));
        assertFalse(result.frame.transitionMotionAllowed);
        assertFalse(result.frame.nodes.get(0).transitionMotion);
    }

    private static HeartbeatSceneGraph.Frame goodFrame(String pulseId) {
        HeartbeatEnvelopeParser.Result parsed = HeartbeatEnvelopeParser.parse(
                canonicalEnvelope(pulseId, "true"));
        return HeartbeatSceneGraph.build(parsed, null);
    }

    private static String canonicalEnvelope(String pulseId, String complete) {
        return "{\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"" + pulseId + "\","
                + "\"complete\":" + complete + ","
                + "\"lights\":[{"
                + "\"id\":\"execution-truth\","
                + "\"label\":\"Execution Truth\","
                + "\"provenanceKind\":\"repository_skill\","
                + "\"provenanceLocator\":\"skills/execution-truth/SKILL.md\","
                + "\"activationReason\":\"Persisted integrity metadata must be exact before semantic trust.\","
                + "\"state\":\"active\","
                + "\"changedThisPulse\":true,"
                + "\"consequence\":\"Non-canonical integrity metadata cannot be normalized into accepted evidence.\","
                + "\"evidenceBoundary\":\"Pure source regression fixture.\""
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
