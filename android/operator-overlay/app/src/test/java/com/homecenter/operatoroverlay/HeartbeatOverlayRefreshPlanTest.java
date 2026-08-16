package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class HeartbeatOverlayRefreshPlanTest {
    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            String label,
            HeartbeatSkillPolicy.State state,
            boolean changed,
            String consequence,
            String evidenceBoundary) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                label,
                "doctrine",
                "fixture:" + id,
                "Materially active in fixture",
                state,
                changed,
                consequence,
                evidenceBoundary);
    }

    @Test
    public void coldStartRendersButDoesNotPretendItObservedATransition() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-one",
                Collections.singletonList(typed(
                        "contact",
                        "Contact",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Contact established",
                        "Exact fixture boundary")),
                true,
                null);
        HeartbeatOverlayRefreshPlan.Plan plan =
                HeartbeatOverlayRefreshPlan.fromFrame(frame, "contact");

        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuild("", plan));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce("", plan));
    }

    @Test
    public void exactSceneRetryDoesNotRebuildOrReannounce() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-one",
                Collections.singletonList(typed(
                        "contact",
                        "Contact",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Contact established",
                        "Exact fixture boundary")),
                true,
                null);
        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(frame, "contact");
        HeartbeatOverlayRefreshPlan.Plan retry =
                HeartbeatOverlayRefreshPlan.fromFrame(frame, first.selectedControlId);

        assertEquals("contact", retry.selectedControlId);
        assertEquals(first.renderIdentity, retry.renderIdentity);
        assertEquals(first.announcementIdentity, retry.announcementIdentity);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuild(first.renderIdentity, retry));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                retry));
    }

    @Test
    public void evidenceOnlyRefreshRebuildsDetailWithoutUnsolicitedSpeech() {
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.build(
                "pulse-one",
                Collections.singletonList(typed(
                        "regnet",
                        "Regnet",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        false,
                        "Tests blocked",
                        "Evidence A")),
                true,
                null);
        HeartbeatSceneGraph.Frame evidenceRefresh = HeartbeatSceneGraph.build(
                "pulse-two",
                Collections.singletonList(typed(
                        "regnet",
                        "Regnet",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        false,
                        "Tests blocked",
                        "Evidence B")),
                true,
                firstFrame);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "regnet");
        HeartbeatOverlayRefreshPlan.Plan next =
                HeartbeatOverlayRefreshPlan.fromFrame(evidenceRefresh, "regnet");

        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuild(first.renderIdentity, next));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next));
        assertEquals("regnet", next.selectedControlId);
    }

    @Test
    public void stateChangeRebuildsAndChangesAnnouncementIdentity() {
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.build(
                "pulse-one",
                Collections.singletonList(typed(
                        "shovel",
                        "Failure Is The Shovel",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        false,
                        "Waiting",
                        "Boundary")),
                true,
                null);
        HeartbeatSceneGraph.Frame recovered = HeartbeatSceneGraph.build(
                "pulse-two",
                Collections.singletonList(typed(
                        "shovel",
                        "Failure Is The Shovel",
                        HeartbeatSkillPolicy.State.RECOVERED,
                        true,
                        "Different front advanced",
                        "Boundary")),
                true,
                firstFrame);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "shovel");
        HeartbeatOverlayRefreshPlan.Plan next =
                HeartbeatOverlayRefreshPlan.fromFrame(recovered, "shovel");

        assertNotEquals(first.renderIdentity, next.renderIdentity);
        assertNotEquals(first.announcementIdentity, next.announcementIdentity);
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuild(first.renderIdentity, next));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next));
    }

    @Test
    public void interruptedRefreshPreservesSelectionAndAnnouncesWoundOnce() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Arrays.asList(
                        typed(
                                "warm-walls",
                                "Warm Walls",
                                HeartbeatSkillPolicy.State.ACTIVE,
                                true,
                                "Contact established",
                                "Wall intact"),
                        typed(
                                "regnet",
                                "Regnet",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "CI blocked",
                                "Actions budget")),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "pulse-bad",
                lastGood,
                "Stored heartbeat SHA-256 mismatch.");

        HeartbeatOverlayRefreshPlan.Plan good =
                HeartbeatOverlayRefreshPlan.fromFrame(lastGood, "regnet");
        HeartbeatOverlayRefreshPlan.Plan wound =
                HeartbeatOverlayRefreshPlan.fromFrame(interrupted, "regnet");
        HeartbeatOverlayRefreshPlan.Plan sameWound =
                HeartbeatOverlayRefreshPlan.fromFrame(interrupted, wound.selectedControlId);

        assertEquals("regnet", wound.selectedControlId);
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuild(good.renderIdentity, wound));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                good.announcementIdentity,
                wound));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuild(
                wound.renderIdentity,
                sameWound));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                wound.announcementIdentity,
                sameWound));
        assertFalse(wound.model.transitionMotionAllowed);
    }

    @Test
    public void missingSelectedLightClearsSelectionBySemanticIdentity() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-one",
                Collections.singletonList(typed(
                        "hunger",
                        "Hunger",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Ate the poster",
                        "Boundary")),
                true,
                null);

        HeartbeatOverlayRefreshPlan.Plan plan =
                HeartbeatOverlayRefreshPlan.fromFrame(frame, "missing-light");

        assertEquals("", plan.selectedControlId);
    }

    @Test
    public void persistedStorageRejectionKeepsLastGoodContactAndSelection() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(typed(
                        "contact",
                        "Contact Preservation",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Last good wall remains",
                        "Boundary")),
                true,
                null);
        byte[] hostile = new byte[] {(byte) 0xc3, 0x28};

        HeartbeatOverlayRefreshPlan.PersistedPlan result =
                HeartbeatOverlayRefreshPlan.projectPersisted(
                        hostile,
                        hostile.length,
                        "0000000000000000000000000000000000000000000000000000000000000000",
                        1L,
                        lastGood,
                        "contact");

        assertFalse(result.projection.storageAccepted);
        assertTrue(result.plan.model.refreshInterrupted);
        assertEquals("pulse-good", result.plan.model.visiblePulseId);
        assertEquals("contact", result.plan.selectedControlId);
        assertEquals(1, result.plan.model.controls.size());
        assertFalse(result.plan.model.controls.get(0).transitionMotion);
    }
}
