package com.homecenter.ritsucontrol;

import static org.junit.Assert.*;
import org.junit.Test;

public final class SafeInsetsTest {
    @Test public void footerClearsGestureNavigationBar() {
        assertEquals(32, SafeInsets.bottom(32, 0));
    }
    @Test public void keyboardMovesFooterAboveImeWithoutDoubleCountingNavBar() {
        assertEquals(760, SafeInsets.bottom(32, 760));
    }
    @Test public void keyboardClosingRestoresNavigationSafeArea() {
        assertEquals(32, SafeInsets.bottom(32, 0));
    }
    @Test public void displayCutoutAndStatusBarKeepHeaderVisible() {
        assertEquals(90, SafeInsets.top(55, 90));
    }
}
