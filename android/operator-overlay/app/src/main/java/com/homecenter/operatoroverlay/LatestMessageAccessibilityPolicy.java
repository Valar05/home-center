package com.homecenter.operatoroverlay;

/**
 * Pure source policy for the existing latest-message TextView interaction.
 *
 * The changing TextView text remains the semantic value. This policy owns the
 * interaction semantics layered on top of that value and the spatial contract for
 * expanded inspection: expansion may be height-bounded, but must not amputate the
 * semantic text with an arbitrary line ceiling.
 *
 * Do not add a separate confirmation announcement for this simple action. Android 16
 * (API 36) deprecates announceForAccessibility/TYPE_ANNOUNCEMENT in favor of semantic
 * UI state, and View.setStateDescription(...) already emits the appropriate semantic
 * state-change event on supported platform versions.
 */
final class LatestMessageAccessibilityPolicy {
    private static final int COLLAPSED_MAX_LINES = 2;
    private static final int EXPANDED_MAX_HEIGHT_DP = 520;

    private LatestMessageAccessibilityPolicy() {}

    static String clickActionLabel(boolean expanded) {
        return expanded ? "Collapse latest message" : "Expand latest message";
    }

    static String stateDescription(boolean expanded) {
        return expanded ? "Expanded" : "Collapsed";
    }

    /**
     * Expanded inspection must retain the entire TextView layout and use the existing
     * scrollable height-bounded viewport as the spatial limit. A finite expanded line
     * ceiling can make later message content impossible to inspect visually.
     */
    static int maxLines(boolean expanded) {
        return expanded ? Integer.MAX_VALUE : COLLAPSED_MAX_LINES;
    }

    static int expandedMaxHeightDp() {
        return EXPANDED_MAX_HEIGHT_DP;
    }
}
