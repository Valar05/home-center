package com.homecenter.operatoroverlay;

/**
 * Pure source policy for the existing Adam mode selector.
 *
 * <p>The overlay exposes five mutually-exclusive modes. Choosing the already-selected mode does
 * not turn that mode off, so this is a persistent one-of-many selection contract rather than five
 * unrelated toggles. Selection, keyboard focus, accessibility focus, and the editable Adam input
 * are separate states.</p>
 *
 * <p>The selected state alone is not the complete one-of-many context. Each canonical mode also
 * has a stable one-based position in the five-item set so a native owner can expose collection or
 * set-position semantics without deriving order from labels or focus. Position metadata is source
 * context only until the native owner actually consumes it.</p>
 *
 * <p>The owner should expose selection through a native selected/checked semantic state. Do not
 * duplicate that same state into a generic custom stateDescription merely to make the source look
 * more accessible. Mode wire identities are exact; whitespace or case drift fails closed instead
 * of being normalized into a different source identity. This policy owns no View, RadioGroup,
 * controller, renderer, phone surface, transport, or P0 recovery path.
 * {@link OperatorOverlayService} remains the sole native owner. Source policy is not
 * Android/TalkBack runtime proof.</p>
 */
public final class AdamModeSelectionAccessibilityPolicy {
    public enum Mode {
        TERMINAL("terminal", "Terminal"),
        CHAT("chat", "Chat"),
        CONTINUE("continue", "Continue"),
        VLAD("vlad", "Vlad"),
        RADIO("radio", "Radio");

        public final String wireValue;
        public final String spokenLabel;

        Mode(String wireValue, String spokenLabel) {
            this.wireValue = wireValue;
            this.spokenLabel = spokenLabel;
        }
    }

    public static final int SET_SIZE = Mode.values().length;

    public static final class Decision {
        public final Mode mode;
        public final boolean selected;
        public final boolean persistentOneOfMany;
        public final int positionInSet;
        public final int setSize;
        public final boolean selectionOwnsKeyboardFocus;
        public final boolean selectionOwnsAccessibilityFocus;
        public final String actionDescription;

        private Decision(Mode mode, boolean selected) {
            this.mode = mode;
            this.selected = selected;
            this.persistentOneOfMany = true;
            this.positionInSet = mode.ordinal() + 1;
            this.setSize = SET_SIZE;
            this.selectionOwnsKeyboardFocus = false;
            this.selectionOwnsAccessibilityFocus = false;
            this.actionDescription = "Use Adam " + mode.spokenLabel + " mode";
        }
    }

    private AdamModeSelectionAccessibilityPolicy() {
    }

    public static Mode requireMode(String value) {
        for (Mode mode : Mode.values()) {
            if (mode.wireValue.equals(value)) return mode;
        }
        throw new IllegalArgumentException("unsupported Adam mode: " + value);
    }

    public static Decision decisionFor(String activeMode, String candidateMode) {
        Mode active = requireMode(activeMode);
        Mode candidate = requireMode(candidateMode);
        return new Decision(candidate, active == candidate);
    }

    /** Exactly one canonical mode is active. */
    public static int selectedCount(String activeMode) {
        Mode active = requireMode(activeMode);
        int count = 0;
        for (Mode mode : Mode.values()) {
            if (mode == active) count++;
        }
        return count;
    }
}
