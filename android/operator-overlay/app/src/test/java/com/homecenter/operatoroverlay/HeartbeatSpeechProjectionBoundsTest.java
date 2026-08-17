package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

public class HeartbeatSpeechProjectionBoundsTest {
    private static final String TRUNCATION_SUFFIX = "… (truncated)";

    private static HeartbeatSkillPolicy.Candidate typed(String id, String label) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                label,
                "doctrine",
                "Contact Preservation",
                "Preserve the visible heartbeat while a later refresh fails",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Last-good contact remains available",
                "Exact source fixture remains inspectable");
    }

    @Test
    public void focusedSpeechBoundsDirectSourceLabelWithoutMutatingCandidate() {
        String swan = "🦢";
        String longLabel = repeat(swan, 140);
        HeartbeatSkillPolicy.Candidate candidate = typed("swan-label", longLabel);

        String compact = HeartbeatSkillPolicy.contentDescription(candidate);
        String detail = HeartbeatSkillPolicy.detailContentDescription(candidate);
        int projectedSwanBudget = HeartbeatSkillPolicy.MAX_SPOKEN_LABEL_CODE_POINTS
                - TRUNCATION_SUFFIX.codePointCount(0, TRUNCATION_SUFFIX.length());

        assertEquals(longLabel, candidate.label);
        assertTrue(compact.contains(repeat(swan, 96) + "…"));
        assertFalse(compact.contains(repeat(swan, 97)));
        assertTrue(detail.contains(repeat(swan, projectedSwanBudget) + TRUNCATION_SUFFIX));
        assertFalse(detail.contains(repeat(swan, projectedSwanBudget + 1)));
    }

    @Test
    public void interruptedSpeechBoundsPulseAndBoundaryWithoutMutatingFrameEvidence() {
        String swan = "🦢";
        String longPulseId = "pulse-" + repeat(swan, 140);
        String longBoundary = "boundary-" + repeat("x", 420);
        HeartbeatSceneGraph.Frame complete = HeartbeatSceneGraph.build(
                longPulseId,
                Collections.singletonList(typed("contact", "Contact Preservation")),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt-next",
                complete,
                longBoundary);

        String speech = HeartbeatFrameAccessibility.collapsedContentDescription(interrupted);

        assertEquals(longPulseId, interrupted.visiblePulseId);
        assertEquals(longBoundary, interrupted.refreshBoundary);
        assertTrue(speech.contains("Showing last complete heartbeat pulse-"));
        assertTrue(speech.contains("… (truncated)"));
        assertFalse(speech.contains(repeat(swan, 97)));
        assertFalse(speech.contains(repeat("x", 321)));
        assertTrue(speech.length() < 1200);
    }

    @Test
    public void unsafePreParserBoundaryRemainsExactButIsNotSpoken() {
        String poisonedBoundary = "storage wound \u202Ehidden";
        HeartbeatSceneGraph.Frame complete = HeartbeatSceneGraph.build(
                "pulse-safe",
                Collections.singletonList(typed("contact", "Contact Preservation")),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt-next",
                complete,
                poisonedBoundary);

        String speech = HeartbeatFrameAccessibility.collapsedContentDescription(interrupted);

        assertEquals(poisonedBoundary, interrupted.refreshBoundary);
        assertTrue(speech.contains("Heartbeat refresh boundary contains unsafe semantic text."));
        assertFalse(speech.contains("\u202E"));
        assertFalse(speech.contains("hidden"));
    }

    @Test
    public void edgeControlBoundaryIsPreservedBeforeSpeechSafetyRuns() {
        String poisonedBoundary = "\tstorage wound";
        HeartbeatSceneGraph.Frame complete = HeartbeatSceneGraph.build(
                "pulse-safe",
                Collections.singletonList(typed("contact", "Contact Preservation")),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt-next",
                complete,
                poisonedBoundary);

        String speech = HeartbeatFrameAccessibility.collapsedContentDescription(interrupted);

        assertEquals(poisonedBoundary, interrupted.refreshBoundary);
        assertTrue(speech.contains("Heartbeat refresh boundary contains unsafe semantic text."));
        assertFalse(speech.contains("storage wound"));
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
