package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/**
 * Source-only regression fixtures for separating exact pulse/checkpoint identity
 * from actual Operator Overlay content work. These tests are not Android/runtime
 * evidence until an authorized test body executes them.
 */
public class HeartbeatInvisiblePulseIdDedupTest {
    private static HeartbeatSkillPolicy.Candidate typed(String evidence) {
        return new HeartbeatSkillPolicy.Candidate(
                "contact",
                "Contact Preservation",
                "doctrine",
                "Contact Preservation",
                "Avoid focus churn when only an invisible pulse identity advances.",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Presented heartbeat contact is unchanged.",
                evidence);
    }

    @Test
    public void newPulseIdWithSamePresentedSurfaceDoesNotCreateUiOrSpeechWork() {
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed("Exact evidence")),
                true,
                null);
        HeartbeatSceneGraph.Frame secondFrame = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed("Exact evidence")),
                true,
                firstFrame);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "contact");
        HeartbeatOverlayRefreshPlan.Plan second =
                HeartbeatOverlayRefreshPlan.fromFrame(secondFrame, first.selectedControlId);

        assertNotEquals(
                HeartbeatFrameCheckpoint.contactSha256(firstFrame),
                HeartbeatFrameCheckpoint.contactSha256(secondFrame));
        assertEquals(
                HeartbeatFrameCheckpoint.presentationSha256(firstFrame),
                HeartbeatFrameCheckpoint.presentationSha256(secondFrame));
        assertEquals(first.structureIdentity, second.structureIdentity);
        assertEquals(first.renderIdentity, second.renderIdentity);
        assertEquals(first.announcementIdentity, second.announcementIdentity);
        assertEquals("contact", second.selectedControlId);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                second));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
                first.renderIdentity,
                second));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                second));
    }

    @Test
    public void evidenceChangeStillCreatesContentWorkWithoutChristmasSpeech() {
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed("Evidence A")),
                true,
                null);
        HeartbeatSceneGraph.Frame secondFrame = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed("Evidence B")),
                true,
                firstFrame);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "contact");
        HeartbeatOverlayRefreshPlan.Plan second =
                HeartbeatOverlayRefreshPlan.fromFrame(secondFrame, first.selectedControlId);

        assertTrue(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
                first.renderIdentity,
                second));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                second));
    }
}
