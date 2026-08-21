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
    }

    @Test
    public void expandedStateOffersCollapseActionAndSemanticState() {
        assertEquals("Collapse latest message",
                LatestMessageAccessibilityPolicy.clickActionLabel(true));
        assertEquals("Expanded",
                LatestMessageAccessibilityPolicy.stateDescription(true));
    }
}
