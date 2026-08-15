package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

public class HeartbeatFrameCheckpointTest {
    private static HeartbeatSkillPolicy.Candidate typed(
            String evidence,
            String consequence) {
        return new HeartbeatSkillPolicy.Candidate(
                "contact",
                "Contact Preservation",
                "doctrine",
                "Contact Preservation",
                "Keep last-good heartbeat readable during refresh failure",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                consequence,
                evidence);
    }

    @Test
    public void interruptedRefreshDoesNotMutateVisibleContactFingerprint() {
        HeartbeatSceneGraph.Frame complete = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed("evidence-a", "Last-good contact is visible")),
                true,
                null);

        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed("evidence-b", "Attempted content must not replace contact")),
                false,
                complete);

        assertTrue(interrupted.refreshInterrupted);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(complete, interrupted));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(complete, interrupted));
    }

    @Test
    public void evidenceOnlyRefreshChangesContactIdentityButNotTransitionIdentity() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed("evidence-a", "Stable consequence")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed("evidence-b", "Stable consequence")),
                true,
                before);

        assertFalse(after.transitionMotionAllowed);
        assertFalse(HeartbeatFrameCheckpoint.sameVisibleContact(before, after));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
    }

    @Test
    public void consequenceChangeEarnsNewTransitionIdentity() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed("evidence-a", "Old consequence")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed("evidence-b", "New consequence")),
                true,
                before);

        assertTrue(after.transitionMotionAllowed);
        assertFalse(HeartbeatFrameCheckpoint.sameVisibleContact(before, after));
        assertFalse(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
    }
}
