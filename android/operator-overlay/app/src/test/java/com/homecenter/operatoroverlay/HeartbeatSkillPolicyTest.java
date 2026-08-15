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

    @Test
    public void collapsedDescriptionPreservesMaterialOrderExactStatesAndConsequences() {
        String description = HeartbeatSkillPolicy.collapsedContentDescription(
                Arrays.asList(
                        new HeartbeatSkillPolicy.Candidate(
                                "execution-truth", "Execution truth", HeartbeatSkillPolicy.State.ACTIVE,
                                true, "Collapsed UI keeps proof visible"),
                        new HeartbeatSkillPolicy.Candidate(
                                "decorative", "Decorative", HeartbeatSkillPolicy.State.ACTIVE,
                                false, "Must remain dark"),
                        new HeartbeatSkillPolicy.Candidate(
                                "regnet", "Regnet QA", HeartbeatSkillPolicy.State.BLOCKED,
                                false, "UI consumer not wired yet"),
                        new HeartbeatSkillPolicy.Candidate(
                                "REGNET", "Duplicate Regnet", HeartbeatSkillPolicy.State.FAULT,
                                false, "Must dedupe by stable id")));

        assertEquals(
                "2 material skill lights. "
                        + "Skill Execution truth, active. Collapsed UI keeps proof visible. "
                        + "Skill Regnet QA, blocked. UI consumer not wired yet.",
                description);
    }

    @Test
    public void fullConstructorPreservesTypedSourceContractAndLegacyRemainsExplicitlyUntyped() {
        HeartbeatSkillPolicy.Candidate typed = new HeartbeatSkillPolicy.Candidate(
                "fortress-core",
                "Fortress Core",
                "repository_skill",
                "skills/fortress-core/SKILL.md",
                "P0 firewall constrained this pulse",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Kept phone ownership read-only",
                "PR #329 pre-execution plan receipt");
        HeartbeatSkillPolicy.Candidate legacy = new HeartbeatSkillPolicy.Candidate(
                "legacy",
                "Legacy",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Still material but not typed");

        assertEquals("repository_skill", typed.provenanceKind);
        assertEquals("skills/fortress-core/SKILL.md", typed.provenanceLocator);
        assertEquals("P0 firewall constrained this pulse", typed.activationReason);
        assertEquals("PR #329 pre-execution plan receipt", typed.evidenceBoundary);
        assertTrue(HeartbeatSkillPolicy.hasTypedSourceContract(typed));

        assertEquals("", legacy.provenanceKind);
        assertEquals("", legacy.provenanceLocator);
        assertEquals("", legacy.activationReason);
        assertEquals("", legacy.evidenceBoundary);
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(legacy));
        assertTrue(HeartbeatSkillPolicy.isMaterial(legacy));
    }

    @Test
    public void displayReadySelectionRejectsLegacyAndUnknownProvenanceWithoutInventingEvidence() {
        HeartbeatSkillPolicy.Candidate typed = new HeartbeatSkillPolicy.Candidate(
                "execution-truth",
                "Execution Truth",
                "repository_skill",
                "skills/execution-truth/SKILL.md",
                "Capability-state truth is material",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Prevented source from becoming deployed",
                "Exact branch readback");
        HeartbeatSkillPolicy.Candidate legacy = new HeartbeatSkillPolicy.Candidate(
                "legacy",
                "Legacy",
                HeartbeatSkillPolicy.State.FAULT,
                false,
                "Material fault with no typed provenance");
        HeartbeatSkillPolicy.Candidate invented = new HeartbeatSkillPolicy.Candidate(
                "invented",
                "Invented",
                "mystical_skill",
                "skills/invented/SKILL.md",
                "Looks authoritative",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Must not cross the display gate",
                "No valid provenance");

        List<HeartbeatSkillPolicy.Candidate> selected =
                HeartbeatSkillPolicy.selectDisplayReadyLights(Arrays.asList(typed, legacy, invented));

        assertEquals(1, selected.size());
        assertEquals("execution-truth", selected.get(0).id);
    }

    @Test
    public void typedSourceContractRejectsUnknownProvenanceKindAndMissingCoreIdentity() {
        HeartbeatSkillPolicy.Candidate invented = new HeartbeatSkillPolicy.Candidate(
                "fake-skill",
                "Fake skill",
                "mystical_skill",
                "skills/fake/SKILL.md",
                "Looks impressive",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Should not earn typed provenance",
                "No authoritative source");
        HeartbeatSkillPolicy.Candidate missingId = new HeartbeatSkillPolicy.Candidate(
                "",
                "Missing identity",
                "repository_skill",
                "skills/missing/SKILL.md",
                "Should fail closed",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Exact blocker",
                "Receipt");

        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(invented));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(missingId));
    }

    @Test
    public void detailDescriptionCarriesReasonConsequenceEvidenceAndSource() {
        HeartbeatSkillPolicy.Candidate typed = new HeartbeatSkillPolicy.Candidate(
                "execution-truth",
                "Execution Truth",
                "repository_skill",
                "skills/execution-truth/SKILL.md",
                "Capability labels are material",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Prevented source from being called deployed",
                "Exact GitHub branch readback");

        assertEquals(
                "Skill Execution Truth, active. Why: Capability labels are material. "
                        + "Consequence: Prevented source from being called deployed. "
                        + "Evidence: Exact GitHub branch readback. "
                        + "Source: repository skill skills/execution-truth/SKILL.md.",
                HeartbeatSkillPolicy.detailContentDescription(typed));
    }

    @Test
    public void legacyDetailDescriptionDoesNotInventMissingProvenance() {
        HeartbeatSkillPolicy.Candidate legacy = new HeartbeatSkillPolicy.Candidate(
                "regnet",
                "Regnet QA",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Deterministic suite did not execute");

        assertEquals(
                HeartbeatSkillPolicy.contentDescription(legacy),
                HeartbeatSkillPolicy.detailContentDescription(legacy));
    }
}
