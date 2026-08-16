package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

/**
 * Source-level regression contract for translating semantic Christmas-light motion
 * into a bounded native-owner decision without decorative replay.
 *
 * <p>These fixtures are regression source only until an authorized test runner
 * executes them.</p>
 */
public class HeartbeatNativeMotionPolicyTest {
    private static HeartbeatSkillPolicy.Candidate candidate(
            String id,
            HeartbeatSkillPolicy.State state,
            String consequence,
            String evidence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "doctrine",
                "fixture:native-motion",
                "Material transition must earn motion rather than decoration",
                state,
                true,
                consequence,
                evidence);
    }

    @Test
    public void materialNodeTransitionMayAnimateOnceWhenPresentedAndPlatformAllowsIt() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-before",
                Collections.singletonList(candidate(
                        "warm-walls",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        "wall closed",
                        "evidence-a")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-after",
                Collections.singletonList(candidate(
                        "warm-walls",
                        HeartbeatSkillPolicy.State.RECOVERED,
                        "wall reopened",
                        "evidence-b")),
                true,
                before);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(after);
        HeartbeatNativeMotionPolicy.Decision decision = model.motionDecisionFor(
                "warm-walls",
                true,
                true);

        assertTrue(decision.animate);
        assertEquals(
                HeartbeatNativeMotionPolicy.Boundary.MATERIAL_TRANSITION,
                decision.boundary);
        assertEquals(140L, decision.durationMs);
    }

    @Test
    public void collapsedOrPlatformDisabledSurfaceCannotReplaySemanticMotion() {
        HeartbeatNativeMotionPolicy.Decision collapsed =
                HeartbeatNativeMotionPolicy.decideNode(true, true, false, true);
        HeartbeatNativeMotionPolicy.Decision reducedMotion =
                HeartbeatNativeMotionPolicy.decideNode(true, true, true, false);

        assertFalse(collapsed.animate);
        assertEquals(
                HeartbeatNativeMotionPolicy.Boundary.SURFACE_NOT_PRESENTED,
                collapsed.boundary);
        assertFalse(reducedMotion.animate);
        assertEquals(
                HeartbeatNativeMotionPolicy.Boundary.PLATFORM_ANIMATORS_DISABLED,
                reducedMotion.boundary);
    }

    @Test
    public void evidenceOnlyRefreshDoesNotEarnChristmasMotion() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-before",
                Collections.singletonList(candidate(
                        "regnet",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        "test gate unchanged",
                        "evidence-a")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-after",
                Collections.singletonList(candidate(
                        "regnet",
                        HeartbeatSkillPolicy.State.BLOCKED,
                        "test gate unchanged",
                        "evidence-b")),
                true,
                before);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(after);
        assertFalse(model.transitionMotionAllowed);
        assertFalse(model.anyNodeTransitionMotion);
        assertFalse(model.motionDecisionFor("regnet", true, true).animate);
        assertFalse(model.summaryMotionDecision(true, true).animate);
    }

    @Test
    public void pureRemovalUsesSummaryFallbackWithoutInventingReplacementLight() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-before",
                Arrays.asList(
                        candidate(
                                "contact",
                                HeartbeatSkillPolicy.State.ACTIVE,
                                "contact preserved",
                                "evidence-contact"),
                        candidate(
                                "temporary",
                                HeartbeatSkillPolicy.State.ACTIVE,
                                "temporary work existed",
                                "evidence-temporary")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-after",
                Collections.singletonList(candidate(
                        "contact",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        "contact preserved",
                        "evidence-contact")),
                true,
                before);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(after);
        assertTrue(model.transitionMotionAllowed);
        assertFalse(model.anyNodeTransitionMotion);
        assertTrue(model.summaryTransitionMotion);
        assertEquals(1, model.controls.size());
        assertTrue(model.summaryMotionDecision(true, true).animate);
    }

    @Test
    public void interruptedPreservedFrameCannotLeakPriorNodeMotion() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-accepted",
                Collections.singletonList(candidate(
                        "contact",
                        HeartbeatSkillPolicy.State.RECOVERED,
                        "contact recovered",
                        "evidence")),
                true,
                null);
        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.preserveRejectedRefresh(
                "pulse-next",
                accepted,
                "refresh rejected");

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(rejected);
        assertFalse(model.transitionMotionAllowed);
        assertFalse(model.anyNodeTransitionMotion);
        assertFalse(model.summaryTransitionMotion);
        assertFalse(model.motionDecisionFor("contact", true, true).animate);
    }
}
