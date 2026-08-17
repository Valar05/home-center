package com.homecenter.operatoroverlay;

/**
 * Narrow source policy for invisible, non-directional formatting controls that can
 * make two operator-facing heartbeat strings look equivalent while remaining
 * different evidence/checkpoint identities.
 *
 * <p>This deliberately does not reject every Unicode FORMAT character. U+200D ZERO
 * WIDTH JOINER and U+200C ZERO WIDTH NON-JOINER have legitimate grapheme/language
 * shaping uses and remain allowed. Directional bidi controls and ISO controls remain
 * owned by {@link HeartbeatSkillPolicy}. This policy only names the additional
 * invisible presentation aliases that should fail closed when the existing semantic
 * consumers are wired to it.</p>
 *
 * <p>This class owns no parser, scene, renderer, storage, transport, phone surface,
 * deployment, or P0 recovery action. Source policy is not consumer wiring or runtime
 * proof.</p>
 */
public final class HeartbeatInvisibleSemanticControlPolicy {
    public static final int ZERO_WIDTH_SPACE = 0x200B;
    public static final int WORD_JOINER = 0x2060;
    public static final int BYTE_ORDER_MARK = 0xFEFF;

    public static final String REJECTION_BOUNDARY =
            "Heartbeat semantic text contains an invisible presentation control.";

    private HeartbeatInvisibleSemanticControlPolicy() {
    }

    /**
     * True when text contains one of the three invisible presentation aliases this
     * policy owns. Null/empty text is not a violation here; required-field semantics
     * remain with the existing parser/typed source gate.
     */
    public static boolean containsForbiddenInvisibleControl(String value) {
        if (value == null || value.isEmpty()) return false;
        for (int index = 0; index < value.length();) {
            int codePoint = value.codePointAt(index);
            if (isForbiddenInvisibleControl(codePoint)) return true;
            index += Character.charCount(codePoint);
        }
        return false;
    }

    /**
     * Composition-ready semantic safety check. Existing ISO/bidi/surrogate safety
     * remains authoritative; this policy contributes only its additional narrow
     * invisible-control boundary.
     */
    public static boolean isSafeOperatorSemanticText(String value) {
        return HeartbeatSkillPolicy.isSafeSemanticText(value)
                && !containsForbiddenInvisibleControl(value);
    }

    public static boolean isForbiddenInvisibleControl(int codePoint) {
        return codePoint == ZERO_WIDTH_SPACE
                || codePoint == WORD_JOINER
                || codePoint == BYTE_ORDER_MARK;
    }
}
