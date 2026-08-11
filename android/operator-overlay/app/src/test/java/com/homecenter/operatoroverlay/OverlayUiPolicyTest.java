package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class OverlayUiPolicyTest {
    @Test
    public void gestureThresholdSeparatesTapFromDrag() {
        assertTrue(OverlayUiPolicy.isClick(3f, 4f, 8));
        assertFalse(OverlayUiPolicy.isDrag(3f, 4f, 8));
        assertTrue(OverlayUiPolicy.isDrag(8f, 0f, 8));
        assertFalse(OverlayUiPolicy.isClick(8f, 0f, 8));
    }

    @Test
    public void dragArbitrationWorksInBothAxes() {
        assertTrue(OverlayUiPolicy.isDrag(0f, -9f, 8));
        assertTrue(OverlayUiPolicy.isDrag(-9f, 0f, 8));
        assertFalse(OverlayUiPolicy.isDrag(5f, 5f, 8));
    }

    @Test
    public void hideAndRestoreAreExplicitTransitions() {
        assertTrue(OverlayUiPolicy.nextHidden(false, OverlayUiPolicy.VisibilityAction.HIDE));
        assertFalse(OverlayUiPolicy.nextHidden(true, OverlayUiPolicy.VisibilityAction.RESTORE));
    }

    @Test
    public void edgeSnapChoosesNearestSafeEdge() {
        assertTrue(OverlayUiPolicy.snapToNearestHorizontalEdge(100, 8, 652) == 8);
        assertTrue(OverlayUiPolicy.snapToNearestHorizontalEdge(600, 8, 652) == 652);
    }

    @Test
    public void autoCollapseWaitsForIdleAndNeverInterruptsDriving() {
        assertTrue(OverlayUiPolicy.shouldAutoCollapse(false, false, 8000L, 8000L));
        assertFalse(OverlayUiPolicy.shouldAutoCollapse(true, false, 8000L, 8000L));
        assertFalse(OverlayUiPolicy.shouldAutoCollapse(false, true, 9000L, 8000L));
        assertFalse(OverlayUiPolicy.shouldAutoCollapse(false, false, 7999L, 8000L));
    }

    @Test
    public void positionClampsToInsetsAndEveryEdge() {
        assertArrayEquals(
                new int[]{8, 32},
                OverlayUiPolicy.clampPosition(-100, -100, 0, 24, 1080, 1896, 420, 220, 8));
        assertArrayEquals(
                new int[]{652, 1668},
                OverlayUiPolicy.clampPosition(5000, 5000, 0, 24, 1080, 1896, 420, 220, 8));
    }

    @Test
    public void oversizedPanelStillLeavesLocalEscapeCornerReachable() {
        assertArrayEquals(
                new int[]{12, 12},
                OverlayUiPolicy.clampPosition(800, 900, 0, 0, 320, 480, 800, 900, 12));
    }
}
