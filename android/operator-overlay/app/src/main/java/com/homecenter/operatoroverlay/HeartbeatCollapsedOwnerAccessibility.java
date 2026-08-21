package com.homecenter.operatoroverlay;

/**
 * Pure accessibility projection for the existing Operator Overlay control that
 * survives while heartbeat details are collapsed.
 *
 * <p>This class does not own Android views, focus, rendering, transport, phone
 * execution, or P0 recovery. It composes the already-accepted heartbeat model so
 * the existing owner can expose heartbeat truth without re-deriving scene state.</p>
 */
public final class HeartbeatCollapsedOwnerAccessibility {
    /** Hard returned budget for the entire collapsed drag-handle description. */
    public static final int MAX_COLLAPSED_OWNER_CODE_POINTS = 320;
    public static final String OVERLAY_ACTION_DESCRIPTION =
            "Drag Home Center overlay. Tap to shrink or expand.";
    public static final String COLLAPSED_ACTION_DESCRIPTION =
            "Drag Home Center overlay. Tap to expand for heartbeat details.";
    public static final String WAITING_DESCRIPTION =
            "Heartbeat skill lights waiting for a material pulse.";
    public static final String ACCEPTED_ZERO_MATERIAL_DESCRIPTION =
            "Heartbeat accepted with no material skill lights.";
    public static final String HELD_ZERO_MATERIAL_DESCRIPTION =
            "Last complete heartbeat has no material skill lights.";

    private HeartbeatCollapsedOwnerAccessibility() {
    }

    /**
     * Backward-compatible heartbeat-only projection. New owner wiring should prefer
     * the overload that also receives the current operator-status description so a
     * custom contentDescription cannot mask the changing visible HC state.
     */
    public static String contentDescription(
            boolean collapsed,
            HeartbeatOverlayViewModel.Model model) {
        return contentDescription(collapsed, "", model);
    }

    /**
     * Description for the existing drag handle.
     *
     * <p>Expanded mode keeps the ordinary overlay action description because the
     * heartbeat summary/detail subtree and operational status surfaces are visible and
     * accessibility-reachable. Collapsed mode has only one surviving owner, so its
     * custom contentDescription must include any material operator-status description
     * before heartbeat truth. Otherwise the custom description masks the visible
     * compact HC state from accessibility services.</p>
     *
     * <p>The operator-status text is supplied by the existing owner; this projection
     * does not re-derive control, connectivity, remote-input, mute, or P0 state. The
     * heartbeat portion keeps the surviving action control concise: action + current
     * operator status + canonical heartbeat summary + compact blocked/fault attention
     * truth + only the contact/interruption truth needed before explicit expansion.
     * Detailed light names remain behind the existing expand action. The entire
     * returned description has one hard aggregate speech budget while exact model and
     * evidence fields remain unchanged.</p>
     */
    public static String contentDescription(
            boolean collapsed,
            String operatorStatusDescription,
            HeartbeatOverlayViewModel.Model model) {
        if (!collapsed) return OVERLAY_ACTION_DESCRIPTION;

        StringBuilder out = new StringBuilder(COLLAPSED_ACTION_DESCRIPTION);
        appendSentence(out, operatorStatusDescription);
        if (model == null) {
            appendSentence(out, WAITING_DESCRIPTION);
            return bounded(out.toString());
        }

        String summary = clean(model.summaryVisibleLabel());
        appendSentence(out, summary.isEmpty() ? WAITING_DESCRIPTION : summary);
        appendSentence(out, model.attentionStatusDescription);

        boolean hasVisibleContact = !clean(model.visiblePulseId).isEmpty();
        if (model.controls.isEmpty() && hasVisibleContact) {
            appendSentence(
                    out,
                    model.refreshInterrupted
                            ? HELD_ZERO_MATERIAL_DESCRIPTION
                            : ACCEPTED_ZERO_MATERIAL_DESCRIPTION);
        }

        if (model.refreshInterrupted) {
            appendSentence(out, model.interruptionDetailContentDescription());
        }
        return bounded(out.toString());
    }

    private static void appendSentence(StringBuilder out, String value) {
        String sentence = sentence(value);
        if (sentence.isEmpty()) return;
        if (out.length() > 0 && out.charAt(out.length() - 1) != ' ') out.append(' ');
        out.append(sentence);
    }

    private static String sentence(String value) {
        String clean = clean(value);
        if (clean.isEmpty()) return "";
        char last = clean.charAt(clean.length() - 1);
        if (last == '.' || last == '!' || last == '?') return clean;
        return clean + ".";
    }

    private static String bounded(String value) {
        return HeartbeatPlainTextBudget.boundedWithEllipsis(
                clean(value),
                MAX_COLLAPSED_OWNER_CODE_POINTS);
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
