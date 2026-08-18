package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatDetailSurfacePolicyTest {
    @Test
    public void longExplicitDetailRemainsExactAndScrollInspectable() {
        String detail = "Skill Regnet, fault. Why: source review. Consequence: boundary held. "
                + "Evidence: exact source identity remains visible after several lines of operator detail. "
                + "Source: repository skill skills/regnet/SKILL.md.";

        HeartbeatDetailSurfacePolicy.Presentation presentation =
                HeartbeatDetailSurfacePolicy.fromDetail(detail);

        assertEquals(detail, presentation.text);
        assertEquals(detail, presentation.contentDescription);
        assertEquals(HeartbeatDetailSurfacePolicy.MAX_VISIBLE_LINES, presentation.maxVisibleLines);
        assertFalse(presentation.ellipsizeEnd);
        assertTrue(presentation.verticallyScrollable);
        assertEquals(OverlayUiPolicy.MIN_TOUCH_TARGET_DP, presentation.minTouchTargetDp);
    }

    @Test
    public void touchScrollableDetailDoesNotClaimKeyboardOrClickOwnership() {
        HeartbeatDetailSurfacePolicy.Presentation presentation =
                HeartbeatDetailSurfacePolicy.fromDetail(
                        "Why: inspect. Consequence: full detail remains touch-scrollable.");

        assertTrue(presentation.verticallyScrollable);
        assertFalse(presentation.keyboardFocusable);
        assertFalse(presentation.clickable);
        assertFalse(presentation.longClickable);
    }

    @Test
    public void emptyDetailUsesOneDeterministicInspectableFallback() {
        HeartbeatDetailSurfacePolicy.Presentation presentation =
                HeartbeatDetailSurfacePolicy.fromDetail("   ");

        assertEquals(HeartbeatDetailSurfacePolicy.EMPTY_DETAIL, presentation.text);
        assertEquals(presentation.text, presentation.contentDescription);
        assertFalse(presentation.ellipsizeEnd);
        assertTrue(presentation.verticallyScrollable);
    }

    @Test
    public void viewportPolicyDoesNotRewriteInteriorUnicodeOrEvidence() {
        String detail = "Why: warm\u200Bwall. Evidence: 👩‍💻 exact. Source: swan/veil.";

        HeartbeatDetailSurfacePolicy.Presentation presentation =
                HeartbeatDetailSurfacePolicy.fromDetail("  " + detail + "  ");

        assertEquals(detail, presentation.text);
        assertEquals(detail, presentation.contentDescription);
    }

    @Test
    public void fiveLineSpatialBudgetConvertsToPixelHeight() {
        assertEquals(
                108,
                HeartbeatDetailSurfacePolicy.maxViewportHeightPx(20, 8));
    }

    @Test
    public void viewportHeightPolicyFailsClosedForNegativeDimensions() {
        assertEquals(0, HeartbeatDetailSurfacePolicy.maxViewportHeightPx(-1, -1));
        assertEquals(8, HeartbeatDetailSurfacePolicy.maxViewportHeightPx(-1, 8));
    }

    @Test
    public void viewportHeightPolicyUsesOverflowSafeArithmetic() {
        assertEquals(
                Integer.MAX_VALUE,
                HeartbeatDetailSurfacePolicy.maxViewportHeightPx(
                        Integer.MAX_VALUE,
                        Integer.MAX_VALUE));
    }

    @Test
    public void backgroundRefreshPreservesLegalReadingPosition() {
        assertEquals(120, HeartbeatDetailSurfacePolicy.clampScrollY(120, 1000, 300));
    }

    @Test
    public void shorterRefreshedDetailClampsOldReadingPositionToNewBottom() {
        assertEquals(700, HeartbeatDetailSurfacePolicy.clampScrollY(900, 1000, 300));
        assertEquals(40, HeartbeatDetailSurfacePolicy.clampScrollY(500, 340, 300));
    }

    @Test
    public void nonOverflowingOrNegativeReadingPositionCollapsesToTop() {
        assertEquals(0, HeartbeatDetailSurfacePolicy.clampScrollY(90, 200, 300));
        assertEquals(0, HeartbeatDetailSurfacePolicy.clampScrollY(-20, 1000, 300));
        assertEquals(0, HeartbeatDetailSurfacePolicy.clampScrollY(90, -1, 300));
    }

    @Test
    public void clampUsesOverflowSafeArithmeticAtIntegerEdges() {
        assertEquals(
                Integer.MAX_VALUE,
                HeartbeatDetailSurfacePolicy.clampScrollY(
                        Integer.MAX_VALUE,
                        Integer.MAX_VALUE,
                        0));
    }
}