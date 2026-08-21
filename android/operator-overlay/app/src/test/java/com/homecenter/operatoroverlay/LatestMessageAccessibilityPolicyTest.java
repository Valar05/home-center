package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class LatestMessageAccessibilityPolicyTest {
    @Test
    public void collapsedStateOffersExpandActionAndSemanticState() {
        assertEquals("Expand latest message",
                LatestMessageAccessibilityPolicy.clickActionLabel(false));
        assertEquals("Collapsed",
                LatestMessageAccessibilityPolicy.stateDescription(false));
        assertEquals(2, LatestMessageAccessibilityPolicy.maxLines(false));
    }

    @Test
    public void expandedStateOffersCollapseActionAndSemanticState() {
        assertEquals("Collapse latest message",
                LatestMessageAccessibilityPolicy.clickActionLabel(true));
        assertEquals("Expanded",
                LatestMessageAccessibilityPolicy.stateDescription(true));
        assertEquals(Integer.MAX_VALUE, LatestMessageAccessibilityPolicy.maxLines(true));
        assertEquals(520, LatestMessageAccessibilityPolicy.expandedMaxHeightDp());
    }

    @Test
    public void expandedInspectionUsesHeightNotFiniteLineAmputation() {
        assertEquals(Integer.MAX_VALUE, LatestMessageAccessibilityPolicy.maxLines(true));
    }
}
