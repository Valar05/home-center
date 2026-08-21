package com.homecenter.operatoroverlay;

/**
 * Pure source policy for the existing latest-message TextView interaction.
 *
 * The changing TextView text remains the semantic value. This policy owns only the
 * interaction semantics layered on top of that value: current expand/collapse state,
 * the labeled standard click consequence, and the bounded post-action confirmation.
 */
final class LatestMessageAccessibilityPolicy {
    private LatestMessageAccessibilityPolicy() {}

    static String clickActionLabel(boolean expanded) {
        return expanded ? "Collapse latest message" : "Expand latest message";
    }

    static String stateDescription(boolean expanded) {
        return expanded ? "Expanded" : "Collapsed";
    }

    static String confirmationAnnouncement(boolean expanded) {
        return expanded ? "Latest message expanded" : "Latest message collapsed";
    }
}
