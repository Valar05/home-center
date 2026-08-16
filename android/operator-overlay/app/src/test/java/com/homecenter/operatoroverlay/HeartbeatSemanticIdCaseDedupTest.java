package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/**
 * Source regression for the exact-evidence / presentation-identity split.
 *
 * <p>Semantic heartbeat ids are case-insensitive UI identities, but exact source
 * spelling remains part of checkpoint/evidence truth. A case-only producer drift
 * must therefore be observable to checkpointing without becoming fake UI work,
 * unsolicited speech, or Christmas-light motion.</p>
 */
public class HeartbeatSemanticIdCaseDedupTest {
    private static HeartbeatSkillPolicy.Candidate regnet(String id) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                "Regnet QA",
                "doctrine",
                "Regnet QA",
                "Testing is materially blocked by the deterministic CI boundary",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Tests remain blocked; source evidence must not impersonate execution",
                "GitHub Actions budget prevents the Android job from starting");
    }

    @Test
    public void caseOnlySemanticIdDriftAdvancesExactCheckpointButEarnsNoUiWork() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(regnet("Regnet")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(regnet("regnet")),
                true,
                before);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(before, "REGNET");
        HeartbeatOverlayRefreshPlan.Plan next =
                HeartbeatOverlayRefreshPlan.fromFrame(after, "REGNET");

        assertFalse(HeartbeatFrameCheckpoint.sameVisibleContact(before, after));
        assertTrue(HeartbeatFrameCheckpoint.samePresentation(before, after));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
        assertFalse(after.transitionMotionAllowed);

        assertEquals(first.structureIdentity, next.structureIdentity);
        assertEquals(first.renderIdentity, next.renderIdentity);
        assertEquals(first.announcementIdentity, next.announcementIdentity);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                next));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
                first.renderIdentity,
                next));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next));
        assertEquals("regnet", next.selectedControlId.toLowerCase(java.util.Locale.ROOT));
    }
}
