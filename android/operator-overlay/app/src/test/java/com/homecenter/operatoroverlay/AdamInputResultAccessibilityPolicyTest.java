package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class AdamInputResultAccessibilityPolicyTest {
    @Test
    public void readyStatePreservesEditableValueAndAddsModeContext() {
        AdamInputResultAccessibilityPolicy.Decision decision =
                AdamInputResultAccessibilityPolicy.decisionFor(
                        "continue",
                        AdamInputResultAccessibilityPolicy.ResultState.READY);
        assertTrue(decision.preserveEditableTextValue);
        assertTrue(decision.useStateDescription);
        assertFalse(decision.ownerAnnouncementMigrationReady);
        assertEquals("Continue mode. Ready to send.", decision.stateDescription);
    }

    @Test
    public void sentStateIsPersistentSemanticStateWithoutClaimingAnnouncementMigration() {
        AdamInputResultAccessibilityPolicy.Decision decision =
                AdamInputResultAccessibilityPolicy.decisionFor(
                        "radio",
                        AdamInputResultAccessibilityPolicy.ResultState.SENT);
        assertEquals("Radio mode. Sent.", decision.stateDescription);
        assertFalse(decision.ownerAnnouncementMigrationReady);
    }

    @Test(expected = IllegalArgumentException.class)
    public void missingResultStateFailsClosed() {
        AdamInputResultAccessibilityPolicy.decisionFor("terminal", null);
    }
}
