package com.homecenter.ritsucontrol;

/** Pure inset arithmetic for Android 15+ edge-to-edge + IME safe footer. */
final class SafeInsets {
    static int bottom(int navigation, int keyboard) {
        return Math.max(0, Math.max(navigation, keyboard));
    }
    static int top(int statusBar, int displayCutout) {
        return Math.max(0, Math.max(statusBar, displayCutout));
    }
    private SafeInsets() {}
}
