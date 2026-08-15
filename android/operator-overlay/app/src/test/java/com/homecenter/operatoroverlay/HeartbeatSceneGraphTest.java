package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class HeartbeatSceneGraphTest {
    private static HeartbeatSkillPolicy.Candidate active(String id, String consequence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                consequence);
    }

    @Test
    public void materialOrderBecomesStableFocusOrderWithAccessibleTouchTargets() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-1",
                Arrays.asList(
                        active("hunger", "Rejected decorative status"),
                        new HeartbeatSkillPolicy.Candidate(
                                "regnet",
                                "Regnet QA",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "Renderer not wired")),
                true,
                null);

        assertEquals(2, frame.nodes.size());
        assertEquals(0, frame.nodes.get(0).focusIndex);
        assertEquals(1, frame.nodes.get(1).focusIndex);
        assertEquals(48, frame.nodes.get(0).touchTargetDp);
        assertEquals("●", frame.nodes.get(0).stateToken);
        assertEquals("□", frame.nodes.get(1).stateToken);
        assertTrue(frame.nodes.get(1).contentDescription.contains("blocked"));
    }

    @Test
    public void nonColorTokensDistinguishEveryMaterialState() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-tokens",
                Arrays.asList(
                        active("active", "Changed"),
                        new HeartbeatSkillPolicy.Candidate(
                                "blocked", "Blocked", HeartbeatSkillPolicy.State.BLOCKED,
                                false, "Exact blocker"),
                        new HeartbeatSkillPolicy.Candidate(
                                "fault", "Fault", HeartbeatSkillPolicy.State.FAULT,
                                false, "Exact fault"),
                        new HeartbeatSkillPolicy.Candidate(
                                "recovered", "Recovered", HeartbeatSkillPolicy.State.RECOVERED,
                                true, "Recovered this pulse")),
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
        assertTrue(interrupted.interruptedRefreshDescription().contains("pulse-good"));
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
    public void incompleteFirstPulseExposesInterruptionWithoutInventingLights() {
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "pulse-zero",
                Collections.singletonList(active("fake", "Must not appear")),
                false,
                null);

        assertTrue(interrupted.refreshInterrupted);
        assertTrue(interrupted.nodes.isEmpty());
        assertFalse(interrupted.transitionMotionAllowed);
        assertTrue(interrupted.interruptedRefreshDescription().contains("No complete heartbeat"));
    }
}
