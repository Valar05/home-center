package com.homecenter.operatoroverlay;

/**
 * Pure source policy for the existing Operator Overlay heartbeat detail surface.
 *
 * <p>Explicit detail already contains the bounded Why / Consequence / Evidence /
 * Source projection. The native owner must not destructively ellipsize that text
 * merely to keep the overlay spatially bounded. Instead, one bounded-height detail
 * viewport keeps the exact projected detail and makes overflow vertically
 * inspectable by touch.</p>
 *
 * <p>This class owns no Android View, renderer, controller, storage, transport,
 * phone surface, deployment, or P0 action. {@code OperatorOverlayService} remains
 * the sole native owner.</p>
 */
public final class HeartbeatDetailSurfacePolicy {
    /** Keep the visible detail well compact while overflow remains scroll-inspectable. */
    public static final int MAX_VISIBLE_LINES = 5;
    /** Reuse the overlay's existing first-class touch floor rather than drifting a duplicate literal. */
    public static final int MIN_TOUCH_TARGET_DP = OverlayUiPolicy.MIN_TOUCH_TARGET_DP;
    /** Passive detail is not part of direct keyboard-focus ownership. */
    public static final boolean KEYBOARD_FOCUSABLE = false;
    /** Passive detail scrolling is not a click action. */
    public static final boolean CLICKABLE = false;
    /** Passive detail scrolling does not expose a long-click action. */
    public static final boolean LONG_CLICKABLE = false;
    public static final String EMPTY_DETAIL = "No heartbeat detail available.";

    public static final class Presentation {
        /** Full projected detail; never shortened merely to fit the visible viewport. */
        public final String text;
        /** TalkBack receives the same full explicit detail. */
        public final String contentDescription;
        public final int maxVisibleLines;
        /** END ellipsis would make omitted visible evidence unreachable by sight/touch. */
        public final boolean ellipsizeEnd;
        /** Overflow is inspectable inside the bounded existing detail surface. */
        public final boolean verticallyScrollable;
        public final int minTouchTargetDp;
        /**
         * The detail well is not a keyboard-focus owner. Android movement-method wiring
         * may mutate focus/click state, so the existing owner must explicitly restore
         * these values after installing or changing the movement method.
         */
        public final boolean keyboardFocusable;
        /** Passive touch scrolling does not turn the detail well into a click action. */
        public final boolean clickable;
        /** Passive touch scrolling does not grow a long-click action either. */
        public final boolean longClickable;

        private Presentation(String text) {
            this.text = text;
            this.contentDescription = text;
            this.maxVisibleLines = MAX_VISIBLE_LINES;
            this.ellipsizeEnd = false;
            this.verticallyScrollable = true;
            this.minTouchTargetDp = MIN_TOUCH_TARGET_DP;
            this.keyboardFocusable = KEYBOARD_FOCUSABLE;
            this.clickable = CLICKABLE;
            this.longClickable = LONG_CLICKABLE;
        }
    }

    private HeartbeatDetailSurfacePolicy() {
    }

    /**
     * Project one already-bounded explicit detail into native surface semantics.
     *
     * <p>The existing owner historically trims surrounding whitespace before
     * display/announcement, so this helper preserves that established behavior. It
     * never truncates the remaining text or invents a second evidence formatter.</p>
     */
    public static Presentation fromDetail(String detail) {
        String clean = detail == null ? "" : detail.trim();
        return new Presentation(clean.isEmpty() ? EMPTY_DETAIL : clean);
    }

    /**
     * Preserve a reader's vertical position only while that position still exists
     * in the refreshed detail layout.
     *
     * <p>The owner calls this after layout because refreshed evidence may be shorter
     * than the prior detail. Negative positions and non-overflowing layouts collapse
     * to zero. Long arithmetic avoids integer overflow while deriving the legal
     * maximum.</p>
     */
    public static int clampScrollY(
            int requestedScrollY,
            int contentHeightPx,
            int viewportHeightPx) {
        long requested = Math.max(0L, (long) requestedScrollY);
        long content = Math.max(0L, (long) contentHeightPx);
        long viewport = Math.max(0L, (long) viewportHeightPx);
        long maxScroll = Math.max(0L, content - viewport);
        return (int) Math.min(requested, Math.min(maxScroll, Integer.MAX_VALUE));
    }
}
