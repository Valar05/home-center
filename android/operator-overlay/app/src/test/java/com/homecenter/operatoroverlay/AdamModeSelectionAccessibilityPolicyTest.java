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

    @Test(expected = IllegalArgumentException.class)
    public void unknownModeFailsClosed() {
        AdamModeSelectionAccessibilityPolicy.requireMode("office-carpet");
    }
}
