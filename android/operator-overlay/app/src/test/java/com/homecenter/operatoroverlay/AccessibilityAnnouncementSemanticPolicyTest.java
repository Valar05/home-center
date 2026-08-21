package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class AccessibilityAnnouncementSemanticPolicyTest {
    @Test
    public void spotifyReceiptUsesUserTriggeredPoliteValueChannel() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.POLITE_LIVE_REGION_VALUE,
                decision.channel);
        assertFalse(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.preserveNativeTextValue);
    }

    @Test
    public void heartbeatAutomaticSpeechRequiresMaterialTransition() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.POLITE_LIVE_REGION_VALUE,
                decision.channel);
        assertTrue(decision.automaticUpdateAllowed);
        assertFalse(decision.requiresExplicitUserAction);
        assertTrue(decision.requiresMaterialTransition);
    }

    @Test
    public void explicitDetailSelectionUsesSelectedDetailValueNotGlobalAnnouncementChannel() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.SELECTED_DETAIL_VALUE,
                decision.channel);
        assertFalse(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresExplicitUserAction);
    }

    @Test
    public void adamSendUsesStatusOrStateSemantics() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.STATUS_OR_STATE_DESCRIPTION,
                decision.channel);
        assertFalse(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring);
    }

    @Test(expected = IllegalArgumentException.class)
    public void nullConsequenceFailsClosed() {
        AccessibilityAnnouncementSemanticPolicy.decisionFor(null);
    }
}
