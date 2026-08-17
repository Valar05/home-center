package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/**
 * Regression source for contact truth when an accepted heartbeat contains no
 * material lights. A non-empty visiblePulseId is contact even when nodes is empty;
 * node count must not collapse accepted contact back into pre-contact waiting.
 */
public class HeartbeatZeroMaterialContactTruthTest {
    @Test
    public void acceptedZeroMaterialPulseIsContactNotWaiting() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-zero-current",
                Collections.emptyList(),
                true,
                null);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(accepted);
        String collapsed = HeartbeatFrameAccessibility.collapsedContentDescription(accepted);

        assertFalse(accepted.refreshInterrupted);
        assertEquals("pulse-zero-current", accepted.visiblePulseId);
        assertTrue(accepted.nodes.isEmpty());
        assertTrue(HeartbeatPersistedPollPolicy.hasVisibleLastGoodContact(accepted));
        assertEquals("HEARTBEAT • 0 LIGHTS", model.summaryVisibleLabel());
        assertEquals("Heartbeat accepted with no material skill lights.", collapsed);
        assertFalse(collapsed.toLowerCase(java.util.Locale.ROOT).contains("waiting"));
    }

    @Test
    public void interruptedZeroMaterialContactIsHeldNotCurrent() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-zero-last-good",
                Collections.emptyList(),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                accepted,
                "fixture wound");

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(interrupted);
        String collapsed = HeartbeatFrameAccessibility.collapsedContentDescription(interrupted);

        assertTrue(interrupted.refreshInterrupted);
        assertEquals("HEARTBEAT • CONTACT HELD", model.summaryVisibleLabel());
        assertTrue(collapsed.startsWith("No material skill lights in the last complete heartbeat."));
        assertTrue(collapsed.contains("Heartbeat refresh interrupted"));
        assertTrue(collapsed.contains("Showing last complete heartbeat pulse-zero-last-good"));
    }

    @Test
    public void preContactWoundStillCannotClaimAcceptedZeroLightContact() {
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                null,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(interrupted);
        String collapsed = HeartbeatFrameAccessibility.collapsedContentDescription(interrupted);

        assertTrue(interrupted.refreshInterrupted);
        assertTrue(interrupted.visiblePulseId.isEmpty());
        assertFalse(HeartbeatPersistedPollPolicy.hasVisibleLastGoodContact(interrupted));
        assertEquals("HEARTBEAT • REFRESH BLOCKED", model.summaryVisibleLabel());
        assertTrue(collapsed.startsWith("No material skill lights."));
        assertTrue(collapsed.contains("No complete heartbeat is available"));
        assertFalse(collapsed.contains("Heartbeat accepted with no material skill lights"));
    }

    @Test
    public void nullSceneRemainsUnavailableRatherThanAcceptedZeroLightContact() {
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(null);

        assertEquals("HEARTBEAT • REFRESH BLOCKED", model.summaryVisibleLabel());
        assertEquals(
                "Heartbeat scene unavailable.",
                HeartbeatFrameAccessibility.collapsedContentDescription(null));
    }
}
