package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/** Source-only regression fixtures for root pulse-identity bound parity. */
public class HeartbeatPulseIdentityBoundParityTest {
    @Test
    public void directSceneAcceptsCanonicalMaxPulseIdentity() {
        String pulseId = repeat("p", HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS);

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                pulseId,
                Collections.singletonList(candidate()),
                true,
                null);

        assertFalse(frame.refreshInterrupted);
        assertEquals(pulseId, frame.visiblePulseId);
        assertEquals(pulseId, frame.attemptedPulseId);
    }

    @Test
    public void directSceneRejectsMaxPlusOneLikeCanonicalParserAndPreservesContact() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(candidate()),
                true,
                null);
        String oversized = repeat("p", HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS + 1);

        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                oversized,
                Collections.singletonList(candidate()),
                true,
                lastGood);

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("", rejected.attemptedPulseId);
        assertEquals(
                "Pulse identity exceeds "
                        + HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS
                        + " characters.",
                rejected.refreshBoundary);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, rejected));
        assertFalse(rejected.transitionMotionAllowed);
        assertFalse(rejected.nodes.get(0).transitionMotion);

        HeartbeatEnvelopeParser.Result canonical = HeartbeatEnvelopeParser.parse(
                envelope(oversized));
        assertFalse(canonical.accepted());
        assertTrue(canonical.boundary.contains(
                "pulseId exceeds " + HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS));
    }

    @Test
    public void preParserOversizedAttemptedIdentityIsNotRetainedAsDiagnosticState() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(candidate()),
                true,
                null);
        String oversized = repeat("x", HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS + 1);

        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.preserveRejectedRefresh(
                oversized,
                lastGood,
                "Persisted heartbeat byte identity mismatch.");

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("", rejected.attemptedPulseId);
        assertEquals(
                "Persisted heartbeat byte identity mismatch.",
                rejected.refreshBoundary);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, rejected));
        assertFalse(rejected.transitionMotionAllowed);
        assertFalse(rejected.nodes.get(0).transitionMotion);
    }

    private static HeartbeatSkillPolicy.Candidate candidate() {
        return new HeartbeatSkillPolicy.Candidate(
                "contact-preservation",
                "Contact Preservation",
                "doctrine",
                "last-good contact",
                "Root pulse identity bounds must not erase last-good contact.",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Oversized direct pulse identities fail closed.",
                "Pulse identity bound parity regression fixture");
    }

    private static String envelope(String pulseId) {
        return "{"
                + "\"schema\":\"heartbeat-skill-lights.v1\"," 
                + "\"pulseId\":\"" + pulseId + "\"," 
                + "\"complete\":true,"
                + "\"lights\":[]"
                + "}";
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder(value.length() * count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
