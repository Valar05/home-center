package com.homecenter.operatoroverlay;

/**
 * Pure accessibility policy for native Adam Send availability.
 *
 * <p>The visible Send button remains the existing native owner. This policy only answers whether
 * the current editable request is materially sendable under the owner's established trim
 * contract, and exposes the already-owned mode-specific action wording.</p>
 *
 * <p>Direct editable values cross the same broad source-work ceiling used by the heartbeat
 * envelope before whole-source work. Admitted values are scanned in-place using the exact
 * historical {@link String#trim()} emptiness predicate ({@code char <= U+0020}) rather than being
 * materialized through {@code toString()}. Over-ceiling values fail closed as a distinct state;
 * they are not truncated or normalized. This does not claim callback-free arbitrary
 * {@link CharSequence} admission; it bounds the number of source observations owned by this
 * policy.</p>
 *
 * <p>This policy owns no View, TextWatcher, announcement, controller, transport, phone execution,
 * or P0 recovery path. {@link OperatorOverlayService} remains the sole native owner.</p>
 */
public final class AdamSendAvailabilityAccessibilityPolicy {
    public static final int MAX_REQUEST_SOURCE_CODE_UNITS =
            HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS;

    public enum RequestState {
        EMPTY_OR_WHITESPACE,
        MATERIAL,
        OVER_BUDGET
    }

    public static final class Decision {
        public final AdamModeSelectionAccessibilityPolicy.Mode mode;
        public final RequestState requestState;
        public final boolean enabled;
        public final String visibleLabel;
        public final String actionDescription;
        public final boolean requiresSyntheticAnnouncement;

        private Decision(
                AdamModeSelectionAccessibilityPolicy.Mode mode,
                RequestState requestState,
                String actionDescription) {
            this.mode = mode;
            this.requestState = requestState;
            this.enabled = requestState == RequestState.MATERIAL;
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
        return new Decision(action.mode, classifyRequest(editableValue), action.actionDescription);
    }

    /**
     * Return whether direct source is within the finite work throat before whole-source work.
     *
     * <p>This intentionally performs only the caller's {@code length()} observation. It does not
     * materialize, trim, truncate, or otherwise rewrite evidence.</p>
     */
    public static boolean sourceWithinWorkBudget(CharSequence editableValue) {
        return editableValue == null
                || editableValue.length() <= MAX_REQUEST_SOURCE_CODE_UNITS;
    }

    /**
     * Classify request material under bounded source work without materializing the whole
     * {@link CharSequence}.
     */
    public static RequestState classifyRequest(CharSequence editableValue) {
        if (editableValue == null) return RequestState.EMPTY_OR_WHITESPACE;

        int sourceLength = editableValue.length();
        if (sourceLength > MAX_REQUEST_SOURCE_CODE_UNITS) return RequestState.OVER_BUDGET;

        for (int index = 0; index < sourceLength; index++) {
            if (editableValue.charAt(index) > ' ') {
                return RequestState.MATERIAL;
            }
        }
        return RequestState.EMPTY_OR_WHITESPACE;
    }

    /** Match the existing owner's {@code String.trim().isEmpty()} material-request admission. */
    public static boolean hasMaterialRequest(CharSequence editableValue) {
        return classifyRequest(editableValue) == RequestState.MATERIAL;
    }
}
