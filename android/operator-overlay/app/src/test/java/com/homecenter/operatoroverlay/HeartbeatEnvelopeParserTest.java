package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatEnvelopeParserTest {
    @Test
    public void canonicalTypedEnvelopeParsesIntoCandidates() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope(
                        "pulse-1",
                        "true",
                        light(
                                "execution-truth",
                                "Execution Truth",
                                "repository_skill",
                                "skills/execution-truth/SKILL.md",
                                "Source progress needs capability truth.",
                                "active",
                                "true",
                                "Source mutation is separated from runtime proof.",
                                "GitHub branch readback.")));

        assertTrue(result.accepted());
        assertEquals("pulse-1", result.pulse.pulseId);
        assertTrue(result.pulse.complete);
        assertEquals(1, result.pulse.candidates.size());
        HeartbeatSkillPolicy.Candidate candidate = result.pulse.candidates.get(0);
        assertEquals("execution-truth", candidate.id);
        assertEquals(HeartbeatSkillPolicy.State.ACTIVE, candidate.state);
        assertTrue(HeartbeatSkillPolicy.hasTypedSourceContract(candidate));
    }

    @Test
    public void duplicateLightIdsAreRejectedCaseInsensitively() {
        String first = light(
                "regnet",
                "Regnet QA",
                "repository_skill",
                "skills/renee-qa/SKILL.md",
                "QA is material.",
                "blocked",
                "false",
                "Tests have not executed.",
                "Actions budget boundary.");
        String second = light(
                "REGNET",
                "Regnet duplicate",
                "repository_skill",
                "skills/renee-qa/SKILL.md",
                "Duplicate should fail closed.",
                "blocked",
                "false",
                "Duplicate identity is ambiguous.",
                "Parser duplicate-id boundary.");

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-2", "true", first + "," + second));

        assertFalse(result.accepted());
        assertEquals("Duplicate heartbeat light id: REGNET", result.boundary);
    }

    @Test
    public void activeAndRecoveredRequireRealPulseChange() {
        HeartbeatEnvelopeParser.Result active = HeartbeatEnvelopeParser.parse(
                envelope(
                        "pulse-active",
                        "true",
                        light(
                                "hunger",
                                "Hunger",
                                "doctrine",
                                "Hunger",
                                "Hunger was selected.",
                                "active",
                                "false",
                                "Nothing changed.",
                                "No change receipt.")));
        HeartbeatEnvelopeParser.Result recovered = HeartbeatEnvelopeParser.parse(
                envelope(
                        "pulse-recovered",
                        "true",
                        light(
                                "shovel",
                                "Failure Is The Shovel",
                                "doctrine",
                                "Failure Is The Shovel",
                                "Recovery path changed.",
                                "recovered",
                                "false",
                                "The old failure remains unchanged.",
                                "No changed condition.")));

        assertFalse(active.accepted());
        assertTrue(active.boundary.contains("requires changedThisPulse=true"));
        assertFalse(recovered.accepted());
        assertTrue(recovered.boundary.contains("requires changedThisPulse=true"));
    }

    @Test
    public void unsupportedStateCannotMasqueradeAsLitTelemetry() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope(
                        "pulse-dark",
                        "true",
                        light(
                                "decorative",
                                "Decorative",
                                "doctrine",
                                "Decorative",
                                "Should stay dark.",
                                "dark",
                                "false",
                                "No material consequence.",
                                "Not a light.")));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("unsupported state: dark"));
    }

    @Test
    public void incompleteCanonicalPulseStillParsesButRemainsIncomplete() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope(
                        "pulse-incomplete",
                        "false",
                        light(
                                "contact",
                                "Contact Preservation",
                                "doctrine",
                                "Contact Preservation",
                                "A refresh is underway.",
                                "blocked",
                                "false",
                                "Last-good frame must remain visible.",
                                "Pulse is not complete.")));

        assertTrue(result.accepted());
        assertFalse(result.pulse.complete);
    }

    @Test
    public void duplicateJsonMemberFailsClosed() {
        String payload = "{\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"pulse-a\",\"pulseId\":\"pulse-b\","
                + "\"complete\":true,\"lights\":[]}";

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(payload);

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("Duplicate JSON member: pulseId"));
    }

    @Test
    public void trailingGarbageAndWrongSchemaFailClosed() {
        HeartbeatEnvelopeParser.Result trailing = HeartbeatEnvelopeParser.parse(
                envelope("pulse-3", "true", "") + " garbage");
        HeartbeatEnvelopeParser.Result schema = HeartbeatEnvelopeParser.parse(
                "{\"schema\":\"heartbeat-skill-lights.v2\","
                        + "\"pulseId\":\"pulse-4\",\"complete\":true,\"lights\":[]}");

        assertFalse(trailing.accepted());
        assertTrue(trailing.boundary.contains("Trailing data"));
        assertFalse(schema.accepted());
        assertEquals(
                "Unsupported heartbeat envelope schema: heartbeat-skill-lights.v2",
                schema.boundary);
    }

    @Test
    public void unicodeAndShellLookingTextRemainInertJsonData() {
        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope(
                        "pulse-unicode",
                        "true",
                        light(
                                "jar",
                                "Judgment Jar",
                                "jar",
                                "Autocorrect Judgment Jar",
                                "Keep Drew's text inert: $(touch nope) — 🦢.",
                                "active",
                                "true",
                                "Parser returns text; it executes nothing.",
                                "Pure Java candidate data.")));

        assertTrue(result.accepted());
        assertTrue(result.pulse.candidates.get(0).activationReason.contains("$(touch nope)"));
        assertTrue(result.pulse.candidates.get(0).activationReason.contains("🦢"));
    }

    private static String envelope(String pulseId, String complete, String lights) {
        return "{\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"" + pulseId + "\","
                + "\"complete\":" + complete + ","
                + "\"lights\":[" + lights + "]}";
    }

    private static String light(
            String id,
            String label,
            String provenanceKind,
            String provenanceLocator,
            String activationReason,
            String state,
            String changedThisPulse,
            String consequence,
            String evidenceBoundary) {
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
