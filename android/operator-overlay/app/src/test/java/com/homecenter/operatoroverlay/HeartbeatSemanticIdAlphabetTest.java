package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;
import java.util.Locale;

import org.junit.Test;

/**
 * Regression source for one semantic-id equivalence relation across parser, scene,
 * native ownership, selection, checkpoint, and viewport policy.
 */
public class HeartbeatSemanticIdAlphabetTest {
    private static HeartbeatSkillPolicy.Candidate typed(String id) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                "Semantic identity",
                "doctrine",
                "semantic-id-boundary",
                "One source id must name one deterministic UI owner",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Mixed Unicode case equivalence must not alias native controls",
                "Typed semantic-id boundary");
    }

    @Test
    public void asciiMachineTokensRemainAcceptedIncludingLegacyCaseDrift() {
        assertTrue(HeartbeatSkillPolicy.isDeterministicSemanticId("regnet-qa/v1:source_7"));
        assertTrue(HeartbeatSkillPolicy.isDeterministicSemanticId("Regnet-QA/V1:SOURCE_7"));
        assertTrue(HeartbeatSkillPolicy.hasTypedSourceContract(typed("Regnet-QA/V1:SOURCE_7")));
    }

    @Test
    public void unicodeIdentityWhoseCaseRelationsDisagreeIsRejectedAtTypedBoundary() {
        String dottedCapitalI = "\u0130";
        assertTrue(dottedCapitalI.equalsIgnoreCase("i"));
        assertFalse(dottedCapitalI.toLowerCase(Locale.ROOT)
                .equals("i".toLowerCase(Locale.ROOT)));

        assertFalse(HeartbeatSkillPolicy.isDeterministicSemanticId(dottedCapitalI + "d"));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(typed(dottedCapitalI + "d")));
    }

    @Test
    public void unicodeConfusableCannotBecomeDisplayReadyIdentity() {
        String cyrillicSmallIe = "\u0435";
        HeartbeatSkillPolicy.Candidate confusable = typed("r" + cyrillicSmallIe + "gnet");

        assertTrue(HeartbeatSkillPolicy.isSafeSemanticText(confusable.id));
        assertFalse(HeartbeatSkillPolicy.isDeterministicSemanticId(confusable.id));
        assertTrue(HeartbeatSkillPolicy.selectDisplayReadyLights(
                Collections.singletonList(confusable)).isEmpty());
    }

    @Test
    public void canonicalParserRejectsNonAsciiMachineIdentity() {
        String payload = "{"
                + "\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"pulse-id-alphabet\","
                + "\"complete\":true,"
                + "\"lights\":[{"
                + "\"id\":\"\u0130d\","
                + "\"label\":\"Unicode label stays legal 🦢\","
                + "\"provenanceKind\":\"doctrine\","
                + "\"provenanceLocator\":\"semantic-id-boundary\","
                + "\"activationReason\":\"Identity ownership must be deterministic\","
                + "\"state\":\"blocked\","
                + "\"changedThisPulse\":false,"
                + "\"consequence\":\"Reject an ambiguous machine id\","
                + "\"evidenceBoundary\":\"Typed id alphabet\""
                + "}]}";

        HeartbeatEnvelopeParser.Result parsed = HeartbeatEnvelopeParser.parse(payload);

        assertFalse(parsed.accepted());
        assertTrue(parsed.boundary.contains("lacks the complete typed source contract"));
    }

    @Test
    public void directSourceAttemptWithUnicodeIdPreservesLastGoodContact() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(typed("regnet")),
                true,
                null);
        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "pulse-unicode-id",
                Collections.singletonList(typed("\u0130d")),
                true,
                lastGood);

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals(1, rejected.nodes.size());
        assertEquals("regnet", rejected.nodes.get(0).id);
        assertTrue(rejected.refreshBoundary.contains("typed source/evidence contract"));
        assertFalse(rejected.transitionMotionAllowed);
    }
}
