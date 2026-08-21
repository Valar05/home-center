package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.view.View;

import org.junit.Test;

public class AccessibilityAnnouncementSemanticPolicyTest {
    @Test
    public void heartbeatMaterialTransitionIsTheOnlyReadyLiveRegionValueChange() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.LIVE_REGION_VALUE_CHANGE,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.HEARTBEAT_SUMMARY_MATERIAL_TRANSITION,
                decision.ownerMechanism);
        assertTrue(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresMaterialTransition);
        assertFalse(decision.repeatableIdenticalValuePossible);
        assertTrue(decision.ownerMigrationReady);
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
    public void spotifyReceiptCanRepeatWithoutChangingCurrentStatusSoMigrationStaysUnready() {
        assertRepeatableActionUnready(
                AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT);
    }

    @Test
    public void explicitDetailCanBeSelectedRepeatedlyWithoutChangingDetailSoMigrationStaysUnready() {
        assertRepeatableActionUnready(
                AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION);
    }

    @Test
    public void adamSendCanRepeatInSameModeWithoutChangingSimpleSentLabelSoMigrationStaysUnready() {
        assertRepeatableActionUnready(
                AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION);
    }

    @Test(expected = IllegalArgumentException.class)
    public void nullConsequenceFailsClosed() {
        AccessibilityAnnouncementSemanticPolicy.decisionFor(null);
    }

    private static void assertRepeatableActionUnready(
            AccessibilityAnnouncementSemanticPolicy.Consequence consequence) {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(consequence);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.REPEATABLE_ACTION_EVENT_UNRESOLVED,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.UNRESOLVED_REPEATABLE_ACTION_EVENT,
                decision.ownerMechanism);
        assertFalse(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.preserveNativeTextValue);
        assertTrue(decision.repeatableIdenticalValuePossible);
        assertFalse(decision.ownerMigrationReady);
        assertTrue(decision.legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        consequence,
                        true,
                        true,
                        false));
    }
}
