package com.homecenter.operatoroverlay;

/**
 * Explicit evidence projection for legitimate invisible semantic layout/shaping
 * controls.
 *
 * <p>Invisibility is not itself a rejection reason. Unicode assigns real semantics
 * to several zero-width characters: U+200B can create a word/line-break opportunity,
 * U+2060 prevents a line break, and U+200C/U+200D participate in language/grapheme
 * shaping. U+FEFF also has BOM/legacy ZWNBSP history. A blanket FORMAT-character ban
 * would therefore destroy legitimate text semantics.</p>
 *
 * <p>This policy does not normalize or rewrite canonical heartbeat text. It offers a
 * separate deterministic diagnostic projection that makes selected invisible code
 * points explicit when an operator/reviewer needs exact evidence visibility. The
 * original source string remains authoritative. Existing ISO-control, malformed
 * surrogate, and bidi-direction rejection remains owned by {@link HeartbeatSkillPolicy}.</p>
 *
 * <p>The projection reserves backslash as its marker introducer and doubles literal
 * source backslashes. That makes an actual invisible control distinguishable from
 * source text that merely spells a marker such as {@code \u{200B ZWSP}}. A diagnostic
 * projection that aliases those two sources would be evidence theater.</p>
 *
 * <p>This class owns no parser, acceptance gate, scene, renderer, storage, transport,
 * phone surface, deployment, or P0 recovery action. Source projection is not consumer
 * wiring or runtime proof.</p>
 */
public final class HeartbeatInvisibleSemanticControlPolicy {
    public static final int ZERO_WIDTH_SPACE = 0x200B;
    public static final int ZERO_WIDTH_NON_JOINER = 0x200C;
    public static final int ZERO_WIDTH_JOINER = 0x200D;
    public static final int WORD_JOINER = 0x2060;
    public static final int BYTE_ORDER_MARK = 0xFEFF;

    private HeartbeatInvisibleSemanticControlPolicy() {
    }

    /** True when the text contains an invisible semantic layout/shaping control this policy can reveal. */
    public static boolean containsRevealableInvisibleControl(String value) {
        if (value == null || value.isEmpty()) return false;
        for (int index = 0; index < value.length();) {
            int codePoint = value.codePointAt(index);
            if (isRevealableInvisibleControl(codePoint)) return true;
            index += Character.charCount(codePoint);
        }
        return false;
    }

    /**
     * Separate human-readable evidence projection. Exact source text is not modified;
     * callers must keep the original string as canonical identity/evidence.
     *
     * <p>Literal source backslashes are doubled before marker insertion so the marker
     * namespace is injective for the characters this policy transforms.</p>
     */
    public static String explicitEvidenceProjection(String value) {
        if (value == null || value.isEmpty()) return "";
        StringBuilder out = new StringBuilder(value.length());
        for (int index = 0; index < value.length();) {
            int codePoint = value.codePointAt(index);
            out.append(projectedUnit(codePoint));
            index += Character.charCount(codePoint);
        }
        return out.toString();
    }

    /**
     * Bounded on-demand evidence projection for spoken/detail surfaces.
     *
     * <p>The bound is applied <em>after</em> invisible controls are expanded into
     * explicit markers. A source field that is legal at the parser boundary can grow
     * several times larger when every invisible control becomes a marker; bounding the
     * source before projection would therefore fail to bound the actual TalkBack/detail
     * output.</p>
     *
     * <p>Projection units are atomic. A marker such as {@code \u{200B ZWSP}} and an
     * escaped literal backslash are either emitted whole or not emitted at all, so
     * truncation cannot create a partial marker that aliases some other source text.
     * The exact source string remains separately authoritative.</p>
     */
    public static String boundedEvidenceProjection(String value, int maxCodePoints) {
        if (value == null || value.isEmpty() || maxCodePoints <= 0) return "";
        StringBuilder out = new StringBuilder(Math.min(value.length(), maxCodePoints));
        int projectedCodePoints = 0;
        for (int index = 0; index < value.length();) {
            int codePoint = value.codePointAt(index);
            String unit = projectedUnit(codePoint);
            int unitCodePoints = unit.codePointCount(0, unit.length());
            if (projectedCodePoints + unitCodePoints > maxCodePoints) {
                out.append("… (truncated)");
                break;
            }
            out.append(unit);
            projectedCodePoints += unitCodePoints;
            index += Character.charCount(codePoint);
        }
        return out.toString();
    }

    public static boolean isRevealableInvisibleControl(int codePoint) {
        return markerFor(codePoint) != null;
    }

    private static String projectedUnit(int codePoint) {
        String marker = markerFor(codePoint);
        if (marker != null) return marker;
        if (codePoint == '\\') return "\\\\";
        return new String(Character.toChars(codePoint));
    }

    private static String markerFor(int codePoint) {
        switch (codePoint) {
            case ZERO_WIDTH_SPACE:
                return "\\u{200B ZWSP}";
            case ZERO_WIDTH_NON_JOINER:
                return "\\u{200C ZWNJ}";
            case ZERO_WIDTH_JOINER:
                return "\\u{200D ZWJ}";
            case WORD_JOINER:
                return "\\u{2060 WJ}";
            case BYTE_ORDER_MARK:
                return "\\u{FEFF BOM}";
            default:
                return null;
        }
    }
}
