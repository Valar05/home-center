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
    public void coldStartNeedsStructureAndContentButDoesNotPretendItObservedATransition() {
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

        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuildStructure("", plan));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRefreshContent("", plan));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuild("", plan));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce("", plan));
    }

    @Test
    public void exactSceneRetryDoesNotRebuildRefreshOrReannounce() {
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
        assertEquals(first.structureIdentity, retry.structureIdentity);
        assertEquals(first.renderIdentity, retry.renderIdentity);
        assertEquals(first.announcementIdentity, retry.announcementIdentity);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                retry));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
                first.renderIdentity,
                retry));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                retry));
    }

    @Test
    public void evidenceOnlyRefreshKeepsNativeStructureButRefreshesDetailWithoutSpeech() {
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

        assertEquals(first.structureIdentity, next.structureIdentity);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                next));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
                first.renderIdentity,
                next));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next));
        assertEquals("regnet", next.selectedControlId);
    }

    @Test
    public void stateChangeKeepsSameNativeControlsButRefreshesAndAnnounces() {
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

        assertEquals(first.structureIdentity, next.structureIdentity);
        assertNotEquals(first.renderIdentity, next.renderIdentity);
        assertNotEquals(first.announcementIdentity, next.announcementIdentity);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                next));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
                first.renderIdentity,
                next));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next));
    }

    @Test
    public void reorderOrMembershipChangeRequiresNativeStructureRebuild() {
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.build(
                "pulse-one",
                Arrays.asList(
                        typed(
                                "a",
                                "A",
                                HeartbeatSkillPolicy.State.ACTIVE,
                                true,
                                "A active",
                                "Boundary"),
                        typed(
                                "b",
                                "B",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "B blocked",
                                "Boundary")),
                true,
                null);
        HeartbeatSceneGraph.Frame reordered = HeartbeatSceneGraph.build(
                "pulse-two",
                Arrays.asList(
                        typed(
                                "b",
                                "B",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "B blocked",
                                "Boundary"),
                        typed(
                                "a",
                                "A",
                                HeartbeatSkillPolicy.State.ACTIVE,
                                true,
                                "A active",
                                "Boundary")),
                true,
                firstFrame);
        HeartbeatSceneGraph.Frame added = HeartbeatSceneGraph.build(
                "pulse-three",
                Arrays.asList(
                        typed(
                                "a",
                                "A",
                                HeartbeatSkillPolicy.State.ACTIVE,
                                true,
                                "A active",
                                "Boundary"),
                        typed(
                                "b",
                                "B",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "B blocked",
                                "Boundary"),
                        typed(
                                "c",
                                "C",
                                HeartbeatSkillPolicy.State.RECOVERED,
                                true,
                                "C recovered",
                                "Boundary")),
                true,
                firstFrame);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "a");
        HeartbeatOverlayRefreshPlan.Plan reorderPlan =
                HeartbeatOverlayRefreshPlan.fromFrame(reordered, "a");
        HeartbeatOverlayRefreshPlan.Plan addedPlan =
                HeartbeatOverlayRefreshPlan.fromFrame(added, "a");

        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                reorderPlan));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                addedPlan));
    }

    @Test
    public void semanticIdCaseDoesNotForceStructureReplacement() {
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.build(
                "pulse-one",
                Collections.singletonList(typed(
                        "Regnet",
                        "Regnet",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        false,
                        "Blocked",
                        "Boundary")),
                true,
                null);
        HeartbeatSceneGraph.Frame caseOnly = HeartbeatSceneGraph.build(
                "pulse-two",
                Collections.singletonList(typed(
                        "regnet",
                        "Regnet",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        false,
                        "Blocked",
                        "Boundary")),
                true,
                firstFrame);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "REGNET");
        HeartbeatOverlayRefreshPlan.Plan next =
                HeartbeatOverlayRefreshPlan.fromFrame(caseOnly, "REGNET");

        assertEquals(first.structureIdentity, next.structureIdentity);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                first.structureIdentity,
                next));
    }

    @Test
    public void mutedAndHiddenPresentationSuppressesSpeechWithoutChangingSemanticIdentity() {
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.build(
                "pulse-one",
                Collections.singletonList(typed(
                        "warm-walls",
                        "Warm Walls",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        false,
                        "Waiting",
                        "Boundary")),
                true,
                null);
        HeartbeatSceneGraph.Frame recovered = HeartbeatSceneGraph.build(
                "pulse-two",
                Collections.singletonList(typed(
                        "warm-walls",
                        "Warm Walls",
                        HeartbeatSkillPolicy.State.RECOVERED,
                        true,
                        "Contact returned",
                        "Boundary")),
                true,
                firstFrame);

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "warm-walls");
        HeartbeatOverlayRefreshPlan.Plan next =
                HeartbeatOverlayRefreshPlan.fromFrame(recovered, "warm-walls");

        assertTrue(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next,
                false,
                true));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next,
                true,
                true));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                first.announcementIdentity,
                next,
                false,
                false));
        assertEquals(
                next.announcementIdentity,
                HeartbeatOverlayRefreshPlan.fromFrame(recovered, "warm-walls").announcementIdentity);
    }

    @Test
    public void interruptedRefreshPreservesSelectionAndNativeStructureButChangesWoundContentOnce() {
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
        assertEquals(good.structureIdentity, wound.structureIdentity);
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(
                good.structureIdentity,
                wound));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
                good.renderIdentity,
                wound));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                good.announcementIdentity,
                wound));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRefreshContent(
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
