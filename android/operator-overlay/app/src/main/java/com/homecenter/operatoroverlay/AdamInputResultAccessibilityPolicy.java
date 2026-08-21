package com.homecenter.operatoroverlay;

/**
 * Pure source policy for the Adam editable-input result state.
 *
 * <p>The editable text remains the field's value. Mode/result context belongs in state semantics;
 * it must not be hidden exclusively in an empty-field hint while a generic contentDescription
 * masks that hint. This supporting policy does not authorize removal of the current explicit send
 * announcement: repeated identical sends still require a separately reviewed event-result contract.</p>
 *
 * <p>This class owns no View, announcement surface, controller, phone execution, or P0 recovery
 * path. {@link OperatorOverlayService} remains the sole native owner.</p>
 */
public final class AdamInputResultAccessibilityPolicy {
    public enum ResultState {
        READY,
        SENT
    }

    public static final class Decision {
        public final AdamModeSelectionAccessibilityPolicy.Mode mode;
        public final ResultState resultState;
        public final boolean preserveEditableTextValue;
        public final boolean useStateDescription;
        public final boolean ownerAnnouncementMigrationReady;
        public final String stateDescription;

        private Decision(
                AdamModeSelectionAccessibilityPolicy.Mode mode,
                ResultState resultState) {
            this.mode = mode;
            this.resultState = resultState;
            this.preserveEditableTextValue = true;
            this.useStateDescription = true;
            this.ownerAnnouncementMigrationReady = false;
            this.stateDescription = mode.spokenLabel + " mode. "
                    + (resultState == ResultState.SENT ? "Sent." : "Ready to send.");
        }
    }

    private AdamInputResultAccessibilityPolicy() {
    }

    public static Decision decisionFor(String mode, ResultState resultState) {
        if (resultState == null) {
            throw new IllegalArgumentException("resultState is required");
        }
        return new Decision(AdamModeSelectionAccessibilityPolicy.requireMode(mode), resultState);
    }
}
