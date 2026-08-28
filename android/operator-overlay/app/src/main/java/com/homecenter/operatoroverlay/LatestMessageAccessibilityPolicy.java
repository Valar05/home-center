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
 * UI state. API 30+ stateDescription remains the compatibility semantic state. API 36
 * additionally defines AccessibilityNodeInfo expanded-state semantics, but this module
 * currently compiles against SDK 35, so supporting policy must not directly reference
 * API-36-only symbols until the existing Android build contract is deliberately raised.
 */
final class LatestMessageAccessibilityPolicy {
    private static final int COLLAPSED_MAX_LINES = 2;
    private static final int EXPANDED_MAX_HEIGHT_DP = 520;

    // Android 16 AccessibilityNodeInfo contract values, kept platform-neutral while
    // compileSdk remains 35. These are evidence/policy values, not owner API wiring.
    static final int API36_EXPANDED_STATE_COLLAPSED = 1;
    static final int API36_EXPANDED_STATE_FULL = 3;

    private LatestMessageAccessibilityPolicy() {}

    static String clickActionLabel(boolean expanded) {
        return expanded ? "Collapse latest message" : "Expand latest message";
    }

    static String stateDescription(boolean expanded) {
        return expanded ? "Expanded" : "Collapsed";
    }

    /**
     * API-36 semantic expansion state value. This remains supporting source only while
     * compileSdk is 35; owner use of AccessibilityNodeInfo.setExpandedState requires a
     * separately reviewed compileSdk >= 36 build-contract change plus owner wiring.
     */
    static int expandedStateApi36(boolean expanded) {
        return expanded
                ? API36_EXPANDED_STATE_FULL
                : API36_EXPANDED_STATE_COLLAPSED;
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
