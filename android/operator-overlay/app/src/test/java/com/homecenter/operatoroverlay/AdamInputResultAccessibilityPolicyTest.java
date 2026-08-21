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
        assertFalse(decision.useContentDescriptionForEditableValue);
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
        assertTrue(decision.preserveEditableTextValue);
        assertFalse(decision.useContentDescriptionForEditableValue);
        assertEquals("Radio mode. Sent.", decision.stateDescription);
        assertFalse(decision.ownerAnnouncementMigrationReady);
    }

    @Test
    public void successfulSubmitMovesReadyToSent() {
        assertEquals(
                AdamInputResultAccessibilityPolicy.ResultState.SENT,
                AdamInputResultAccessibilityPolicy.nextState(
                        AdamInputResultAccessibilityPolicy.ResultState.READY,
                        AdamInputResultAccessibilityPolicy.Transition.SUBMIT_SUCCEEDED,
                        false));
    }

    @Test
    public void programmaticEmptyClearAfterSubmitPreservesSent() {
        assertEquals(
                AdamInputResultAccessibilityPolicy.ResultState.SENT,
                AdamInputResultAccessibilityPolicy.nextState(
                        AdamInputResultAccessibilityPolicy.ResultState.SENT,
                        AdamInputResultAccessibilityPolicy.Transition.EDITED,
                        false));
    }

    @Test
    public void realNewEditingAfterSentReturnsReady() {
        assertEquals(
                AdamInputResultAccessibilityPolicy.ResultState.READY,
                AdamInputResultAccessibilityPolicy.nextState(
                        AdamInputResultAccessibilityPolicy.ResultState.SENT,
                        AdamInputResultAccessibilityPolicy.Transition.EDITED,
                        true));
    }

    @Test
    public void selectingAnyModeReturnsReady() {
        assertEquals(
                AdamInputResultAccessibilityPolicy.ResultState.READY,
                AdamInputResultAccessibilityPolicy.nextState(
                        AdamInputResultAccessibilityPolicy.ResultState.SENT,
                        AdamInputResultAccessibilityPolicy.Transition.MODE_SELECTED,
                        false));
    }

    @Test(expected = IllegalArgumentException.class)
    public void missingResultStateFailsClosed() {
        AdamInputResultAccessibilityPolicy.decisionFor("terminal", null);
    }

    @Test(expected = IllegalArgumentException.class)
    public void missingCurrentLifecycleStateFailsClosed() {
        AdamInputResultAccessibilityPolicy.nextState(
                null,
                AdamInputResultAccessibilityPolicy.Transition.EDITED,
                true);
    }

    @Test(expected = IllegalArgumentException.class)
    public void missingLifecycleTransitionFailsClosed() {
        AdamInputResultAccessibilityPolicy.nextState(
                AdamInputResultAccessibilityPolicy.ResultState.READY,
                null,
                true);
    }
}
