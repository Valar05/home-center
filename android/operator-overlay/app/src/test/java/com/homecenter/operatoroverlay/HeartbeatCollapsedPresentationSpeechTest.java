package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/**
 * Source-level regression contract for automatic heartbeat speech when the whole
 * overlay remains visible but the heartbeat/details surface is collapsed/GONE.
 *
 * <p>These fixtures are regression source only until an authorized Android/test
 * runner executes them.</p>
 */
public class HeartbeatCollapsedPresentationSpeechTest {
    private static HeartbeatSkillPolicy.Candidate candidate(
            HeartbeatSkillPolicy.State state,
            boolean changed,
            String consequence) {
        return new HeartbeatSkillPolicy.Candidate(
                "warm-walls",
                "Warm Walls",
                "doctrine",
                "fixture:collapsed-heartbeat-surface",
                "Presentation truth must gate unsolicited speech",
                state,
                changed,
                consequence,
                "Exact collapsed-surface fixture boundary");
    }

    private static HeartbeatOverlayRefreshPlan.Plan[] transitionPlans() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-before",
                Collections.singletonList(candidate(
                        HeartbeatSkillPolicy.State.BLOCKED,
                        false,
                        "Waiting behind the wall")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-after",
                Collections.singletonList(candidate(
                        HeartbeatSkillPolicy.State.RECOVERED,
                        true,
                        "Warm wall contact recovered")),
                true,
                before);
        return new HeartbeatOverlayRefreshPlan.Plan[] {
                HeartbeatOverlayRefreshPlan.fromFrame(before, "warm-walls"),
                HeartbeatOverlayRefreshPlan.fromFrame(after, "warm-walls")
        };
    }

    @Test
    public void visibleHeartbeatSurfaceMaySpeakEstablishedTransition() {
        HeartbeatOverlayRefreshPlan.Plan[] plans = transitionPlans();

        assertTrue(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                plans[0].announcementIdentity,
                plans[1],
                false,
                true,
                true));
    }

    @Test
    public void visibleRootDoesNotAuthorizeSpeechFromCollapsedHeartbeatSurface() {
        HeartbeatOverlayRefreshPlan.Plan[] plans = transitionPlans();

        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                plans[0].announcementIdentity,
                plans[1],
                false,
                true,
                false));
    }

    @Test
    public void compatibilityGateCannotRepresentCollapsedSubsurfaceTruth() {
        HeartbeatOverlayRefreshPlan.Plan[] plans = transitionPlans();

        // The four-argument compatibility path has only root visibility and therefore
        // treats a visible root as a visible heartbeat surface. Existing-owner wiring
        // with real details/subtree visibility must use the five-argument gate.
        assertTrue(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                plans[0].announcementIdentity,
                plans[1],
                false,
                true));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                plans[0].announcementIdentity,
                plans[1],
                false,
                true,
                false));
    }

    @Test
    public void muteOrHiddenOverlayStillSuppressesAutomaticHeartbeatSpeech() {
        HeartbeatOverlayRefreshPlan.Plan[] plans = transitionPlans();

        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                plans[0].announcementIdentity,
                plans[1],
                true,
                true,
                true));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                plans[0].announcementIdentity,
                plans[1],
                false,
                false,
                true));
    }

    @Test
    public void expandingAfterSuppressedCollapsedTransitionDoesNotReplayIt() {
        HeartbeatOverlayRefreshPlan.Plan[] plans = transitionPlans();

        // The owner suppresses speech while collapsed but still remembers the new
        // announcement identity. Expanding later therefore sees no new transition.
        String rememberedWhileCollapsed = plans[1].announcementIdentity;
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(
                rememberedWhileCollapsed,
                plans[1],
                false,
                true,
                true));
    }
}
