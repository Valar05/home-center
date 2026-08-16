package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

public class HeartbeatDirectionalControlSafetyTest {
    @Test
    public void typedSourceContractRejectsDirectionalOverrideButAllowsZwj() {
        HeartbeatSkillPolicy.Candidate spoofed = candidate("Warm\u202EWall");
        HeartbeatSkillPolicy.Candidate joinedEmoji = candidate(
                "Coder \uD83D\uDC69\u200D\uD83D\uDCBB");

        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(spoofed));
        assertEquals("", HeartbeatSkillPolicy.contentDescription(spoofed));
        assertTrue(HeartbeatSkillPolicy.hasTypedSourceContract(joinedEmoji));
        assertFalse(HeartbeatSkillPolicy.contentDescription(joinedEmoji).isEmpty());
    }

    @Test
    public void canonicalParserFailsClosedWhenLabelContainsRlo() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-rlo", "Warm\u202EWall", "Evidence is ordinary text."));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("label contains a bidi-direction control"));
    }

    @Test
    public void canonicalParserFailsClosedWhenEvidenceContainsDirectionalIsolate() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-isolate", "Warm Wall", "Evidence \u2066spoof\u2069"));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("evidenceBoundary contains a bidi-direction control"));
    }

    @Test
    public void canonicalParserRejectsDirectionalPulseIdentityBeforeSceneConstruction() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-\u202Eevil", "Warm Wall", "Evidence is ordinary text."));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("pulseId contains a bidi-direction control"));
    }

    @Test
    public void protocolStateTokenRejectsDirectionalIsolate() {
        String json = envelope("pulse-state", "Warm Wall", "Evidence is ordinary text.")
                .replace("\"state\":\"active\"", "\"state\":\"active\u2066\"");

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(json);

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("state contains a bidi-direction control"));
    }

    @Test
    public void sceneDefenseInDepthRejectsSpoofedDirectPulseIdentityWithoutLeakingAttemptedText() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(candidate("Warm Wall")),
                true,
                null);
        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "pulse-\u202Eevil",
                Collections.singletonList(candidate("Warm Wall")),
                true,
                lastGood);

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("", rejected.attemptedPulseId);
        assertTrue(rejected.refreshBoundary.contains("bidi-direction control"));
        assertFalse(rejected.transitionMotionAllowed);
        assertFalse(rejected.nodes.get(0).transitionMotion);
        assertEquals(
                HeartbeatFrameCheckpoint.contactSha256(lastGood),
                HeartbeatFrameCheckpoint.contactSha256(rejected));
    }

    @Test
    public void validZwjAndSupplementaryUnicodeRemainSemanticData() {
        String label = "Coder \uD83D\uDC69\u200D\uD83D\uDCBB and swan \uD83E\uDDA2";
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-unicode", label, "Unicode remains inert evidence."));

        assertTrue(result.accepted());
        assertEquals(label, result.pulse.candidates.get(0).label);
    }

    private static HeartbeatSkillPolicy.Candidate candidate(String label) {
        return new HeartbeatSkillPolicy.Candidate(
                "warm-wall",
                label,
                "doctrine",
                "Warm Walls",
                "Directional text safety is material to touch and speech semantics.",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Canonical semantic text stays readable without rewriting legitimate Unicode.",
                "Pure source regression fixture.");
    }

    private static String envelope(String pulseId, String label, String evidence) {
        return "{"
                + "\"schema\":\"" + HeartbeatEnvelopeParser.SCHEMA + "\","
                + "\"pulseId\":\"" + escape(pulseId) + "\","
                + "\"complete\":true,"
                + "\"lights\":[{"
                + "\"id\":\"warm-wall\","
                + "\"label\":\"" + escape(label) + "\","
                + "\"provenanceKind\":\"doctrine\","
                + "\"provenanceLocator\":\"Warm Walls\","
                + "\"activationReason\":\"Directional text safety is material.\","
                + "\"state\":\"active\","
                + "\"changedThisPulse\":true,"
                + "\"consequence\":\"Canonical semantic text remains inert and readable.\","
                + "\"evidenceBoundary\":\"" + escape(evidence) + "\""
                + "}]}";
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
