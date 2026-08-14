package com.homecenter.operatoroverlay;

final class OverlayUiPolicy {
    static final int DRAG_THRESHOLD_DP = 8;
    static final int MIN_TOUCH_TARGET_DP = 48;

    enum VisibilityAction {
        HIDE,
        RESTORE
    }

    private OverlayUiPolicy() {}

    static boolean isDrag(float deltaX, float deltaY, int thresholdPx) {
        float distanceSquared = deltaX * deltaX + deltaY * deltaY;
        return distanceSquared >= (float) thresholdPx * thresholdPx;
    }

    static boolean isClick(float deltaX, float deltaY, int thresholdPx) {
        return !isDrag(deltaX, deltaY, thresholdPx);
    }

    static boolean nextHidden(boolean hidden, VisibilityAction action) {
        return action == VisibilityAction.HIDE;
    }

    static int[] clampPosition(
            int proposedX,
            int proposedY,
            int visibleLeft,
            int visibleTop,
            int visibleRight,
            int visibleBottom,
            int overlayWidth,
            int overlayHeight,
            int edgeInset) {
        int minX = visibleLeft + Math.max(0, edgeInset);
        int minY = visibleTop + Math.max(0, edgeInset);
        int maxX = Math.max(minX, visibleRight - Math.max(1, overlayWidth) - edgeInset);
        int maxY = Math.max(minY, visibleBottom - Math.max(1, overlayHeight) - edgeInset);
        return new int[]{clamp(proposedX, minX, maxX), clamp(proposedY, minY, maxY)};
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(value, max));
    }
}
