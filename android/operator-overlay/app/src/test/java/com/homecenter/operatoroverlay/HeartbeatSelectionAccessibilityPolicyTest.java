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

    private static String repeated(char value, int count) {
        StringBuilder out = new StringBuilder(count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }

    @Test
    public void persistentHorizontalSelectionIsSingleColumnCollection() {
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision decision =
                HeartbeatSelectionAccessibilityPolicy.fromModel(
                        model("pulse-selection", "hunger", "regnet", "venice"),
                        "regnet");

        assertEquals(3, decision.rowCount);
        assertEquals(1, decision.columnCount);
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
        assertEquals(1, selected.rowIndex);
        assertEquals(0, selected.columnIndex);
    }

    @Test
    public void renderedOrderOwnsStableOneBasedPositionsAndNativeRows() {
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision first =
                HeartbeatSelectionAccessibilityPolicy.fromModel(
                        model("pulse-a", "alpha", "beta"),
                        "beta");
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision reordered =
                HeartbeatSelectionAccessibilityPolicy.fromModel(
                        model("pulse-b", "beta", "alpha"),
                        "beta");

        assertEquals(2, first.itemById("beta").positionInSet);
        assertEquals(1, first.itemById("beta").rowIndex);
        assertEquals(1, reordered.itemById("beta").positionInSet);
        assertEquals(0, reordered.itemById("beta").rowIndex);
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
    public void directSelectedIdSourceWorkIsBoundedBeforeItemComparison() {
        HeartbeatOverlayViewModel.Model source = model("pulse-source-bound", "alpha", "beta");
        int max = HeartbeatSelectionAccessibilityPolicy.MAX_DIRECT_SELECTED_ID_SOURCE_CODE_UNITS;
        String atMaxId = repeated('x', max);
        String overId = repeated('x', max + 1);

        HeartbeatSelectionAccessibilityPolicy.CollectionDecision atMax =
                HeartbeatSelectionAccessibilityPolicy.fromModel(source, atMaxId);
        HeartbeatSelectionAccessibilityPolicy.CollectionDecision maxPlusOne =
                HeartbeatSelectionAccessibilityPolicy.fromModel(source, overId);

        assertEquals(0, atMax.selectedCount());
        assertEquals(0, maxPlusOne.selectedCount());
        assertFalse(maxPlusOne.itemById("alpha").selected);
        assertFalse(maxPlusOne.itemById("beta").selected);
        assertNull(maxPlusOne.itemById(overId));
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