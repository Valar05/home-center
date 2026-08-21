package com.homecenter.operatoroverlay;

/**
 * Pure source policy for the Adam editable-input result state.
 *
 * <p>The editable text remains the field's value. Mode/result context belongs in state semantics;
 * it must not be hidden exclusively in an empty-field hint or replaced by a generic
 * contentDescription. In the native owner, the editable field's contentDescription should remain
 * null so accessibility services can expose the actual changing EditText value; READY/SENT mode
 * context belongs in stateDescription where the platform supports it.</p>
 *
 * <p>This supporting policy does not authorize removal of the current explicit send announcement:
 * repeated identical sends still require a separately reviewed event-result contract.</p>
 *
 * <p>SENT is persistent only while there is no newer unsent request. Selecting another mode makes
 * the field READY. A successful submit makes it SENT. Programmatic clearing after submit does not
 * erase SENT, while real new non-empty editing does return the field to READY. That distinction
 * prevents the send-result state from lying about newly typed, unsent text.</p>
 *
 * <p>This class owns no View, TextWatcher, announcement surface, controller, phone execution, or
 * P0 recovery path. {@link OperatorOverlayService} remains the sole native owner.</p>
 */
public final class AdamInputResultAccessibilityPolicy {
    public enum ResultState {
        READY,
        SENT
    }

    public enum Transition {
        MODE_SELECTED,
        SUBMIT_SUCCEEDED,
        EDITED
    }

    public static final class Decision {
        public final AdamModeSelectionAccessibilityPolicy.Mode mode;
        public final ResultState resultState;
        public final boolean preserveEditableTextValue;
        public final boolean useContentDescriptionForEditableValue;
        public final boolean useStateDescription;
        public final boolean ownerAnnouncementMigrationReady;
        public final String stateDescription;

        private Decision(
                AdamModeSelectionAccessibilityPolicy.Mode mode,
                ResultState resultState) {
            this.mode = mode;
            this.resultState = resultState;
            this.preserveEditableTextValue = true;
            this.useContentDescriptionForEditableValue = false;
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

    /**
     * Return the next persistent result state for one material owner transition.
     *
     * <p>For {@link Transition#EDITED}, {@code hasNonWhitespaceText} means the user-visible field
     * now contains a real unsent request. An empty edit intentionally preserves the current state;
     * this is what lets the owner's programmatic {@code setText("")} after submit retain SENT.</p>
     */
    public static ResultState nextState(
            ResultState current,
            Transition transition,
            boolean hasNonWhitespaceText) {
        if (current == null) throw new IllegalArgumentException("current state is required");
        if (transition == null) throw new IllegalArgumentException("transition is required");
        switch (transition) {
            case MODE_SELECTED:
                return ResultState.READY;
            case SUBMIT_SUCCEEDED:
                return ResultState.SENT;
            case EDITED:
                return hasNonWhitespaceText ? ResultState.READY : current;
            default:
                throw new IllegalArgumentException("unsupported transition: " + transition);
        }
    }
}
