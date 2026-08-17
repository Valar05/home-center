package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/** Regression source for the existing owner's non-canonical persisted Base64 boundary. */
public final class HeartbeatPersistedBase64OwnerBoundaryTest {
    @Test
    public void nonCanonicalDeclarationPreservesLastGoodContactAndClampsMotion() {
        HeartbeatSceneGraph.Frame lastGood = goodFrame("pulse-before-base64-alias");

        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                "Zg==\n",
                "Zg=="));

        HeartbeatSceneGraph.Frame preserved = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                lastGood,
                HeartbeatPersistedBase64Canonicality.NON_CANONICAL_BOUNDARY);
        HeartbeatOverlayRefreshPlan.Plan plan = HeartbeatOverlayRefreshPlan.fromFrame(
                preserved,
                "execution-truth");

        assertTrue(preserved.refreshInterrupted);
        assertEquals(
                HeartbeatPersistedBase64Canonicality.NON_CANONICAL_BOUNDARY,
                preserved.refreshBoundary);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, preserved));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(lastGood, preserved));
        assertFalse(preserved.transitionMotionAllowed);
        assertFalse(preserved.nodes.get(0).transitionMotion);
        assertEquals(lastGood.visiblePulseId, plan.frame.visiblePulseId);
    }

    @Test
    public void canonicalDeclarationDoesNotInventARejectionBoundary() {
        assertTrue(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                "Zg==",
                "Zg=="));
        assertFalse(HeartbeatPersistedBase64Canonicality.NON_CANONICAL_BOUNDARY.isEmpty());
    }

    private static HeartbeatSceneGraph.Frame goodFrame(String pulseId) {
        HeartbeatEnvelopeParser.Result parsed = HeartbeatEnvelopeParser.parse(
                "{\"schema\":\"heartbeat-skill-lights.v1\","
                        + "\"pulseId\":\"" + pulseId + "\","
                        + "\"complete\":true,"
                        + "\"lights\":[{"
                        + "\"id\":\"execution-truth\","
                        + "\"label\":\"Execution Truth\","
                        + "\"provenanceKind\":\"repository_skill\","
                        + "\"provenanceLocator\":\"skills/execution-truth/SKILL.md\","
                        + "\"activationReason\":\"Persisted declaration identity must be exact before semantic trust.\","
                        + "\"state\":\"active\","
                        + "\"changedThisPulse\":true,"
                        + "\"consequence\":\"Decoder-tolerated aliases cannot replace last-good contact.\","
                        + "\"evidenceBoundary\":\"Pure owner-boundary regression source.\""
                        + "}]}" );
        return HeartbeatSceneGraph.build(parsed, null);
    }
}
