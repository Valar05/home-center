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
    /** Same first-class touch floor used by the rest of the Operator Overlay. */
    public static final int MIN_TOUCH_TARGET_DP = 48;
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

        private Presentation(String text) {
            this.text = text;
            this.contentDescription = text;
            this.maxVisibleLines = MAX_VISIBLE_LINES;
            this.ellipsizeEnd = false;
            this.verticallyScrollable = true;
            this.minTouchTargetDp = MIN_TOUCH_TARGET_DP;
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
}
