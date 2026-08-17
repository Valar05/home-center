package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/** Source-only regressions keeping direct Candidate ingress aligned with parser bounds. */
public class HeartbeatDirectSourceBoundsParityTest {
    @Test
    public void directTypedCandidateUsesCanonicalParserFieldBounds() {
        HeartbeatSkillPolicy.Candidate atBounds = candidate(
                repeat("a", HeartbeatEnvelopeParser.MAX_ID_CHARS),
                repeat("L", HeartbeatEnvelopeParser.MAX_LABEL_CHARS),
                repeat("p", HeartbeatEnvelopeParser.MAX_PROVENANCE_LOCATOR_CHARS),
                repeat("r", HeartbeatEnvelopeParser.MAX_ACTIVATION_REASON_CHARS),
                repeat("c", HeartbeatEnvelopeParser.MAX_CONSEQUENCE_CHARS),
                repeat("e", HeartbeatEnvelopeParser.MAX_EVIDENCE_BOUNDARY_CHARS));

        assertTrue(HeartbeatSkillPolicy.hasTypedSourceContract(atBounds));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                repeat("a", HeartbeatEnvelopeParser.MAX_ID_CHARS + 1),
                "Label", "source", "reason", "consequence", "evidence")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "id", repeat("L", HeartbeatEnvelopeParser.MAX_LABEL_CHARS + 1),
                "source", "reason", "consequence", "evidence")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "id", "Label",
                repeat("p", HeartbeatEnvelopeParser.MAX_PROVENANCE_LOCATOR_CHARS + 1),
                "reason", "consequence", "evidence")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "id", "Label", "source",
                repeat("r", HeartbeatEnvelopeParser.MAX_ACTIVATION_REASON_CHARS + 1),
                "consequence", "evidence")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "id", "Label", "source", "reason",
                repeat("c", HeartbeatEnvelopeParser.MAX_CONSEQUENCE_CHARS + 1),
                "evidence")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "id", "Label", "source", "reason", "consequence",
                repeat("e", HeartbeatEnvelopeParser.MAX_EVIDENCE_BOUNDARY_CHARS + 1))));
    }

    @Test
    public void oversizedDirectCandidateFailsClosedAndPreservesLastGoodContact() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(candidate(
                        "contact-preservation",
                        "Contact Preservation",
                        "doctrine",
                        "last-good contact",
                        "Last-good contact remains readable.",
                        "Exact source fixture")),
                true,
                null);

        HeartbeatSkillPolicy.Candidate oversized = candidate(
                "oversized-direct-source",
                repeat("L", HeartbeatEnvelopeParser.MAX_LABEL_CHARS + 1),
                "doctrine",
                "direct source bypass attempt",
                "Oversized direct source must not enter the scene.",
                "Direct source bound parity fixture");

        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "pulse-oversized",
                Collections.singletonList(oversized),
                true,
                lastGood);

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("pulse-oversized", rejected.attemptedPulseId);
        assertEquals(
                "At least one material light lacks the complete typed source/evidence contract.",
                rejected.refreshBoundary);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, rejected));
        assertFalse(rejected.transitionMotionAllowed);
        assertFalse(rejected.nodes.get(0).transitionMotion);
    }

    private static HeartbeatSkillPolicy.Candidate candidate(
            String id,
            String label,
            String provenanceLocator,
            String activationReason,
            String consequence,
            String evidenceBoundary) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                label,
                "doctrine",
                provenanceLocator,
                activationReason,
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                consequence,
                evidenceBoundary);
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder(value.length() * count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}