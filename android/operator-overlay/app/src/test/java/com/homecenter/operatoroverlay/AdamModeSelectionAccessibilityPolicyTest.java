package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class AdamModeSelectionAccessibilityPolicyTest {
    @Test
    public void terminalIsExactlyOnePersistentSelectionByDefault() {
        assertEquals(1, AdamModeSelectionAccessibilityPolicy.selectedCount("terminal"));
        AdamModeSelectionAccessibilityPolicy.Decision terminal =
                AdamModeSelectionAccessibilityPolicy.decisionFor("terminal", "terminal");
        AdamModeSelectionAccessibilityPolicy.Decision chat =
                AdamModeSelectionAccessibilityPolicy.decisionFor("terminal", "chat");

        assertTrue(terminal.persistentOneOfMany);
        assertTrue(terminal.selected);
        assertEquals("Use Adam Terminal mode", terminal.actionDescription);

        assertFalse(chat.selected);
        assertEquals("Use Adam Chat mode", chat.actionDescription);
    }

    @Test
    public void canonicalOrderProvidesStableOneBasedSetPositions() {
        assertEquals(5, AdamModeSelectionAccessibilityPolicy.SET_SIZE);
        int expectedPosition = 1;
        for (AdamModeSelectionAccessibilityPolicy.Mode mode
                : AdamModeSelectionAccessibilityPolicy.Mode.values()) {
            AdamModeSelectionAccessibilityPolicy.Decision decision =
                    AdamModeSelectionAccessibilityPolicy.decisionFor("terminal", mode.wireValue);
            assertEquals(expectedPosition, decision.positionInSet);
            assertEquals(AdamModeSelectionAccessibilityPolicy.SET_SIZE, decision.setSize);
            expectedPosition++;
        }
    }

    @Test
    public void selectionDoesNotOwnKeyboardOrAccessibilityFocus() {
        AdamModeSelectionAccessibilityPolicy.Decision decision =
                AdamModeSelectionAccessibilityPolicy.decisionFor("vlad", "vlad");
        assertFalse(decision.selectionOwnsKeyboardFocus);
        assertFalse(decision.selectionOwnsAccessibilityFocus);
    }

    @Test
    public void everyCanonicalModeRoundTrips() {
        for (AdamModeSelectionAccessibilityPolicy.Mode mode
                : AdamModeSelectionAccessibilityPolicy.Mode.values()) {
            assertEquals(mode,
                    AdamModeSelectionAccessibilityPolicy.requireMode(mode.wireValue));
            assertEquals(1,
                    AdamModeSelectionAccessibilityPolicy.selectedCount(mode.wireValue));
        }
    }

    @Test
    public void modeSourceWorkThroatRejectsMaxPlusOneWithoutNormalization() {
        StringBuilder max = new StringBuilder();
        for (int i = 0; i < AdamModeSelectionAccessibilityPolicy.MAX_MODE_SOURCE_CODE_UNITS; i++) {
            max.append('x');
        }
        try {
            AdamModeSelectionAccessibilityPolicy.requireMode(max.toString());
        } catch (IllegalArgumentException expectedUnknownAtExactCeiling) {
            assertEquals("unsupported Adam mode", expectedUnknownAtExactCeiling.getMessage());
        }

        max.append('x');
        try {
            AdamModeSelectionAccessibilityPolicy.requireMode(max.toString());
        } catch (IllegalArgumentException expectedOverBudget) {
            assertEquals(
                    "Adam mode source exceeds finite work budget",
                    expectedOverBudget.getMessage());
            return;
        }
        throw new AssertionError("max+1 Adam mode source must fail closed");
    }

    @Test(expected = IllegalArgumentException.class)
    public void nullModeFailsClosed() {
        AdamModeSelectionAccessibilityPolicy.requireMode(null);
    }

    @Test(expected = IllegalArgumentException.class)
    public void whitespaceModeDoesNotNormalizeIntoAuthority() {
        AdamModeSelectionAccessibilityPolicy.requireMode(" terminal ");
    }

    @Test(expected = IllegalArgumentException.class)
    public void caseDriftDoesNotNormalizeIntoAuthority() {
        AdamModeSelectionAccessibilityPolicy.requireMode("TERMINAL");
    }

    @Test(expected = IllegalArgumentException.class)
    public void unknownModeFailsClosed() {
        AdamModeSelectionAccessibilityPolicy.requireMode("office-carpet");
    }
}
