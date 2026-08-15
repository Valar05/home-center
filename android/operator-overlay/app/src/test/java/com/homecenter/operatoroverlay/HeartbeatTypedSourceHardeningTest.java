package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/** Source-only regressions for the typed heartbeat contract and parser-to-scene seam. */
public class HeartbeatTypedSourceHardeningTest {
    @Test
    public void canonicalEnvelopeRejectsUnknownRootMember() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                "{\"schema\":\"heartbeat-skill-lights.v1\","
                        + "\"pulseId\":\"pulse-root-typo\","
                        + "\"complete\":true,\"lights\":[],"
                        + "\"deployed\":true}");

        assertFalse(result.accepted());
        assertEquals("Heartbeat envelope has unknown field: deployed.", result.boundary);
    }

    @Test
    public void canonicalEnvelopeRejectsUnknownLightMember() {
        String payload = envelope(
                "pulse-light-typo",
                light(
                        "execution-truth",
                        "Execution Truth",
                        "repository_skill",
                        "skills/execution-truth/SKILL.md",
                        "Capability state must remain exact.",
                        "blocked",
                        false,
                        "Runtime rendering is still absent.",
                        "Exact source-only boundary",
                        ",\"uiRendered\":true"));

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(payload);

        assertFalse(result.accepted());
        assertEquals("Light 0 has unknown field: uiRendered.", result.boundary);
    }

    @Test
    public void repositorySkillProvenanceRequiresExactSkillFileShape() {
        assertTrue(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "skills/execution-truth/SKILL.md")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "docs/execution-truth/SKILL.md")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "skills/../execution-truth/SKILL.md")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "skills\\execution-truth\\SKILL.md")));
        assertFalse(HeartbeatSkillPolicy.hasTypedSourceContract(candidate(
                "skills/execution-truth/README.md")));
    }

    @Test
    public void rejectedParserResultPreservesLastGoodSceneAndExactBoundary() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(new HeartbeatSkillPolicy.Candidate(
                        "contact-preservation",
                        "Contact Preservation",
                        "doctrine",
                        "Contact Preservation",
                        "Last-good contact is material.",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Last-good heartbeat remains readable.",
                        "Exact source fixture")),
                true,
                null);

        HeartbeatEnvelopeParser.Result rejected = HeartbeatEnvelopeParser.parse(
                "{\"schema\":\"heartbeat-skill-lights.v1\","
                        + "\"pulseId\":\"pulse-bad\","
                        + "\"complete\":true,\"lights\":[],"
                        + "\"accepted\":true}");
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(rejected, lastGood);

        assertTrue(frame.refreshInterrupted);
        assertEquals("pulse-good", frame.visiblePulseId);
        assertEquals("", frame.attemptedPulseId);
        assertEquals("Heartbeat envelope has unknown field: accepted.", frame.refreshBoundary);
        assertSame(lastGood.nodes.get(0), frame.nodes.get(0));
        assertFalse(frame.transitionMotionAllowed);
    }

    @Test
    public void acceptedParserResultComposesIntoSemanticSceneWithoutRuntimeClaim() {
        HeartbeatEnvelopeParser.Result parsed = HeartbeatEnvelopeParser.parse(
                envelope(
                        "pulse-composed",
                        light(
                                "execution-truth",
                                "Execution Truth",
                                "repository_skill",
                                "skills/execution-truth/SKILL.md",
                                "Source parsing is materially composed.",
                                "active",
                                true,
                                "Parser output now feeds the pure semantic scene.",
                                "Source-only composition fixture",
                                "")));

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(parsed, null);

        assertTrue(parsed.accepted());
        assertFalse(frame.refreshInterrupted);
        assertEquals("pulse-composed", frame.visiblePulseId);
        assertEquals(1, frame.nodes.size());
        assertEquals("execution-truth", frame.nodes.get(0).id);
        assertEquals("Source-only composition fixture", frame.nodes.get(0).evidenceBoundary);
        assertTrue(frame.transitionMotionAllowed);
    }

    private static HeartbeatSkillPolicy.Candidate candidate(String locator) {
        return new HeartbeatSkillPolicy.Candidate(
                "execution-truth",
                "Execution Truth",
                "repository_skill",
                locator,
                "Provenance truth is material.",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Malformed repository-skill locators stay out of display-ready state.",
                "Source contract fixture");
    }

    private static String envelope(String pulseId, String light) {
        return "{\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"" + pulseId + "\","
                + "\"complete\":true,\"lights\":[" + light + "]}";
    }

    private static String light(
            String id,
            String label,
            String provenanceKind,
            String provenanceLocator,
            String activationReason,
            String state,
            boolean changedThisPulse,
            String consequence,
            String evidenceBoundary,
            String extraMember) {
        return "{"
                + field("id", id) + ","
                + field("label", label) + ","
                + field("provenanceKind", provenanceKind) + ","
                + field("provenanceLocator", provenanceLocator) + ","
                + field("activationReason", activationReason) + ","
                + field("state", state) + ","
                + "\"changedThisPulse\":" + changedThisPulse + ","
                + field("consequence", consequence) + ","
                + field("evidenceBoundary", evidenceBoundary)
                + extraMember
                + "}";
    }

    private static String field(String name, String value) {
        return "\"" + name + "\":\"" + escape(value) + "\"";
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
