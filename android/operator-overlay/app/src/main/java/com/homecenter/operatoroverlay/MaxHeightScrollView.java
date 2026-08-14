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
        int boundedHeight = MeasureSpec.makeMeasureSpec(maxHeightPx, MeasureSpec.AT_MOST);
        super.onMeasure(widthMeasureSpec, boundedHeight);
    }
}
