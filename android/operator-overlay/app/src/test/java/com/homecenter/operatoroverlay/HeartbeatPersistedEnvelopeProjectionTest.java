package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import org.junit.Test;

public class HeartbeatPersistedEnvelopeProjectionTest {
    @Test
    public void exactStoredIdentityProjectsThroughParserAndScene() {
        String payload = canonicalEnvelope("pulse-storage-good", "true");

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        1234L,
                        null);

        assertTrue(result.storageAccepted);
        assertTrue(result.semanticAttempted);
        assertTrue(result.parserAccepted);
        assertTrue(result.presentationAccepted);
        assertEquals("pulse-storage-good", result.frame.visiblePulseId);
        assertFalse(result.frame.refreshInterrupted);
        assertEquals(utf8Bytes(payload), result.observedBytes);
        assertEquals(sha256(payload), result.observedSha256);
    }

    @Test
    public void exactStoredBytesProjectThroughStrictUtf8Path() {
        String payload = canonicalEnvelope("pulse-storage-bytes", "true")
                .replace("Execution Truth", "Execution Truth 🦢");
        byte[] bytes = payload.getBytes(StandardCharsets.UTF_8);

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.projectBytes(
                        bytes,
                        bytes.length,
                        sha256(bytes),
                        1500L,
                        null);

        assertTrue(result.storageAccepted);
        assertTrue(result.semanticAttempted);
        assertTrue(result.parserAccepted);
        assertTrue(result.presentationAccepted);
        assertEquals("Execution Truth 🦢", result.frame.nodes.get(0).label);
        assertEquals(bytes.length, result.observedBytes);
        assertEquals(sha256(bytes), result.observedSha256);
    }

    @Test
    public void validByteFirstAndStringPathsProduceSameVisibleContact() {
        String payload = canonicalEnvelope("pulse-equivalent", "true");
        byte[] bytes = payload.getBytes(StandardCharsets.UTF_8);

        HeartbeatPersistedEnvelopeProjection.Result fromString =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        bytes.length,
                        sha256(bytes),
                        1600L,
                        null);
        HeartbeatPersistedEnvelopeProjection.Result fromBytes =
                HeartbeatPersistedEnvelopeProjection.projectBytes(
                        bytes,
                        bytes.length,
                        sha256(bytes),
                        1600L,
                        null);

        assertTrue(fromString.presentationAccepted);
        assertTrue(fromBytes.presentationAccepted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(
                fromString.frame,
                fromBytes.frame));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(
                fromString.frame,
                fromBytes.frame));
    }

    @Test
    public void malformedUtf8RejectsBeforeParserPreservesContactAndClampsMotion() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-before-invalid-utf8");
        assertTrue(lastGood.transitionMotionAllowed);
        assertTrue(lastGood.nodes.get(0).transitionMotion);
        byte[] malformed = new byte[] {(byte) 0xC3, (byte) 0x28};

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.projectBytes(
                        malformed,
                        malformed.length,
                        sha256(malformed),
                        1700L,
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertFalse(result.parserAccepted);
        assertFalse(result.presentationAccepted);
        assertEquals("Stored heartbeat payload is not valid UTF-8.", result.boundary);
        assertEquals(result.boundary, result.frame.refreshBoundary);
        assertTrue(result.frame.refreshInterrupted);
        assertFalse(result.frame.transitionMotionAllowed);
        assertFalse(result.frame.nodes.get(0).transitionMotion);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(lastGood, result.frame));
    }

    @Test
    public void byteCountMismatchWinsBeforeMalformedUtf8Decode() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-before-byte-mismatch");
        byte[] malformed = new byte[] {(byte) 0xC3, (byte) 0x28};

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.projectBytes(
                        malformed,
                        malformed.length + 1L,
                        sha256(malformed),
                        1800L,
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertTrue(result.boundary.startsWith("Stored heartbeat byte-count mismatch:"));
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
    }

    @Test
    public void byteCountMismatchRejectsBeforeParserPreservesContactAndClampsMotion() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-last-good");
        assertTrue(lastGood.transitionMotionAllowed);
        assertTrue(lastGood.nodes.get(0).transitionMotion);
        String poisonedSemanticPayload = "not-json";

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        poisonedSemanticPayload,
                        utf8Bytes(poisonedSemanticPayload) + 1L,
                        sha256(poisonedSemanticPayload),
                        2000L,
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertFalse(result.parserAccepted);
        assertFalse(result.presentationAccepted);
        assertNotSame(lastGood, result.frame);
        assertTrue(result.frame.refreshInterrupted);
        assertFalse(result.frame.transitionMotionAllowed);
        assertFalse(result.frame.nodes.get(0).transitionMotion);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertTrue(result.boundary.startsWith("Stored heartbeat byte-count mismatch:"));
        assertEquals(result.boundary, result.frame.refreshBoundary);
    }

    @Test
    public void shaMismatchRejectsBeforeParserAndPreservesContact() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-sha-last-good");
        String payload = canonicalEnvelope("pulse-would-parse", "true");
        String wrongHash = "0".repeat(64);
        if (wrongHash.equals(sha256(payload))) wrongHash = "1".repeat(64);

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        wrongHash,
                        3000L,
                        lastGood);

        assertFalse(result.storageAccepted);
        assertFalse(result.semanticAttempted);
        assertTrue(result.frame.refreshInterrupted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertFalse(result.frame.transitionMotionAllowed);
        assertEquals(
                "Stored heartbeat SHA-256 mismatch: declared identity does not match decoded UTF-8 payload.",
                result.boundary);
        assertEquals(result.boundary, result.frame.refreshBoundary);
    }

    @Test
    public void malformedHashMetadataAndMissingUpdateIdentityFailClosed() {
        String payload = canonicalEnvelope("pulse-metadata", "true");
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-before-metadata");

        HeartbeatPersistedEnvelopeProjection.Result uppercaseHash =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload).toUpperCase(Locale.ROOT),
                        4000L,
                        lastGood);
        HeartbeatPersistedEnvelopeProjection.Result missingUpdated =
                HeartbeatPersistedEnvelopeProjection.project(
                        payload,
                        utf8Bytes(payload),
                        sha256(payload),
                        0L,
                        lastGood);

        assertFalse(uppercaseHash.storageAccepted);
        assertFalse(uppercaseHash.semanticAttempted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, uppercaseHash.frame));
        assertEquals(
                "Stored heartbeat SHA-256 metadata is not canonical lowercase hex.",
                uppercaseHash.boundary);
        assertFalse(missingUpdated.storageAccepted);
        assertFalse(missingUpdated.semanticAttempted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, missingUpdated.frame));
        assertEquals("Stored heartbeat update identity is missing.", missingUpdated.boundary);
    }

    @Test
    public void storageValidSemanticRejectUsesExistingSceneFailClosedSemantics() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-semantic-last-good");
        String invalidJson = "{\"schema\":\"heartbeat-skill-lights.v1\"";

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        invalidJson,
                        utf8Bytes(invalidJson),
                        sha256(invalidJson),
                        5000L,
                        lastGood);

        assertTrue(result.storageAccepted);
        assertTrue(result.semanticAttempted);
        assertFalse(result.parserAccepted);
        assertFalse(result.presentationAccepted);
        assertTrue(result.frame.refreshInterrupted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
        assertEquals(result.frame.refreshBoundary, result.boundary);
    }

    @Test
    public void storageValidIncompletePulseIsParserAcceptedButNotPresentationAccepted() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-incomplete-last-good");
        String incomplete = canonicalEnvelope("pulse-incomplete", "false");

        HeartbeatPersistedEnvelopeProjection.Result result =
                HeartbeatPersistedEnvelopeProjection.project(
                        incomplete,
                        utf8Bytes(incomplete),
                        sha256(incomplete),
                        6000L,
                        lastGood);

        assertTrue(result.storageAccepted);
        assertTrue(result.semanticAttempted);
        assertTrue(result.parserAccepted);
        assertFalse(result.presentationAccepted);
        assertTrue(result.frame.refreshInterrupted);
        assertEquals("Pulse is incomplete.", result.boundary);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, result.frame));
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
                + "\"activationReason\":\"Persisted identity must be checked before semantic trust.\","
                + "\"state\":\"active\","
                + "\"changedThisPulse\":true,"
                + "\"consequence\":\"Storage identity and semantic presentation remain separate capability states.\","
                + "\"evidenceBoundary\":\"Pure source projection fixture.\""
                + "}]}";
    }

    private static int utf8Bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8).length;
    }

    private static String sha256(String value) {
        return sha256(value.getBytes(StandardCharsets.UTF_8));
    }

    private static String sha256(byte[] value) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(value);
            StringBuilder out = new StringBuilder(hash.length * 2);
            for (byte b : hash) out.append(String.format(Locale.ROOT, "%02x", b & 0xff));
            return out.toString();
        } catch (Exception impossible) {
            throw new AssertionError(impossible);
        }
    }
}
