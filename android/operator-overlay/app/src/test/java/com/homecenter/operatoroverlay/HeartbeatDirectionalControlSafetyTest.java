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
    public void directCandidateCannotHideEdgeControlThroughConstructorTrim() {
        HeartbeatSkillPolicy.Candidate candidate = candidate("\tWarm Wall");

        assertEquals("Warm Wall", candidate.label);
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate));
        assertEquals("", HeartbeatSkillPolicy.contentDescription(candidate));
    }

    @Test
    public void legacyCollapsedSpeechReportsUnsafeOmissionInsteadOfLyingAboutNamedCount() {
        String description = HeartbeatSkillPolicy.collapsedContentDescription(
                Collections.singletonList(candidate("Warm\u202EWall")));

        assertEquals(
                "1 material light was omitted from speech because its semantic text was rejected.",
                description);
        assertFalse(description.contains("Warm"));
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
    public void unknownDirectionalMemberNameIsNotEchoedIntoParserBoundary() {
        String rlo = String.valueOf((char) 0x202E);
        String base = envelope("pulse-member", "Warm Wall", "Evidence is ordinary text.");
        String json = base.substring(0, base.length() - 1)
                + ",\"bad" + rlo + "key\":true}";

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(json);

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("<unsafe member name>"));
        assertFalse(result.boundary.contains(rlo));
    }

    @Test
    public void duplicateDirectionalMemberNameIsNotEchoedIntoParserBoundary() {
        String rlo = String.valueOf((char) 0x202E);
        String key = "bad" + rlo + "key";
        String json = "{\"" + key + "\":1,\"" + key + "\":2}";

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(json);

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("Duplicate JSON member: <unsafe member name>."));
        assertFalse(result.boundary.contains(rlo));
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
    public void preParserPreservationSuppressesUnsafeAttemptedIdentityButKeepsExactBoundary() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(candidate("Warm Wall")),
                true,
                null);
        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.preserveRejectedRefresh(
                "persisted-\u202Eevil",
                lastGood,
                "Stored heartbeat SHA-256 mismatch.");

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("", rejected.attemptedPulseId);
        assertEquals("Stored heartbeat SHA-256 mismatch.", rejected.refreshBoundary);
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
