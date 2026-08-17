package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatInvisibleSemanticControlPolicyTest {
    @Test
    public void revealsInvisibleLayoutControlsWithoutRewritingSource() {
        String exact = "Warm\u200BWall Evidence\u2060Boundary \uFEFFHeartbeat";

        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(exact));
        assertEquals(
                "Warm<ZWSP U+200B>Wall Evidence<WJ U+2060>Boundary <BOM U+FEFF>Heartbeat",
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
                "Coder \uD83D\uDC69<ZWJ U+200D>\uD83D\uDCBB",
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(zwjEmoji));
        assertEquals(
                "join<ZWNJ U+200C>test",
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(zwnjLanguageShaping));
    }

    @Test
    public void ordinaryUnicodePassesThroughEvidenceProjectionByteForJavaString() {
        String ordinary = "Warm Wall — swan \uD83E\uDDA2";
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(ordinary));
        assertEquals(ordinary, HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(ordinary));
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
