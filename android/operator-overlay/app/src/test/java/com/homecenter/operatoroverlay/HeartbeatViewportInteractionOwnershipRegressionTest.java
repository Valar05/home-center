package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;

import org.junit.Test;

/**
 * Source-only hostile fixtures for viewport interaction ownership.
 * These tests do not prove Android execution, keyboard/TalkBack runtime focus,
 * deployment, phone delivery, or acceptance.
 */
public class HeartbeatViewportInteractionOwnershipRegressionTest {
    private static HeartbeatSkillPolicy.Candidate typed(String id) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "doctrine",
                "fixture:" + id,
                "Interaction ownership fixture",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Viewport owner must remain current",
                "Source-only regression");
    }

    private static HeartbeatOverlayViewModel.Model model(String... ids) {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "interaction-owner",
                Arrays.asList(Arrays.stream(ids)
                        .map(HeartbeatViewportInteractionOwnershipRegressionTest::typed)
                        .toArray(HeartbeatSkillPolicy.Candidate[]::new)),
                true,
                null);
        return HeartbeatOverlayViewModel.fromFrame(frame);
    }

    @Test
    public void newerKeyboardFocusSupersedesSelectionAnchoredRestore() {
        HeartbeatOverlayViewModel.Model accepted = model("selected", "first", "second");
        HeartbeatViewportRestorePolicy.Ticket ticket = HeartbeatViewportRestorePolicy.captureVisible(
                31L,
                "selected",
                true,
                "first",
                true,
                24,
                accepted);

        assertFalse(HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(
                ticket,
                31L,
                accepted,
                "selected",
                "second",
                false,
                true));
    }

    @Test
    public void removedCapturedKeyboardBaselineStillRequiresFocusDestroyingMutation() {
        HeartbeatOverlayViewModel.Model atCapture = model("selected", "focused");
        HeartbeatViewportRestorePolicy.Ticket ticket = HeartbeatViewportRestorePolicy.captureVisible(
                32L,
                "selected",
                true,
                "focused",
                true,
                24,
                atCapture);
        HeartbeatOverlayViewModel.Model afterRemoval = model("selected");

        assertFalse(HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(
                ticket,
                32L,
                afterRemoval,
                "selected",
                "",
                false,
                false));
        assertTrue(HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(
                ticket,
                32L,
                afterRemoval,
                "selected",
                "",
                true,
                false));
    }

    @Test
    public void explicitNoFocusScopeKeepsTouchSelectionUsable() {
        HeartbeatOverlayViewModel.Model accepted = model("selected", "other");
        HeartbeatViewportRestorePolicy.Ticket ticket = HeartbeatViewportRestorePolicy.captureVisible(
                33L,
                "selected",
                true,
                "",
                false,
                24,
                accepted);

        assertTrue(HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(
                ticket,
                33L,
                accepted,
                "selected",
                "",
                false,
                false));
        assertFalse(HeartbeatViewportRestorePolicy.shouldRestoreCapturedOwner(
                ticket,
                33L,
                accepted,
                "selected",
                "",
                false,
                true));
    }
}
