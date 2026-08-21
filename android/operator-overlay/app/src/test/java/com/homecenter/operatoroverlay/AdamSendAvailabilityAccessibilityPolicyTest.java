package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class AdamSendAvailabilityAccessibilityPolicyTest {
    @Test
    public void emptyRequestDisablesNativeSendInsteadOfInventingAnnouncement() {
        AdamSendAvailabilityAccessibilityPolicy.Decision decision =
                AdamSendAvailabilityAccessibilityPolicy.decisionFor("terminal", "   ");

        assertFalse(decision.enabled);
        assertEquals("Send", decision.visibleLabel);
        assertEquals(
                "Send request to Adam using Terminal mode",
                decision.actionDescription);
        assertFalse(decision.requiresSyntheticAnnouncement);
    }

    @Test
    public void materialRequestEnablesExactModeAction() {
        AdamSendAvailabilityAccessibilityPolicy.Decision decision =
                AdamSendAvailabilityAccessibilityPolicy.decisionFor(
                        "vlad",
                        "  inspect this boundary  ");

        assertTrue(decision.enabled);
        assertEquals(
                AdamModeSelectionAccessibilityPolicy.Mode.VLAD,
                decision.mode);
        assertEquals(
                "Send request to Adam using Vlad mode",
                decision.actionDescription);
        assertFalse(decision.requiresSyntheticAnnouncement);
    }

    @Test
    public void nullAndAsciiWhitespaceMatchCurrentOwnerAdmission() {
        assertFalse(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(null));
        assertFalse(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(""));
        assertFalse(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(" \t\r\n"));
        assertTrue(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(" x "));
    }

    @Test
    public void nonAsciiSpaceDoesNotSilentlyBroadenCurrentOwnerTrimContract() {
        String emSpace = "\u2003";
        assertTrue(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(emSpace));
    }

    @Test(expected = IllegalArgumentException.class)
    public void invalidModeStillFailsThroughExistingModeAuthority() {
        AdamSendAvailabilityAccessibilityPolicy.decisionFor("CHAT", "hello");
    }
}
