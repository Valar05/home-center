package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.List;

import org.junit.Test;

public class HeartbeatSkillPolicyTest {
    @Test
    public void activeLightRequiresRealChangeAndConsequence() {
        HeartbeatSkillPolicy.Candidate changed = new HeartbeatSkillPolicy.Candidate(
                "execution-truth", "Execution truth", HeartbeatSkillPolicy.State.ACTIVE,
                true, "Dispatched audited overlay diagnosis");
        HeartbeatSkillPolicy.Candidate decorative = new HeartbeatSkillPolicy.Candidate(
                "hunger", "Hunger", HeartbeatSkillPolicy.State.ACTIVE,
                false, "Nothing changed");
        HeartbeatSkillPolicy.Candidate empty = new HeartbeatSkillPolicy.Candidate(
                "regnet", "Regnet QA", HeartbeatSkillPolicy.State.ACTIVE,
                true, "   ");

        assertTrue(HeartbeatSkillPolicy.isMaterial(changed));
        assertFalse(HeartbeatSkillPolicy.isMaterial(decorative));
        assertFalse(HeartbeatSkillPolicy.isMaterial(empty));
    }

    @Test
    public void exactFaultBoundaryRemainsVisibleWithoutPretendProgress() {
        HeartbeatSkillPolicy.Candidate fault = new HeartbeatSkillPolicy.Candidate(
                "she-raw", "She-Raw", HeartbeatSkillPolicy.State.FAULT,
                false, "Connector authentication unavailable");
        HeartbeatSkillPolicy.Candidate blocked = new HeartbeatSkillPolicy.Candidate(
                "phone-runtime", "Phone runtime", HeartbeatSkillPolicy.State.BLOCKED,
                false, "No fresh on-device receipt yet");

        assertTrue(HeartbeatSkillPolicy.isMaterial(fault));
        assertTrue(HeartbeatSkillPolicy.isMaterial(blocked));
    }

    @Test
    public void recoveredRequiresChangedCondition() {
        HeartbeatSkillPolicy.Candidate staleRecovery = new HeartbeatSkillPolicy.Candidate(
                "shovel", "Failure Is The Shovel", HeartbeatSkillPolicy.State.RECOVERED,
                false, "Changed recovery route");
        HeartbeatSkillPolicy.Candidate realRecovery = new HeartbeatSkillPolicy.Candidate(
                "shovel", "Failure Is The Shovel", HeartbeatSkillPolicy.State.RECOVERED,
                true, "Changed recovery route");

        assertFalse(HeartbeatSkillPolicy.isMaterial(staleRecovery));
        assertTrue(HeartbeatSkillPolicy.isMaterial(realRecovery));
    }

    @Test
    public void selectionPreservesOrderAndRejectsDuplicateSkillIds() {
        List<HeartbeatSkillPolicy.Candidate> selected = HeartbeatSkillPolicy.selectMaterialLights(
                Arrays.asList(
                        new HeartbeatSkillPolicy.Candidate(
                                "execution-truth", "Execution truth", HeartbeatSkillPolicy.State.ACTIVE,
                                true, "Dispatched diagnosis"),
                        new HeartbeatSkillPolicy.Candidate(
                                "EXECUTION-TRUTH", "Execution truth duplicate", HeartbeatSkillPolicy.State.ACTIVE,
                                true, "Should not render twice"),
                        new HeartbeatSkillPolicy.Candidate(
                                "accessibility", "Accessibility", HeartbeatSkillPolicy.State.ACTIVE,
                                true, "TalkBack semantics defined")));

        assertEquals(2, selected.size());
        assertEquals("execution-truth", selected.get(0).id);
        assertEquals("accessibility", selected.get(1).id);
    }

    @Test
    public void accessibilityDescriptionCarriesStateAndConcreteConsequence() {
        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                "regnet", "Regnet QA", HeartbeatSkillPolicy.State.BLOCKED,
                false, "UI consumer not wired yet");

        assertEquals(
                "Skill Regnet QA, blocked. UI consumer not wired yet.",
                HeartbeatSkillPolicy.contentDescription(candidate));
    }
}
