package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class HeartbeatSelectionAccessibilityPolicyTest {
    private static HeartbeatSkillPolicy.Candidate typed(String id) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "doctrine",
                "fixture:" + id,
                "Materially active selection fixture",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Selection fixture consequence",
                "Exact selection fixture boundary");
    }

    private static HeartbeatOverlayViewModel.Model model(String pulse, String... ids) {
        HeartbeatSkillPolicy.Candidate[] candidates = new HeartbeatSkillPolicy.Candidate[ids.length];
        for (int index = 0; index < ids.length; index++) candidates[index] = typed(ids[index]);
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                pulse,
                Arrays.asList(candidates),
                true,
                null);
        return HeartbeatOverlayViewModel.fromFrame(frame);
    }

    @Test
    public void persistentSelectionIsOneSingleSelectionCollection() {
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision decision =
                HeartbeatSelectionAccessibilityPolicy.fromModel(
                        model("pulse-selection", "hunger", "regnet", "venice"),
                        "regnet");

        assertEquals(1, decision.rowCount);
        assertEquals(3, decision.columnCount);
        assertTrue(decision.singleSelection);
        assertEquals(1, decision.selectedCount());

        HeartbeatSelectionAccessibilityPolicy.ItemDecision selected =
                decision.itemById("REGNET");
        assertTrue(selected.selected);
        assertTrue(selected.persistentOneOfMany);
        assertFalse(selected.selectionOwnsKeyboardFocus);
        assertFalse(selected.selectionOwnsAccessibilityFocus);
        assertEquals(2, selected.positionInSet);
        assertEquals(3, selected.setSize);
        assertEquals(0, selected.rowIndex);
        assertEquals(1, selected.columnIndex);
    }

    @Test
    public void renderedOrderOwnsStableOneBasedPositionsForThatFrame() {
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision first =
                HeartbeatSelectionAccessibilityPolicy.fromModel(
                        model("pulse-a", "alpha", "beta"),
                        "beta");
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision reordered =
                HeartbeatSelectionAccessibilityPolicy.fromModel(
                        model("pulse-b", "beta", "alpha"),
                        "beta");

        assertEquals(2, first.itemById("beta").positionInSet);
        assertEquals(1, reordered.itemById("beta").positionInSet);
        assertTrue(first.itemById("beta").selected);
        assertTrue(reordered.itemById("beta").selected);
    }

    @Test
    public void staleSelectionDoesNotInventReplacementSelection() {
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision decision =
                HeartbeatSelectionAccessibilityPolicy.fromModel(
                        model("pulse-stale", "alpha", "beta"),
                        "removed");

        assertEquals(0, decision.selectedCount());
        assertFalse(decision.itemById("alpha").selected);
        assertFalse(decision.itemById("beta").selected);
    }

    @Test
    public void emptyAndNullModelsRemainEmptyCollections() {
        HeartbeatOverlayViewModel.Model emptyModel = HeartbeatOverlayViewModel.fromFrame(
                HeartbeatSceneGraph.build(
                        "pulse-empty",
                        Collections.emptyList(),
                        true,
                        null));
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision empty =
                HeartbeatSelectionAccessibilityPolicy.fromModel(emptyModel, "anything");
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision missing =
                HeartbeatSelectionAccessibilityPolicy.fromModel(null, "anything");

        assertEquals(0, empty.rowCount);
        assertEquals(0, empty.columnCount);
        assertEquals(0, empty.selectedCount());
        assertTrue(empty.items.isEmpty());
        assertNull(empty.itemById("anything"));

        assertEquals(0, missing.rowCount);
        assertEquals(0, missing.columnCount);
        assertTrue(missing.items.isEmpty());
    }
}
