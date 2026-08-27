package com.homecenter.operatoroverlay;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Hard returned-budget projection for routine/plain heartbeat text.
 *
 * <p>This helper is deliberately separate from explicit evidence projection. Routine
 * visible labels and compact TalkBack speech must not start naming invisible Unicode
 * bookkeeping merely because explicit on-demand evidence can reveal it. The caller's
 * already-canonical source remains untouched; only the returned projection is bounded.</p>
 *
 * <p>When truncation is required, the ellipsis is part of the same hard code-point
 * budget. A caller asking for 64 code points therefore receives at most 64 code points,
 * not 64 source code points plus a 65th-code-point suffix. The retained prefix also ends
 * at a Unicode extended-grapheme-cluster boundary, so truncation does not split combining
 * sequences, emoji modifiers, ZWJ emoji, or regional-indicator flags.</p>
 *
 * <p>Returned-text bounds are not enough by themselves. Legacy/direct source callers can
 * bypass the canonical envelope parser, so this projection also owns a finite UTF-16
 * source-work window before code-point counting or grapheme regex traversal. The window is
 * at least as large as the largest canonical heartbeat semantic field; ordinary typed
 * source therefore keeps its existing behavior, while oversized non-authoritative speech
 * input cannot turn a tiny returned description into an arbitrarily large scan.</p>
 */
final class HeartbeatPlainTextBudget {
    static final int MAX_SOURCE_CODE_UNITS = HeartbeatEnvelopeParser.MAX_EVIDENCE_BOUNDARY_CHARS;

    private static final String ELLIPSIS = "…";
    private static final int ELLIPSIS_CODE_POINTS = 1;
    private static final Pattern EXTENDED_GRAPHEME = Pattern.compile("\\X");

    private HeartbeatPlainTextBudget() {
    }

    static String boundedWithEllipsis(String value, int maxCodePoints) {
        if (value == null || value.isEmpty() || maxCodePoints <= 0) return "";

        int sourceEnd = Math.min(value.length(), MAX_SOURCE_CODE_UNITS);
        if (sourceEnd < value.length()
                && sourceEnd > 0
                && Character.isHighSurrogate(value.charAt(sourceEnd - 1))
                && Character.isLowSurrogate(value.charAt(sourceEnd))) {
            sourceEnd--;
        }
        boolean sourceTruncated = sourceEnd < value.length();
        String workValue = sourceTruncated ? value.substring(0, sourceEnd) : value;

        int codePoints = workValue.codePointCount(0, workValue.length());
        if (!sourceTruncated && codePoints <= maxCodePoints) return value;
        if (maxCodePoints <= ELLIPSIS_CODE_POINTS) return ELLIPSIS;

        int contentBudget = maxCodePoints - ELLIPSIS_CODE_POINTS;
        int usedCodePoints = 0;
        int end = 0;
        Matcher graphemes = EXTENDED_GRAPHEME.matcher(workValue);
        while (graphemes.find()) {
            int clusterCodePoints = workValue.codePointCount(graphemes.start(), graphemes.end());
            if (usedCodePoints + clusterCodePoints > contentBudget) break;
            usedCodePoints += clusterCodePoints;
            end = graphemes.end();
        }
        return workValue.substring(0, end) + ELLIPSIS;
    }
}
