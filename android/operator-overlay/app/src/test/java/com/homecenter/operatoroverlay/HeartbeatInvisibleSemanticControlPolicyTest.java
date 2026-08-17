package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatInvisibleSemanticControlPolicyTest {
    @Test
    public void rejectsInvisiblePresentationAliases() {
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsForbiddenInvisibleControl(
                "Warm\u200BWall"));
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsForbiddenInvisibleControl(
                "Evidence\u2060Boundary"));
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsForbiddenInvisibleControl(
                "\uFEFFHeartbeat"));

        assertFalse(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(
                "Warm\u200BWall"));
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(
                "Evidence\u2060Boundary"));
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(
                "\uFEFFHeartbeat"));
    }

    @Test
    public void preservesLegitimateJoinersAndOrdinaryUnicode() {
        String zwjEmoji = "Coder \uD83D\uDC69\u200D\uD83D\uDCBB";
        String zwnjLanguageShaping = "join\u200Ctest";
        String supplementary = "swan \uD83E\uDDA2";

        assertFalse(HeartbeatInvisibleSemanticControlPolicy.containsForbiddenInvisibleControl(zwjEmoji));
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.containsForbiddenInvisibleControl(zwnjLanguageShaping));
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.containsForbiddenInvisibleControl(supplementary));

        assertTrue(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(zwjEmoji));
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(zwnjLanguageShaping));
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(supplementary));
    }

    @Test
    public void composesWithExistingBidiAndControlSafetyInsteadOfReplacingIt() {
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(
                "Warm\u202EWall"));
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(
                "\tWarm Wall"));
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(
                "Warm Wall"));
    }

    @Test
    public void policyNeverNormalizesPoisonIntoAcceptedText() {
        String poisoned = "Reg\u200Bnet";
        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsForbiddenInvisibleControl(poisoned));
        assertFalse(HeartbeatInvisibleSemanticControlPolicy.isSafeOperatorSemanticText(poisoned));
        assertTrue(poisoned.contains("\u200B"));
    }
}
