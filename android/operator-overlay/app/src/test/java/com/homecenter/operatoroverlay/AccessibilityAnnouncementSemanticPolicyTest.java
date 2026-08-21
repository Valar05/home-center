package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.view.View;

import org.junit.Test;

public class AccessibilityAnnouncementSemanticPolicyTest {
    @Test
    public void spotifyReceiptUsesExistingStatusOnlyForExplicitReceipt() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.POLITE_LIVE_REGION_VALUE,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.SPOTIFY_STATUS_EXPLICIT_RECEIPT,
                decision.ownerMechanism);
        assertFalse(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.preserveNativeTextValue);
        assertTrue(decision.backgroundUpdateMustDisableLiveRegion);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_POLITE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT,
                        true,
                        false,
                        true));
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT,
                        false,
                        false,
                        false));
    }

    @Test
    public void heartbeatAutomaticSpeechRequiresMaterialTransitionAndUnmutedOwner() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.HEARTBEAT_SUMMARY_MATERIAL_TRANSITION,
                decision.ownerMechanism);
        assertTrue(decision.automaticUpdateAllowed);
        assertFalse(decision.requiresExplicitUserAction);
        assertTrue(decision.requiresMaterialTransition);
        assertTrue(decision.backgroundUpdateMustDisableLiveRegion);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_POLITE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION,
                        false,
                        true,
                        false));
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION,
                        false,
                        false,
                        false));
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION,
                        false,
                        true,
                        true));
    }

    @Test
    public void explicitDetailSelectionUsesExistingDetailValueWithoutBackgroundSpeech() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.SELECTED_DETAIL_VALUE,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.HEARTBEAT_DETAIL_EXPLICIT_SELECTION,
                decision.ownerMechanism);
        assertFalse(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.backgroundUpdateMustDisableLiveRegion);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_POLITE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION,
                        true,
                        false,
                        false));
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION,
                        false,
                        false,
                        false));
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION,
                        true,
                        false,
                        true));
    }

    @Test
    public void adamSendUsesDedicatedStatusValueNotEditableTextReplacement() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.STATUS_VALUE,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.ADAM_DEDICATED_SEND_STATUS,
                decision.ownerMechanism);
        assertTrue(decision.requiresDedicatedStatusValue);
        assertTrue(decision.preserveNativeTextValue);
        assertTrue(decision.legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_POLITE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION,
                        true,
                        false,
                        true));
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION,
                        false,
                        false,
                        false));
    }

    @Test(expected = IllegalArgumentException.class)
    public void nullConsequenceFailsClosed() {
        AccessibilityAnnouncementSemanticPolicy.decisionFor(null);
    }
}
