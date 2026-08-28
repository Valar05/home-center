package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class HeartbeatOverlayViewModelTest {
    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            HeartbeatSkillPolicy.State state,
            boolean changed,
            String consequence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "doctrine",
                "fixture:" + id,
                "Materially active in fixture",
                state,
                changed,
                consequence,
                "Exact fixture boundary");
    }

    @Test
    public void projectsAccessibleControlsFromAcceptedScene() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-ui",
                Arrays.asList(
                        typed("hunger", HeartbeatSkillPolicy.State.ACTIVE, true, "Changed A"),
                        typed("regnet", HeartbeatSkillPolicy.State.BLOCKED, false, "Changed B")),
                true,
                null);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(frame);

        assertEquals("pulse-ui", model.visiblePulseId);
        assertFalse(model.refreshInterrupted);
        assertEquals(2, model.controls.size());
        assertEquals(48, model.controls.get(0).minTouchTargetDp);
        assertTrue(model.controls.get(0).visibleLabel.startsWith("● "));
        assertTrue(model.controls.get(0).visibleLabel.endsWith(" — active"));
        assertTrue(model.controls.get(1).visibleLabel.startsWith("□ "));
        assertTrue(model.controls.get(1).visibleLabel.endsWith(" — blocked"));
        assertTrue(model.controls.get(1).contentDescription.contains("blocked"));
        assertTrue(model.collapsedContentDescription.contains("2 material skill lights"));
        assertEquals("HEARTBEAT • 2 LIGHTS", model.summaryVisibleLabel());
        assertEquals("", model.interruptionDetailContentDescription());
    }

    @Test
    public void interruptedRefreshProjectsOnlyPreservedContact() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.singletonList(typed(
                        "contact",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Contact established")),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "pulse-broken",
                Collections.singletonList(typed(
                        "replacement",
                        HeartbeatSkillPolicy.State.FAULT,
                        false,
                        "Replacement fixture")),
                false,
                lastGood);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(interrupted);

        assertTrue(model.refreshInterrupted);
        assertEquals("pulse-good", model.visiblePulseId);
        assertEquals("Pulse is incomplete.", model.refreshBoundary);
        assertEquals(1, model.controls.size());
        assertEquals("contact", model.controls.get(0).id);
        assertNull(model.controlById("replacement"));
        assertFalse(model.controls.get(0).transitionMotion);
        assertFalse(model.transitionMotionAllowed);
        assertTrue(model.collapsedContentDescription.contains("Showing last complete heartbeat pulse-good"));
        assertEquals("HEARTBEAT • 1 LIGHT • CONTACT HELD", model.summaryVisibleLabel());
        assertEquals(
                "Refresh rejected. Last good heartbeat contact is preserved; no discarded attempted light is current.",
                model.interruptionDetailContentDescription());
    }

    @Test
    public void zeroMaterialLastGoodContactStillReportsContactHeld() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-zero",
                Collections.emptyList(),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                lastGood,
                "fixture wound");

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(interrupted);

        assertTrue(model.controls.isEmpty());
        assertEquals("pulse-zero", model.visiblePulseId);
        assertEquals("HEARTBEAT • CONTACT HELD", model.summaryVisibleLabel());
        assertEquals(
                "Refresh rejected. Last good heartbeat contact is preserved; no discarded attempted light is current.",
                model.interruptionDetailContentDescription());
    }

    @Test
    public void preContactReadFailureDoesNotClaimContactHeld() {
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                null,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(interrupted);

        assertTrue(model.refreshInterrupted);
        assertTrue(model.visiblePulseId.isEmpty());
        assertTrue(model.controls.isEmpty());
        assertEquals("HEARTBEAT • REFRESH BLOCKED", model.summaryVisibleLabel());
        assertEquals(
                "Refresh blocked before any heartbeat contact was accepted; no discarded attempted light is current.",
                model.interruptionDetailContentDescription());
        assertTrue(model.collapsedContentDescription.contains("No complete heartbeat is available"));
    }

    @Test
    public void stableSemanticLookupSurvivesVisibleOrder() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-order",
                Arrays.asList(
                        typed("second", HeartbeatSkillPolicy.State.BLOCKED, false, "Boundary B"),
                        typed("first", HeartbeatSkillPolicy.State.ACTIVE, true, "Boundary A")),
                true,
                null);

        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(frame);
        HeartbeatOverlayViewModel.LightControl selected = model.controlById("FIRST");

        assertNotNull(selected);
        assertEquals("first", selected.id);
        assertEquals(1, selected.focusIndex);
    }

    @Test
    public void visibleLabelHardBudgetIncludesEllipsisWithoutSplittingUnicode() {
        StringBuilder longLabel = new StringBuilder();
        // 78 supplementary code points = 156 UTF-16 chars: over the 72-code-point
        // visible budget while still inside the typed source label bound of 160 chars.
        for (int index = 0; index < 78; index++) longLabel.append("🦢");
        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                "swan",
                longLabel.toString(),
                "doctrine",
                "fixture:swan",
                "Materially active in fixture",
                HeartbeatSkillPolicy.State.FAULT,
                false,
                "Long label fixture",
                "Exact fixture boundary");
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-swan",
                Collections.singletonList(candidate),
                true,
                null);

        HeartbeatOverlayViewModel.LightControl control =
                HeartbeatOverlayViewModel.fromFrame(frame).controls.get(0);

        String expectedLabel = repeat(
                "🦢",
                HeartbeatOverlayViewModel.MAX_VISIBLE_LABEL_CODE_POINTS - 1) + "…";
        assertEquals("× " + expectedLabel + " — fault", control.visibleLabel);
        assertEquals(
                HeartbeatOverlayViewModel.MAX_VISIBLE_LABEL_CODE_POINTS,
                expectedLabel.codePointCount(0, expectedLabel.length()));
        assertTrue(control.detailContentDescription.contains("🦢"));
    }

    @Test
    public void nullSceneFailsClosedWithoutControls() {
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(null);

        assertTrue(model.refreshInterrupted);
        assertEquals("Heartbeat scene unavailable.", model.refreshBoundary);
        assertTrue(model.controls.isEmpty());
        assertFalse(model.transitionMotionAllowed);
        assertEquals("Heartbeat scene unavailable.", model.collapsedContentDescription);
        assertEquals("HEARTBEAT • REFRESH BLOCKED", model.summaryVisibleLabel());
        assertEquals(
                "Refresh blocked before any heartbeat contact was accepted; no discarded attempted light is current.",
                model.interruptionDetailContentDescription());
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
