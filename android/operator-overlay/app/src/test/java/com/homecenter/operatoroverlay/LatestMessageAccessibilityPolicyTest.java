package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class LatestMessageAccessibilityPolicyTest {
    @Test
    public void collapsedStateOffersExpandActionAndConfirmation() {
        assertEquals("Expand latest message",
                LatestMessageAccessibilityPolicy.clickActionLabel(false));
        assertEquals("Collapsed",
                LatestMessageAccessibilityPolicy.stateDescription(false));
        assertEquals("Latest message collapsed",
                LatestMessageAccessibilityPolicy.confirmationAnnouncement(false));
    }

    @Test
    public void expandedStateOffersCollapseActionAndConfirmation() {
        assertEquals("Collapse latest message",
                LatestMessageAccessibilityPolicy.clickActionLabel(true));
        assertEquals("Expanded",
                LatestMessageAccessibilityPolicy.stateDescription(true));
        assertEquals("Latest message expanded",
                LatestMessageAccessibilityPolicy.confirmationAnnouncement(true));
    }
}
