package com.homecenter.operatoroverlay;

import android.content.Context;
import android.widget.ScrollView;

/** Scrolls expanded controls instead of letting large text push them off-screen. */
final class MaxHeightScrollView extends ScrollView {
    private int maxHeightPx = Integer.MAX_VALUE;

    MaxHeightScrollView(Context context) {
        super(context);
        setFillViewport(false);
        setClipToPadding(false);
    }

    void setMaxHeightPx(int value) {
        int bounded = Math.max(1, value);
        if (bounded == maxHeightPx) return;
        maxHeightPx = bounded;
        requestLayout();
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        int incomingMode = MeasureSpec.getMode(heightMeasureSpec);
        int incomingSize = MeasureSpec.getSize(heightMeasureSpec);
        int boundedSize = incomingMode == MeasureSpec.UNSPECIFIED
                ? maxHeightPx
                : Math.min(incomingSize, maxHeightPx);
        int boundedMode = incomingMode == MeasureSpec.EXACTLY
                && incomingSize <= maxHeightPx
                ? MeasureSpec.EXACTLY
                : MeasureSpec.AT_MOST;
        int boundedHeight = MeasureSpec.makeMeasureSpec(boundedSize, boundedMode);
        super.onMeasure(widthMeasureSpec, boundedHeight);
    }
}
