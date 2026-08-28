package com.homecenter.operatoroverlay;

/**
 * Pure accessibility policy for the existing Adam Send button.
 *
 * <p>The visible button may remain the compact label "Send", but its semantic action must name the
 * exact currently selected Adam mode because the consequence changes with that mode. This is action
 * context, not selection state: the Send button must not claim that it owns the selected mode,
 * keyboard focus, or accessibility focus.</p>
 *
 * <p>Mode identity is delegated to {@link AdamModeSelectionAccessibilityPolicy}; whitespace/case
 * drift therefore fails closed. This policy owns no Button, request transport, announcement,
 * controller, phone execution, or P0 recovery surface. {@link OperatorOverlayService} remains the
 * sole native owner.</p>
 */
public final class AdamSendActionAccessibilityPolicy {
    public static final class Decision {
        public final AdamModeSelectionAccessibilityPolicy.Mode mode;
        public final String visibleLabel;
        public final String actionDescription;
        public final boolean actionOwnsSelection;
        public final boolean actionOwnsKeyboardFocus;
        public final boolean actionOwnsAccessibilityFocus;

        private Decision(AdamModeSelectionAccessibilityPolicy.Mode mode) {
            this.mode = mode;
            this.visibleLabel = "Send";
            this.actionDescription = "Send request to Adam using " + mode.spokenLabel + " mode";
            this.actionOwnsSelection = false;
            this.actionOwnsKeyboardFocus = false;
            this.actionOwnsAccessibilityFocus = false;
        }
    }

    private AdamSendActionAccessibilityPolicy() {
    }

    public static Decision decisionFor(String mode) {
        return new Decision(AdamModeSelectionAccessibilityPolicy.requireMode(mode));
    }
}
