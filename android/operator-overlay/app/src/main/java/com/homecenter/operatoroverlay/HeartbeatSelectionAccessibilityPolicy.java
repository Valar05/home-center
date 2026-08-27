package com.homecenter.operatoroverlay;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Pure source policy for the heartbeat light row's persistent one-of-many selection.
 *
 * <p>The existing Android owner already keeps one semantic selected id and native Button selected
 * state. This policy supplies the missing collection contract without owning Views, focus,
 * rendering, transport, phone execution, or P0 recovery. Persistent selection is not a toggle:
 * selection, keyboard focus, accessibility focus, and activation are separate state machines.</p>
 *
 * <p>The native control strip is horizontal, so its accessibility collection geometry is one row
 * with one column per rendered item. The separate one-based {@code positionInSet} is retained as a
 * source-level human/order identity, while native collection geometry uses {@code rowIndex=0} and
 * {@code columnIndex=index}.</p>
 *
 * <p>Source policy is not native owner wiring or runtime TalkBack evidence. The existing
 * {@link OperatorOverlayService} remains the sole native owner.</p>
 */
public final class HeartbeatSelectionAccessibilityPolicy {
    /** Broad direct selected-id source-work throat before repeated equality checks. */
    public static final int MAX_DIRECT_SELECTED_ID_SOURCE_CODE_UNITS =
            HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS;

    public static final class ItemDecision {
        public final String id;
        public final int rowIndex;
        public final int columnIndex;
        public final int positionInSet;
        public final int setSize;
        public final boolean selected;
        public final boolean persistentOneOfMany;
        public final boolean selectionOwnsKeyboardFocus;
        public final boolean selectionOwnsAccessibilityFocus;

        private ItemDecision(
                String id,
                int itemIndex,
                int setSize,
                boolean selected) {
            this.id = id;
            this.rowIndex = 0;
            this.columnIndex = itemIndex;
            this.positionInSet = itemIndex + 1;
            this.setSize = setSize;
            this.selected = selected;
            this.persistentOneOfMany = true;
            this.selectionOwnsKeyboardFocus = false;
            this.selectionOwnsAccessibilityFocus = false;
        }
    }

    public static final class CollectionDecision {
        public final int rowCount;
        public final int columnCount;
        public final boolean singleSelection;
        public final List<ItemDecision> items;

        private CollectionDecision(List<ItemDecision> items) {
            this.items = Collections.unmodifiableList(new ArrayList<>(items));
            this.rowCount = items.isEmpty() ? 0 : 1;
            this.columnCount = items.size();
            this.singleSelection = true;
        }

        public int selectedCount() {
            int count = 0;
            for (ItemDecision item : items) {
                if (item.selected) count++;
            }
            return count;
        }

        public ItemDecision itemById(String semanticId) {
            String target = boundedDirectSelectedId(semanticId);
            if (target.isEmpty()) return null;
            for (ItemDecision item : items) {
                if (item.id.equalsIgnoreCase(target)) return item;
            }
            return null;
        }
    }

    private HeartbeatSelectionAccessibilityPolicy() {
    }

    /**
     * Derive collection/item semantics from the already accepted UI-ready heartbeat model.
     *
     * <p>A stale selected id does not invent a replacement selection. The rendered order owns
     * stable one-based position-in-set and zero-based native column index for this frame. Reordering
     * therefore changes positions but not semantic identity. No decision here requests keyboard or
     * accessibility focus.</p>
     *
     * <p>The direct selected-id argument is a public source-work boundary of its own. A canonical
     * scene/model id is already small, but direct callers do not inherit that guarantee. Reject an
     * oversized query to "no selection" before repeated {@code equalsIgnoreCase} work; do not trim
     * or synthesize a smaller identity. The same throat protects direct collection lookup.</p>
     */
    public static CollectionDecision fromModel(
            HeartbeatOverlayViewModel.Model model,
            String selectedId) {
        if (model == null || model.controls.isEmpty()) {
            return new CollectionDecision(Collections.emptyList());
        }
        String selected = boundedDirectSelectedId(selectedId);
        int setSize = model.controls.size();
        List<ItemDecision> items = new ArrayList<>(setSize);
        for (int index = 0; index < setSize; index++) {
            HeartbeatOverlayViewModel.LightControl control = model.controls.get(index);
            items.add(new ItemDecision(
                    control.id,
                    index,
                    setSize,
                    !selected.isEmpty() && control.id.equalsIgnoreCase(selected)));
        }
        return new CollectionDecision(items);
    }

    private static String boundedDirectSelectedId(String selectedId) {
        if (selectedId == null
                || selectedId.length() > MAX_DIRECT_SELECTED_ID_SOURCE_CODE_UNITS) {
            return "";
        }
        return selectedId;
    }
}
