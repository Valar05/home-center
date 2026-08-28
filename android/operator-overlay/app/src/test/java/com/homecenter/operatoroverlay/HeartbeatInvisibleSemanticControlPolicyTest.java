package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatInvisibleSemanticControlPolicyTest {
    @Test
    public void revealsInvisibleLayoutControlsWithoutRewritingSource() {
        String exact = "Warm\u200BWall Evidence\u2060Boundary \uFEFFHeartbeat";

        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(exact));
        assertEquals(
                "Warm\\u{200B ZWSP}Wall Evidence\\u{2060 WJ}Boundary \\u{FEFF BOM}Heartbeat",
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(exact));
        assertTrue(exact.contains("\u200B"));
        assertTrue(exact.contains("\u2060"));
        assertTrue(exact.contains("\uFEFF"));
    }

    @Test
    public void revealsLegitimateJoinersRatherThanCallingThemPoison() {
        String zwjEmoji = "Coder \uD83D\uDC69\u200D\uD83D\uDCBB";
        String zwnjLanguageShaping = "join\u200Ctest";

        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(zwjEmoji));
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(zwnjLanguageShaping));
        assertEquals(
                "Coder \uD83D\uDC69\\u{200D ZWJ}\uD83D\uDCBB",
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(zwjEmoji));
        assertEquals(
                "join\\u{200C ZWNJ}test",
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(zwnjLanguageShaping));
    }

    @Test
    public void ordinaryUnicodePassesThroughEvidenceProjectionExceptReservedBackslash() {
        String ordinary = "Warm Wall — swan \uD83E\uDDA2";
        String literalBackslash = "source\\path";

        assertFalse(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(ordinary));
        assertEquals(ordinary, HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(ordinary));
        assertEquals(
                "source\\\\path",
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(literalBackslash));
    }

    @Test
    public void markerTextCannotAliasActualInvisibleSource() {
        String invisible = "Reg\u200Bnet";
        String literalMarkerText = "Reg\\u{200B ZWSP}net";

        String invisibleProjection =
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(invisible);
        String literalProjection =
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(literalMarkerText);

        assertEquals("Reg\\u{200B ZWSP}net", invisibleProjection);
        assertEquals("Reg\\\\u{200B ZWSP}net", literalProjection);
        assertNotEquals(invisibleProjection, literalProjection);
    }

    @Test
    public void projectionDoesNotReplaceExistingUnsafeSemanticTextGate() {
        String directionalSpoof = "Warm\u202EWall";
        String edgeControl = "\tWarm Wall";

        assertFalse(HeartbeatSkillPolicy.isSafeSemanticText(directionalSpoof));
        assertFalse(HeartbeatSkillPolicy.isSafeSemanticText(edgeControl));
        assertEquals(
                directionalSpoof,
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(directionalSpoof));
        assertEquals(
                edgeControl,
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(edgeControl));
    }
}
