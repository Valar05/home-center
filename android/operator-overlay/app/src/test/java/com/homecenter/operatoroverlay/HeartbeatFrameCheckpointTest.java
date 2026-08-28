package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class HeartbeatFrameCheckpointTest {
    private static HeartbeatSkillPolicy.Candidate typed(
            String evidence,
            String consequence) {
        return typed("contact", evidence, consequence);
    }

    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            String evidence,
            String consequence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                "Contact Preservation " + id,
                "doctrine",
                "Contact Preservation",
                "Keep last-good heartbeat readable during refresh failure",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                consequence,
                evidence);
    }

    private static HeartbeatSkillPolicy.Candidate typedWithStablePresentation(
            String id,
            String evidence,
            String consequence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                "Regnet QA",
                "doctrine",
                "Regnet QA",
                "Keep case-only semantic identity drift from becoming fake UI work",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
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
        assertTrue(HeartbeatFrameCheckpoint.samePresentation(complete, interrupted));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(complete, interrupted));
    }

    @Test
    public void newPulseIdentityWithoutSurfaceChangeIsNewCheckpointButSamePresentation() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed("evidence-a", "Stable consequence")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed("evidence-a", "Stable consequence")),
                true,
                before);

        assertFalse(HeartbeatFrameCheckpoint.sameVisibleContact(before, after));
        assertTrue(HeartbeatFrameCheckpoint.samePresentation(before, after));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
    }

    @Test
    public void caseOnlySemanticIdChangeIsExactCheckpointChangeButNotPresentationWork() {
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typedWithStablePresentation(
                        "Regnet",
                        "Actions budget is blocked",
                        "Testing remains blocked")),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typedWithStablePresentation(
                        "regnet",
                        "Actions budget is blocked",
                        "Testing remains blocked")),
                true,
                before);

        assertFalse(after.transitionMotionAllowed);
        assertFalse(HeartbeatFrameCheckpoint.sameVisibleContact(before, after));
        assertTrue(HeartbeatFrameCheckpoint.samePresentation(before, after));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
    }

    @Test
    public void evidenceOnlyRefreshChangesContactAndPresentationButNotTransitionIdentity() {
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
        assertFalse(HeartbeatFrameCheckpoint.samePresentation(before, after));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
    }

    @Test
    public void pureSceneReorderChangesContactAndPresentationButNotTransitionIdentity() {
        HeartbeatSkillPolicy.Candidate alpha = typed(
                "alpha",
                "evidence-alpha",
                "Stable alpha consequence");
        HeartbeatSkillPolicy.Candidate beta = typed(
                "beta",
                "evidence-beta",
                "Stable beta consequence");
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-a",
                Arrays.asList(alpha, beta),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-b",
                Arrays.asList(beta, alpha),
                true,
                before);

        assertFalse(after.transitionMotionAllowed);
        assertFalse(HeartbeatFrameCheckpoint.sameVisibleContact(before, after));
        assertFalse(HeartbeatFrameCheckpoint.samePresentation(before, after));
        assertTrue(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
    }

    @Test
    public void addRemoveStillChangesTransitionIdentityAfterOrderCanonicalization() {
        HeartbeatSkillPolicy.Candidate alpha = typed(
                "alpha",
                "evidence-alpha",
                "Stable alpha consequence");
        HeartbeatSkillPolicy.Candidate beta = typed(
                "beta",
                "evidence-beta",
                "Stable beta consequence");
        HeartbeatSceneGraph.Frame before = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(alpha),
                true,
                null);
        HeartbeatSceneGraph.Frame after = HeartbeatSceneGraph.build(
                "pulse-b",
                Arrays.asList(beta, alpha),
                true,
                before);

        assertTrue(after.transitionMotionAllowed);
        assertFalse(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
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
        assertFalse(HeartbeatFrameCheckpoint.samePresentation(before, after));
        assertFalse(HeartbeatFrameCheckpoint.sameTransitionState(before, after));
    }
}
