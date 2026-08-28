package com.homecenter.operatoroverlay;

import android.view.View;

/**
 * Accessibility policy for the full-screen technical touch-interception layer.
 *
 * The guard exists to reserve pointer input during a remote-input lease. It is not
 * operator content, a status surface, or an accessibility control. Exposing it as a
 * focusable semantic node can create a giant false "Remote input active" target even
 * when the guard is transparent or not touchable. Actual state remains available on
 * the existing status, screen badge, and collapsed-owner surfaces.
 */
final class TechnicalTouchGuardAccessibilityPolicy {
    private TechnicalTouchGuardAccessibilityPolicy() {}

    static int importantForAccessibility() {
        return View.IMPORTANT_FOR_ACCESSIBILITY_NO;
    }

    static String contentDescription() {
        return null;
    }
}
