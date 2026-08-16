package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

/**
 * Source-only regression fixtures for the horizontal semantic viewport anchor.
 * These tests do not prove Android execution, TalkBack focus retention, deployment,
 * or phone delivery until an authorized test body actually runs them.
 */
public class HeartbeatViewportAnchorPolicyTest {
    private static HeartbeatSkillPolicy.Candidate typed(String id) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "doctrine",
                "fixture:" + id,
                "Materially active in viewport fixture",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Viewport contact matters",
                "Source-only fixture");
    }

    private static HeartbeatOverlayViewModel.Model model(String... ids) {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "viewport-pulse",
                ids.length == 0
                        ? Collections.emptyList()
                        : Arrays.asList(Arrays.stream(ids).map(HeartbeatViewportAnchorPolicyTest::typed).toArray(HeartbeatSkillPolicy.Candidate[]::new)),
                true,
                null);
        return HeartbeatOverlayViewModel.fromFrame(frame);
    }

    @Test
    public void selectedSemanticIdWinsOverKeyboardFocus() {
        assertEquals(
                "selected",
                HeartbeatOverlayRefreshPlan.viewportAnchorId(
                        "SELECTED",
                        "focused",
                        model("selected", "focused")));
    }

    @Test
    public void keyboardFocusIsFallbackWhenSelectionIsMissingOrStale() {
        assertEquals(
                "focused",
                HeartbeatOverlayRefreshPlan.viewportAnchorId(
                        "stale-selection",
                        "FOCUSED",
                        model("focused", "other")));
    }

    @Test
    public void staleSelectionAndFocusFailClosedToNoAnchor() {
        assertEquals(
                "",
                HeartbeatOverlayRefreshPlan.viewportAnchorId(
                        "stale-selection",
                        "stale-focus",
                        model("other")));
    }

    @Test
    public void nullModelCannotManufactureAnAnchor() {
        assertEquals(
                "",
                HeartbeatOverlayRefreshPlan.viewportAnchorId(
                        "selected",
                        "focused",
                        null));
    }

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
