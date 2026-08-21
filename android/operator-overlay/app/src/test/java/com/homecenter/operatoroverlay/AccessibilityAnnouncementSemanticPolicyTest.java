package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.view.View;

import org.junit.Test;

public class AccessibilityAnnouncementSemanticPolicyTest {
    @Test
    public void heartbeatMaterialTransitionUsesExistingMaterialChangeGate() {
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
        assertFalse(decision.syntheticRepeatReceiptRequired);
        assertTrue(decision.ownerMigrationReady);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.MigrationBlocker.NONE,
                decision.migrationBlocker);
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
    public void spotifyRepeatableReceiptDesignExistsButOwnerMigrationFailsClosed() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.LIVE_REGION_VALUE_CHANGE,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.SPOTIFY_ACTION_AND_STATUS_VALUE,
                decision.ownerMechanism);
        assertFalse(decision.automaticUpdateAllowed);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.requiresMaterialTransition);
        assertTrue(decision.repeatableIdenticalValuePossible);
        assertFalse(decision.syntheticRepeatReceiptRequired);
        assertFalse(decision.ownerMigrationReady);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.MigrationBlocker.SPOTIFY_REPEATABLE_RECEIPT_UNRESOLVED,
                decision.migrationBlocker);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT,
                        true,
                        true,
                        false));
    }

    @Test
    public void explicitDetailDesignExistsButOwnerMigrationFailsClosed() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.NATIVE_SELECTION_AND_DETAIL,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.HEARTBEAT_SELECTED_CONTROL_AND_DETAIL,
                decision.ownerMechanism);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.repeatableIdenticalValuePossible);
        assertFalse(decision.syntheticRepeatReceiptRequired);
        assertFalse(decision.ownerMigrationReady);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.MigrationBlocker.DETAIL_REPEAT_SELECTION_RECEIPT_UNRESOLVED,
                decision.migrationBlocker);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION,
                        true,
                        true,
                        false));
    }

    @Test
    public void adamSendDesignExistsButOwnerMigrationFailsClosed() {
        AccessibilityAnnouncementSemanticPolicy.Decision decision =
                AccessibilityAnnouncementSemanticPolicy.decisionFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION);

        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.SemanticChannel.NATIVE_ACTION_AND_RESULT_STATE,
                decision.channel);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.OwnerMechanism.ADAM_MODED_SEND_AND_INPUT_RESULT,
                decision.ownerMechanism);
        assertTrue(decision.requiresExplicitUserAction);
        assertTrue(decision.repeatableIdenticalValuePossible);
        assertFalse(decision.syntheticRepeatReceiptRequired);
        assertFalse(decision.ownerMigrationReady);
        assertEquals(
                AccessibilityAnnouncementSemanticPolicy.MigrationBlocker.ADAM_REPEAT_SEND_RESULT_UNRESOLVED,
                decision.migrationBlocker);
        assertEquals(
                View.ACCESSIBILITY_LIVE_REGION_NONE,
                AccessibilityAnnouncementSemanticPolicy.liveRegionModeFor(
                        AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION,
                        true,
                        true,
                        false));
    }

    @Test
    public void migrationReadinessAlwaysHasAnExplicitBlockerState() {
        for (AccessibilityAnnouncementSemanticPolicy.Consequence consequence
                : AccessibilityAnnouncementSemanticPolicy.Consequence.values()) {
            AccessibilityAnnouncementSemanticPolicy.Decision decision =
                    AccessibilityAnnouncementSemanticPolicy.decisionFor(consequence);
            assertEquals(
                    decision.ownerMigrationReady,
                    decision.migrationBlocker == AccessibilityAnnouncementSemanticPolicy.MigrationBlocker.NONE);
        }
    }

    @Test(expected = IllegalArgumentException.class)
    public void nullConsequenceFailsClosed() {
        AccessibilityAnnouncementSemanticPolicy.decisionFor(null);
    }
}
