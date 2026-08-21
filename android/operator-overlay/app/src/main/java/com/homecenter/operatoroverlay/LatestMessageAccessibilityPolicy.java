package com.homecenter.operatoroverlay;

/**
 * Pure source policy for the existing latest-message TextView interaction.
 *
 * The changing TextView text remains the semantic value. This policy owns only the
 * interaction semantics layered on top of that value: the labeled standard click
 * consequence and the expanded/collapsed state description.
 *
 * Do not add a separate confirmation announcement for this simple action. Android 16
 * (API 36) deprecates announceForAccessibility/TYPE_ANNOUNCEMENT in favor of semantic
 * UI state, and View.setStateDescription(...) already emits the appropriate semantic
 * state-change event on supported platform versions.
 */
final class LatestMessageAccessibilityPolicy {
    private LatestMessageAccessibilityPolicy() {}

    static String clickActionLabel(boolean expanded) {
        return expanded ? "Collapse latest message" : "Expand latest message";
    }

    static String stateDescription(boolean expanded) {
        return expanded ? "Expanded" : "Collapsed";
    }
}
