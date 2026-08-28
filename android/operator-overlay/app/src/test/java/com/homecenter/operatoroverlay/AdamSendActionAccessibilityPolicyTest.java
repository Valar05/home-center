package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import org.junit.Test;

public class AdamSendActionAccessibilityPolicyTest {
    @Test
    public void sendActionNamesExactCurrentModeWithoutOwningSelectionOrFocus() {
        AdamSendActionAccessibilityPolicy.Decision decision =
                AdamSendActionAccessibilityPolicy.decisionFor("vlad");
        assertEquals("Send", decision.visibleLabel);
        assertEquals("Send request to Adam using Vlad mode", decision.actionDescription);
        assertFalse(decision.actionOwnsSelection);
        assertFalse(decision.actionOwnsKeyboardFocus);
        assertFalse(decision.actionOwnsAccessibilityFocus);
    }

    @Test
    public void eachCanonicalModeProducesDistinctActionConsequence() {
        assertEquals(
                "Send request to Adam using Terminal mode",
                AdamSendActionAccessibilityPolicy.decisionFor("terminal").actionDescription);
        assertEquals(
                "Send request to Adam using Chat mode",
                AdamSendActionAccessibilityPolicy.decisionFor("chat").actionDescription);
        assertEquals(
                "Send request to Adam using Continue mode",
                AdamSendActionAccessibilityPolicy.decisionFor("continue").actionDescription);
        assertEquals(
                "Send request to Adam using Vlad mode",
                AdamSendActionAccessibilityPolicy.decisionFor("vlad").actionDescription);
        assertEquals(
                "Send request to Adam using Radio mode",
                AdamSendActionAccessibilityPolicy.decisionFor("radio").actionDescription);
    }

    @Test(expected = IllegalArgumentException.class)
    public void modeWhitespaceDriftFailsClosed() {
        AdamSendActionAccessibilityPolicy.decisionFor(" chat");
    }

    @Test(expected = IllegalArgumentException.class)
    public void modeCaseDriftFailsClosed() {
        AdamSendActionAccessibilityPolicy.decisionFor("CHAT");
    }
}
