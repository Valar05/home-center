package com.homecenter.operatoroverlay;

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
 * not 64 source code points plus a 65th-code-point suffix.</p>
 */
final class HeartbeatPlainTextBudget {
    private static final String ELLIPSIS = "…";
    private static final int ELLIPSIS_CODE_POINTS = 1;

    private HeartbeatPlainTextBudget() {
    }

    static String boundedWithEllipsis(String value, int maxCodePoints) {
        if (value == null || value.isEmpty() || maxCodePoints <= 0) return "";

        int codePoints = value.codePointCount(0, value.length());
        if (codePoints <= maxCodePoints) return value;
        if (maxCodePoints <= ELLIPSIS_CODE_POINTS) return ELLIPSIS;

        int contentBudget = maxCodePoints - ELLIPSIS_CODE_POINTS;
        int end = value.offsetByCodePoints(0, contentBudget);
        return value.substring(0, end) + ELLIPSIS;
    }
}
