package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class AdamSendAvailabilityAccessibilityPolicyTest {
    private static final class CountingCharSequence implements CharSequence {
        private final String value;
        int lengthCalls;
        int charAtCalls;
        int toStringCalls;

        CountingCharSequence(String value) {
            this.value = value;
        }

        @Override
        public int length() {
            lengthCalls++;
            return value.length();
        }

        @Override
        public char charAt(int index) {
            charAtCalls++;
            return value.charAt(index);
        }

        @Override
        public CharSequence subSequence(int start, int end) {
            return value.subSequence(start, end);
        }

        @Override
        public String toString() {
            toStringCalls++;
            return value;
        }
    }

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

    @Test
    public void admittedMaterialScanIsBoundedAndNeverMaterializesWholeSource() {
        CountingCharSequence hostile = new CountingCharSequence("   xignored");

        assertTrue(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(hostile));
        assertEquals(1, hostile.lengthCalls);
        assertEquals(4, hostile.charAtCalls);
        assertEquals(0, hostile.toStringCalls);
    }

    @Test
    public void admittedWhitespaceScanIsBoundedAndNeverMaterializesWholeSource() {
        CountingCharSequence hostile = new CountingCharSequence(" \t\r\n");

        assertFalse(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(hostile));
        assertEquals(1, hostile.lengthCalls);
        assertEquals(4, hostile.charAtCalls);
        assertEquals(0, hostile.toStringCalls);
    }

    @Test
    public void exactBroadSourceCeilingStillReachesExistingTrimSemantics() {
        StringBuilder source = new StringBuilder(
                AdamSendAvailabilityAccessibilityPolicy.MAX_REQUEST_SOURCE_CODE_UNITS);
        for (int index = 0;
                index < AdamSendAvailabilityAccessibilityPolicy.MAX_REQUEST_SOURCE_CODE_UNITS - 1;
                index++) {
            source.append(' ');
        }
        source.append('x');

        assertTrue(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(source));
    }

    @Test
    public void maxPlusOneStopsBeforeElementReadsOrWholeSourceMaterialization() {
        StringBuilder source = new StringBuilder(
                AdamSendAvailabilityAccessibilityPolicy.MAX_REQUEST_SOURCE_CODE_UNITS + 1);
        for (int index = 0;
                index < AdamSendAvailabilityAccessibilityPolicy.MAX_REQUEST_SOURCE_CODE_UNITS + 1;
                index++) {
            source.append('x');
        }
        CountingCharSequence hostile = new CountingCharSequence(source.toString());

        assertFalse(AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(hostile));
        assertEquals(1, hostile.lengthCalls);
        assertEquals(0, hostile.charAtCalls);
        assertEquals(0, hostile.toStringCalls);
    }

    @Test(expected = IllegalArgumentException.class)
    public void invalidModeStillFailsThroughExistingModeAuthority() {
        AdamSendAvailabilityAccessibilityPolicy.decisionFor("CHAT", "hello");
    }
}
