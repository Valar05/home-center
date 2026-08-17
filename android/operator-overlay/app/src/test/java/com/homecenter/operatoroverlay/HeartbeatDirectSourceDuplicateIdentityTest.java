package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class HeartbeatDirectSourceDuplicateIdentityTest {
    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            HeartbeatSkillPolicy.State state,
            boolean changed,
            String consequence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                "Light " + id,
                "doctrine",
                "duplicate-owner-test:" + id,
                "Exercise deterministic semantic ownership",
                state,
                changed,
                consequence,
                "Exact duplicate-owner regression fixture");
    }

    @Test
    public void canonicalParserRejectsCaseInsensitiveDuplicateSemanticOwners() {
        String payload = "{"
                + "\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"pulse-parser-duplicate\","
                + "\"complete\":true,"
                + "\"lights\":["
                + typedJson("regnet", "blocked", false, "First owner") + ","
                + typedJson("REGNET", "fault", false, "Second owner")
                + "]}";

        HeartbeatEnvelopeParser.Result parsed = HeartbeatEnvelopeParser.parse(payload);

        assertFalse(parsed.accepted());
        assertTrue(parsed.boundary.contains("Duplicate heartbeat light id"));
    }

    @Test
    public void directDuplicateMaterialOwnersFailClosedAndPreserveLastGoodContact() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(typed(
                        "contact",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Last-good contact remains visible")),
                true,
                null);

        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "pulse-direct-duplicate",
                Arrays.asList(
                        typed(
                                "regnet",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "First material owner"),
                        typed(
                                "REGNET",
                                HeartbeatSkillPolicy.State.FAULT,
                                false,
                                "Second material owner")),
                true,
                lastGood);

        assertTrue(rejected.refreshInterrupted);
        assertEquals("pulse-good", rejected.visiblePulseId);
        assertEquals("pulse-direct-duplicate", rejected.attemptedPulseId);
        assertEquals("Duplicate material heartbeat light identity is ambiguous.", rejected.refreshBoundary);
        assertEquals(1, rejected.nodes.size());
        assertEquals("contact", rejected.nodes.get(0).id);
        assertFalse(rejected.transitionMotionAllowed);
        assertFalse(rejected.nodes.get(0).transitionMotion);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, rejected));
    }

    @Test
    public void nonMaterialAliasDoesNotInventASecondVisibleOwner() {
        HeartbeatSkillPolicy.Candidate decorative = new HeartbeatSkillPolicy.Candidate(
                "regnet",
                "Decorative Regnet",
                HeartbeatSkillPolicy.State.ACTIVE,
                false,
                "No real change");
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-one-material-owner",
                Arrays.asList(
                        decorative,
                        typed(
                                "REGNET",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                false,
                                "Only material owner")),
                true,
                null);

        assertFalse(accepted.refreshInterrupted);
        assertEquals(1, accepted.nodes.size());
        assertEquals("REGNET", accepted.nodes.get(0).id);
    }

    private static String typedJson(
            String id,
            String state,
            boolean changed,
            String consequence) {
        return "{"
                + "\"id\":\"" + id + "\","
                + "\"label\":\"Light " + id + "\","
                + "\"provenanceKind\":\"doctrine\","
                + "\"provenanceLocator\":\"duplicate-owner-test:" + id + "\","
                + "\"activationReason\":\"Exercise deterministic semantic ownership\","
                + "\"state\":\"" + state + "\","
                + "\"changedThisPulse\":" + changed + ","
                + "\"consequence\":\"" + consequence + "\","
                + "\"evidenceBoundary\":\"Exact duplicate-owner regression fixture\""
                + "}";
    }
}
