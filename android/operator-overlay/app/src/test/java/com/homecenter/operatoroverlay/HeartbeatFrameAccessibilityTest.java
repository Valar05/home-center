package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

public class HeartbeatFrameAccessibilityTest {
    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            String consequence,
            String evidence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                "Contact Preservation",
                "doctrine",
                "Contact Preservation",
                "Preserve last-good heartbeat through refresh failure",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                consequence,
                evidence);
    }

    @Test
    public void collapsedDescriptionComesFromVisibleSceneNodes() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed(
                        "contact",
                        "Last-good contact remains readable",
                        "Exact source fixture")),
                true,
                null);

        String description = HeartbeatFrameAccessibility.collapsedContentDescription(frame);
        assertTrue(description.contains("1 material skill light"));
        assertTrue(description.contains("Contact Preservation"));
        assertTrue(description.contains("Last-good contact remains readable"));
    }

    @Test
    public void interruptedRefreshAnnouncesBoundaryWithoutDiscardedAttemptContent() {
        HeartbeatSceneGraph.Frame complete = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed(
                        "contact",
                        "Visible consequence",
                        "evidence-a")),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed(
                        "contact",
                        "Discarded attempted consequence",
                        "evidence-b")),
                false,
                complete);

        String description = HeartbeatFrameAccessibility.collapsedContentDescription(interrupted);
        assertTrue(description.contains("Visible consequence"));
        assertTrue(description.contains("Heartbeat refresh interrupted"));
        assertTrue(description.contains("Showing last complete heartbeat pulse-a"));
        assertFalse(description.contains("Discarded attempted consequence"));
    }

    @Test
    public void detailLookupUsesStableVisibleFocusIndexOnly() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed(
                        "contact",
                        "Visible consequence",
                        "evidence-a")),
                true,
                null);

        String detail = HeartbeatFrameAccessibility.detailContentDescription(frame, 0);
        assertTrue(detail.contains("Why: Preserve last-good heartbeat through refresh failure"));
        assertTrue(detail.contains("Evidence: evidence-a"));
        assertTrue(HeartbeatFrameAccessibility.detailContentDescription(frame, 99).isEmpty());
    }
}
