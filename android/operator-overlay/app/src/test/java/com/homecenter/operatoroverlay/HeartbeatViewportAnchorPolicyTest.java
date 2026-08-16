package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

/**
 * Source-only regression fixtures for the horizontal semantic viewport anchor.
 * These tests do not prove Android execution, TalkBack focus retention, deployment,
 * or phone delivery until an authorized test body actually runs them.
 */
public class HeartbeatViewportAnchorPolicyTest {
    @Test
    public void widerPrecedingContentKeepsAnchorAtSameViewportOffset() {
        // The semantic anchor was 36 px inside the viewport. A wider sibling moves
        // its content-left edge from 180 to 260. The viewport should move by the
        // same 80 px so the anchored control stays visually stationary.
        assertEquals(224, HeartbeatOverlayRefreshPlan.anchoredScrollX(260, 36, 600));
    }

    @Test
    public void unchangedGeometryDoesNotManufactureScrollMotion() {
        assertEquals(144, HeartbeatOverlayRefreshPlan.anchoredScrollX(180, 36, 600));
    }

    @Test
    public void anchorNearLeadingEdgeClampsWithoutNegativeScroll() {
        assertEquals(0, HeartbeatOverlayRefreshPlan.anchoredScrollX(20, 36, 600));
    }

    @Test
    public void anchorPastTrailingEdgeClampsToCurrentScrollRange() {
        assertEquals(320, HeartbeatOverlayRefreshPlan.anchoredScrollX(900, 36, 320));
    }

    @Test
    public void negativeOrMissingScrollRangeFailsClosedAtZero() {
        assertEquals(0, HeartbeatOverlayRefreshPlan.anchoredScrollX(900, 36, -1));
    }

    @Test
    public void arithmeticCannotOverflowIntoNegativeScroll() {
        assertEquals(
                Integer.MAX_VALUE,
                HeartbeatOverlayRefreshPlan.anchoredScrollX(
                        Integer.MAX_VALUE,
                        Integer.MIN_VALUE,
                        Integer.MAX_VALUE));
    }
}
