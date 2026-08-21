package com.homecenter.operatoroverlay;

/**
 * Pure source policy for whether the existing Adam Send button has a real action.
 *
 * <p>The native owner currently trims the editable request and silently returns when
 * the result is empty. A focusable enabled button whose activation is guaranteed to
 * no-op is misleading for touch, keyboard, and accessibility users. Prefer native
 * enabled/disabled semantics tied to the actual trimmed request over inventing a new
 * repeated announcement receipt.</p>
 *
 * <p>Mode-specific action wording remains owned by
 * {@link AdamSendActionAccessibilityPolicy}. Editable value and READY/SENT context
 * remain owned by {@link AdamInputResultAccessibilityPolicy}. This policy owns no
 * Button, TextWatcher, request transport, announcement, controller, phone execution,
 * or P0 recovery surface. {@link OperatorOverlayService} remains the sole native
 * owner.</p>
 */
public final class AdamSendAvailabilityAccessibilityPolicy {
    public static final class Decision {
        public final AdamModeSelectionAccessibilityPolicy.Mode mode;
        public final boolean enabled;
        public final String visibleLabel;
        public final String actionDescription;
        public final boolean requiresSyntheticAnnouncement;

        private Decision(
                AdamModeSelectionAccessibilityPolicy.Mode mode,
                boolean enabled,
                String actionDescription) {
            this.mode = mode;
            this.enabled = enabled;
            this.visibleLabel = "Send";
            this.actionDescription = actionDescription;
            this.requiresSyntheticAnnouncement = false;
        }
    }

    private AdamSendAvailabilityAccessibilityPolicy() {
    }

    public static Decision decisionFor(String mode, CharSequence editableValue) {
        AdamSendActionAccessibilityPolicy.Decision action =
                AdamSendActionAccessibilityPolicy.decisionFor(mode);
        boolean enabled = hasMaterialRequest(editableValue);
        return new Decision(action.mode, enabled, action.actionDescription);
    }

    public static boolean hasMaterialRequest(CharSequence editableValue) {
        if (editableValue == null) return false;
        int length = editableValue.length();
        for (int index = 0; index < length; index++) {
            if (!Character.isWhitespace(editableValue.charAt(index))) return true;
        }
        return false;
    }
}
