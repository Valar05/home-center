package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.AbstractList;
import java.util.Collections;
import java.util.List;

import org.junit.Test;

/**
 * Source regression for bounded direct HeartbeatSceneGraph candidate observation.
 *
 * SOURCE / UNEXECUTED until an authorized regression lane actually runs it.
 */
public class HeartbeatDirectSceneCandidateSnapshotTest {
    private static HeartbeatSkillPolicy.Candidate active(String id) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "doctrine",
                "test-doctrine:" + id,
                "Direct scene snapshot regression",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Material consequence " + id,
                "Exact source fixture");
    }

    private static final class CountingCandidates
            extends AbstractList<HeartbeatSkillPolicy.Candidate> {
        private final int declaredSize;
        int sizeCalls;
        int getCalls;

        CountingCandidates(int declaredSize) {
            this.declaredSize = declaredSize;
        }

        @Override
        public int size() {
            sizeCalls++;
            return declaredSize;
        }

        @Override
        public HeartbeatSkillPolicy.Candidate get(int index) {
            getCalls++;
            return active("light-" + index);
        }
    }

    @Test
    public void maxPlusOneRejectsAfterOneSizeObservationWithoutElementReads() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(active("contact")),
                true,
                null);
        CountingCandidates hostile = new CountingCandidates(HeartbeatEnvelopeParser.MAX_LIGHTS + 1);

        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "pulse-too-many",
                hostile,
                true,
                lastGood);

        assertEquals(1, hostile.sizeCalls);
        assertEquals(0, hostile.getCalls);
        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("contact", rejected.nodes.get(0).id);
        assertFalse(rejected.transitionMotionAllowed);
        assertFalse(rejected.nodes.get(0).transitionMotion);
        assertTrue(rejected.refreshBoundary.contains("exceeds 64 lights"));
    }

    @Test
    public void exactMaximumUsesOneSizeObservationAndAtMostSixtyFourIndexedReads() {
        CountingCandidates admitted = new CountingCandidates(HeartbeatEnvelopeParser.MAX_LIGHTS);

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-max",
                admitted,
                true,
                null);

        assertEquals(1, admitted.sizeCalls);
        assertEquals(HeartbeatEnvelopeParser.MAX_LIGHTS, admitted.getCalls);
        assertFalse(frame.refreshInterrupted);
        assertEquals(HeartbeatEnvelopeParser.MAX_LIGHTS, frame.nodes.size());
        assertFalse(frame.refreshBoundary.length() > 0);
    }
}
