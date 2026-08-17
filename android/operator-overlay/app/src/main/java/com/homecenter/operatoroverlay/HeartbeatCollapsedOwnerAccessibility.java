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
    public static final String OVERLAY_ACTION_DESCRIPTION =
            "Drag Home Center overlay. Tap to shrink or expand.";
    public static final String WAITING_DESCRIPTION =
            "Heartbeat skill lights waiting for a material pulse.";

    private HeartbeatCollapsedOwnerAccessibility() {
    }

    /**
     * Description for the existing drag handle.
     *
     * <p>Expanded mode keeps the ordinary overlay action description because the
     * heartbeat summary/detail subtree is visible and accessibility-reachable.
     * Collapsed mode appends the accepted model's bounded collapsed heartbeat truth
     * to the same surviving control. A null model means there is no accepted or
     * preserved scene and therefore remains ordinary pre-contact waiting.</p>
     */
    public static String contentDescription(
            boolean collapsed,
            HeartbeatOverlayViewModel.Model model) {
        if (!collapsed) return OVERLAY_ACTION_DESCRIPTION;
        if (model == null) {
            return OVERLAY_ACTION_DESCRIPTION + " " + WAITING_DESCRIPTION;
        }

        String summary = clean(model.summaryVisibleLabel());
        String detail = clean(model.collapsedContentDescription);
        if (summary.isEmpty() && detail.isEmpty()) {
            return OVERLAY_ACTION_DESCRIPTION + " " + WAITING_DESCRIPTION;
        }
        if (summary.isEmpty()) return OVERLAY_ACTION_DESCRIPTION + " " + detail;
        if (detail.isEmpty()) return OVERLAY_ACTION_DESCRIPTION + " " + sentence(summary);
        return OVERLAY_ACTION_DESCRIPTION + " " + sentence(summary) + " " + detail;
    }

    private static String sentence(String value) {
        String clean = clean(value);
        if (clean.isEmpty()) return "";
        char last = clean.charAt(clean.length() - 1);
        if (last == '.' || last == '!' || last == '?') return clean;
        return clean + ".";
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
