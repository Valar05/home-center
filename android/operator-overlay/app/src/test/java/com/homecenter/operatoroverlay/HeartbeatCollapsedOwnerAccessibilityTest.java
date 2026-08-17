package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/**
 * Regression source for the accessibility projection consumed by the existing
 * drag handle while the heartbeat details subtree is collapsed.
 */
public class HeartbeatCollapsedOwnerAccessibilityTest {
    @Test
    public void acceptedZeroMaterialContactMustReachCollapsedOwnerSurface() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-zero-collapsed-owner",
                Collections.emptyList(),
                true,
                null);
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(accepted);

        String collapsed = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, model);

        assertTrue(collapsed.startsWith(
                HeartbeatCollapsedOwnerAccessibility.OVERLAY_ACTION_DESCRIPTION));
        assertTrue(collapsed.contains("HEARTBEAT • 0 LIGHTS"));
        assertTrue(collapsed.contains("Heartbeat accepted with no material skill lights."));
        assertFalse(collapsed.toLowerCase(java.util.Locale.ROOT).contains("waiting"));
    }

    @Test
    public void preContactWaitingIsDistinctOnTheSameCollapsedSurface() {
        String collapsed = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, null);

        assertTrue(collapsed.contains(
                HeartbeatCollapsedOwnerAccessibility.WAITING_DESCRIPTION));
        assertFalse(collapsed.contains("HEARTBEAT • 0 LIGHTS"));
        assertFalse(collapsed.contains("CONTACT HELD"));
        assertFalse(collapsed.contains("REFRESH BLOCKED"));
    }

    @Test
    public void heldAndBlockedWoundsRemainDistinctOnCollapsedSurface() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-zero-held-owner",
                Collections.emptyList(),
                true,
                null);
        HeartbeatOverlayViewModel.Model held = HeartbeatOverlayViewModel.fromFrame(
                HeartbeatSceneGraph.preserveRejectedRefresh(
                        "",
                        accepted,
                        "fixture held wound"));
        HeartbeatOverlayViewModel.Model blocked = HeartbeatOverlayViewModel.fromFrame(
                HeartbeatSceneGraph.preserveRejectedRefresh(
                        "",
                        null,
                        "fixture pre-contact wound"));

        String heldDescription = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, held);
        String blockedDescription = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, blocked);

        assertTrue(heldDescription.contains("HEARTBEAT • CONTACT HELD"));
        assertTrue(heldDescription.contains("last complete heartbeat"));
        assertTrue(blockedDescription.contains("HEARTBEAT • REFRESH BLOCKED"));
        assertTrue(blockedDescription.contains("No complete heartbeat is available"));
    }

    @Test
    public void expandedOwnerKeepsOrdinaryOverlayActionDescription() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-expanded-owner",
                Collections.emptyList(),
                true,
                null);
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(accepted);

        assertEquals(
                HeartbeatCollapsedOwnerAccessibility.OVERLAY_ACTION_DESCRIPTION,
                HeartbeatCollapsedOwnerAccessibility.contentDescription(false, model));
    }
}
