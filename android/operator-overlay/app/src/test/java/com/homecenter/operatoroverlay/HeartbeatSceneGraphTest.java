package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class HeartbeatSceneGraphTest {
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
                "test-doctrine:" + id,
                "Materially constrained this pulse",
                state,
                changed,
                consequence,
                evidenceBoundary);
    }

    private static HeartbeatSkillPolicy.Candidate active(String id, String consequence) {
        return typed(
                id,
                id,
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                consequence,
                "Exact source fixture");
    }

    private static HeartbeatSkillPolicy.Candidate typedActive(
            String id,
            String evidenceBoundary) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "repository_skill",
                "skills/" + id + "/SKILL.md",
                "Materially constrained this pulse",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Preserved capability-state truth",
                evidenceBoundary);
    }

    @Test
    public void displayReadyOrderBecomesStableFocusOrderWithAccessibleTouchTargets() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-1",
                Arrays.asList(
                        active("hunger", "Rejected decorative status"),
                        typed(
                                "regnet",
                                "Regnet QA",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "Renderer not wired",
                                "Exact renderer boundary")),
                true,
                null);

        assertEquals(2, frame.nodes.size());
        assertEquals(0, frame.nodes.get(0).focusIndex);
        assertEquals(1, frame.nodes.get(1).focusIndex);
        assertEquals(48, frame.nodes.get(0).touchTargetDp);
        assertEquals("●", frame.nodes.get(0).stateToken);
        assertEquals("□", frame.nodes.get(1).stateToken);
        assertTrue(frame.nodes.get(1).contentDescription.contains("blocked"));
        assertFalse(frame.refreshInterrupted);
    }

    @Test
    public void typedNodeCarriesReasonEvidenceAndProvenanceForTouchDetail() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-typed",
                Collections.singletonList(typedActive("execution-truth", "Exact branch blob")),
                true,
                null);
        HeartbeatSceneGraph.Node node = frame.nodes.get(0);

        assertEquals("repository_skill", node.provenanceKind);
        assertEquals("skills/execution-truth/SKILL.md", node.provenanceLocator);
        assertEquals("Materially constrained this pulse", node.activationReason);
        assertEquals("Exact branch blob", node.evidenceBoundary);
        assertTrue(node.detailContentDescription.contains("Why: Materially constrained this pulse"));
        assertTrue(node.detailContentDescription.contains("Evidence: Exact branch blob"));
        assertTrue(node.detailContentDescription.contains("Source: repository skill skills/execution-truth/SKILL.md"));
    }

    @Test
    public void nonColorTokensDistinguishEveryMaterialState() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-tokens",
                Arrays.asList(
                        active("active", "Changed"),
                        typed(
                                "blocked", "Blocked", HeartbeatSkillPolicy.State.BLOCKED,
                                false, "Exact blocker", "Blocked fixture"),
                        typed(
                                "fault", "Fault", HeartbeatSkillPolicy.State.FAULT,
                                false, "Exact fault", "Fault fixture"),
                        typed(
                                "recovered", "Recovered", HeartbeatSkillPolicy.State.RECOVERED,
                                true, "Recovered this pulse", "Recovery fixture")),
                true,
                null);

        assertEquals("●", frame.nodes.get(0).stateToken);
        assertEquals("□", frame.nodes.get(1).stateToken);
        assertEquals("×", frame.nodes.get(2).stateToken);
        assertEquals("◇", frame.nodes.get(3).stateToken);
    }

    @Test
    public void incompleteRefreshPreservesLastCompleteContactSurface() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(active("contact", "Contact established")),
                true,
                null);

        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "pulse-broken",
                Collections.singletonList(active("replacement", "Must not leak")),
                false,
                lastGood);

        assertTrue(interrupted.refreshInterrupted);
        assertEquals("pulse-good", interrupted.visiblePulseId);
        assertEquals("pulse-broken", interrupted.attemptedPulseId);
        assertEquals(1, interrupted.nodes.size());
        assertSame(lastGood.nodes.get(0), interrupted.nodes.get(0));
        assertEquals("contact", interrupted.nodes.get(0).id);
        assertFalse(interrupted.transitionMotionAllowed);
        assertEquals("Pulse is incomplete.", interrupted.refreshBoundary);
        assertTrue(interrupted.interruptedRefreshDescription().contains("pulse-good"));
        assertTrue(interrupted.interruptedRefreshDescription().contains("Pulse is incomplete"));
    }

    @Test
    public void completePulseWithUntypedMaterialPreservesLastGoodAndNamesBoundary() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(active("contact", "Contact established")),
                true,
                null);
        HeartbeatSkillPolicy.Candidate legacyMaterial = new HeartbeatSkillPolicy.Candidate(
                "legacy",
                "Legacy material",
                HeartbeatSkillPolicy.State.FAULT,
                false,
                "Fault exists but provenance/evidence contract is absent");

        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "pulse-invalid",
                Collections.singletonList(legacyMaterial),
                true,
                lastGood);

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("pulse-invalid", rejected.attemptedPulseId);
        assertSame(lastGood.nodes.get(0), rejected.nodes.get(0));
        assertTrue(rejected.refreshBoundary.contains("typed source/evidence contract"));
        assertFalse(rejected.transitionMotionAllowed);
    }

    @Test
    public void blankCompletePulseIdentityCannotReplaceLastGoodFrame() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(active("contact", "Contact established")),
                true,
                null);

        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "   ",
                Collections.singletonList(active("replacement", "Anonymous replacement")),
                true,
                lastGood);

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("", rejected.attemptedPulseId);
        assertSame(lastGood.nodes.get(0), rejected.nodes.get(0));
        assertEquals("Pulse identity is missing.", rejected.refreshBoundary);
        assertFalse(rejected.transitionMotionAllowed);
    }

    @Test
    public void identicalSemanticFrameDoesNotBlinkAgain() {
        HeartbeatSceneGraph.Frame first = HeartbeatSceneGraph.build(
                "pulse-1",
                Collections.singletonList(active("warm-walls", "Boundary became warm")),
                true,
                null);
        HeartbeatSceneGraph.Frame second = HeartbeatSceneGraph.build(
                "pulse-2",
                Collections.singletonList(active("warm-walls", "Boundary became warm")),
                true,
                first);

        assertTrue(first.transitionMotionAllowed);
        assertFalse(second.transitionMotionAllowed);
        assertFalse(second.nodes.get(0).transitionMotion);
    }

    @Test
    public void evidenceOnlyMetadataChangeDoesNotCreateDecorativeBlink() {
        HeartbeatSceneGraph.Frame first = HeartbeatSceneGraph.build(
                "pulse-1",
                Collections.singletonList(typedActive("execution-truth", "Blob A")),
                true,
                null);
        HeartbeatSceneGraph.Frame second = HeartbeatSceneGraph.build(
                "pulse-2",
                Collections.singletonList(typedActive("execution-truth", "Blob B")),
                true,
                first);

        assertFalse(second.transitionMotionAllowed);
        assertFalse(second.nodes.get(0).transitionMotion);
        assertEquals("Blob B", second.nodes.get(0).evidenceBoundary);
        assertTrue(second.nodes.get(0).detailContentDescription.contains("Evidence: Blob B"));
    }

    @Test
    public void consequenceChangeAllowsOneMeaningfulChristmasLightTransition() {
        HeartbeatSceneGraph.Frame first = HeartbeatSceneGraph.build(
                "pulse-1",
                Collections.singletonList(active("shovel", "Failure exposed boundary A")),
                true,
                null);
        HeartbeatSceneGraph.Frame second = HeartbeatSceneGraph.build(
                "pulse-2",
                Collections.singletonList(active("shovel", "Failure exposed boundary B")),
                true,
                first);

        assertTrue(second.transitionMotionAllowed);
        assertTrue(second.nodes.get(0).transitionMotion);
    }

    @Test
    public void removedMaterialLightCountsAsMeaningfulTransition() {
        HeartbeatSceneGraph.Frame first = HeartbeatSceneGraph.build(
                "pulse-1",
                Arrays.asList(
                        active("warm-walls", "Boundary became warm"),
                        active("hunger", "Ate decorative status")),
                true,
                null);
        HeartbeatSceneGraph.Frame second = HeartbeatSceneGraph.build(
                "pulse-2",
                Collections.singletonList(active("warm-walls", "Boundary became warm")),
                true,
                first);

        assertTrue(second.transitionMotionAllowed);
        assertFalse(second.nodes.get(0).transitionMotion);
        assertEquals(1, second.nodes.size());
    }

    @Test
    public void incompleteFirstPulseExposesInterruptionWithoutInventingLights() {
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "pulse-zero",
                Collections.singletonList(active("fake", "Must not appear")),
                false,
                null);

        assertTrue(interrupted.refreshInterrupted);
        assertTrue(interrupted.nodes.isEmpty());
        assertFalse(interrupted.transitionMotionAllowed);
        assertEquals("Pulse is incomplete.", interrupted.refreshBoundary);
        assertTrue(interrupted.interruptedRefreshDescription().contains("No complete heartbeat"));
    }
}
