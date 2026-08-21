package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import android.view.View;

import org.junit.Test;

public class TechnicalTouchGuardAccessibilityPolicyTest {
    @Test
    public void technicalInterceptionLayerOwnsNoAccessibilityNode() {
        assertEquals(
                View.IMPORTANT_FOR_ACCESSIBILITY_NO,
                TechnicalTouchGuardAccessibilityPolicy.importantForAccessibility());
        assertNull(TechnicalTouchGuardAccessibilityPolicy.contentDescription());
    }
}
