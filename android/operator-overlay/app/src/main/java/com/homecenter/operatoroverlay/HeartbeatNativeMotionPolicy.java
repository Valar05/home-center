package com.homecenter.operatoroverlay;

/**
 * Pure decision policy for one-shot native heartbeat motion.
 *
 * <p>This class deliberately does not animate Android views. It turns semantic scene
 * motion truth plus presentation/accessibility gates into an explicit decision that
 * the existing {@code OperatorOverlayService} may consume. Source policy is not
 * runtime proof.</p>
 */
public final class HeartbeatNativeMotionPolicy {
    public static final long ONE_SHOT_DURATION_MS = 140L;
    public static final float ONE_SHOT_START_SCALE = 0.96f;
    public static final float ONE_SHOT_START_ALPHA = 0.72f;

    public enum Boundary {
        MATERIAL_TRANSITION,
        NODE_HAS_NO_TRANSITION,
        FRAME_MOTION_CLAMPED,
        SURFACE_NOT_PRESENTED,
        PLATFORM_ANIMATORS_DISABLED
    }

    public static final class Decision {
        public final boolean animate;
        public final Boundary boundary;
        public final long durationMs;
        public final float startScale;
        public final float startAlpha;

        private Decision(boolean animate, Boundary boundary) {
            this.animate = animate;
            this.boundary = boundary;
            this.durationMs = ONE_SHOT_DURATION_MS;
            this.startScale = ONE_SHOT_START_SCALE;
            this.startAlpha = ONE_SHOT_START_ALPHA;
        }
    }

    private HeartbeatNativeMotionPolicy() {
    }

    /**
     * Decide whether one semantic node may receive one bounded native motion cue.
     *
     * <p>Every gate is required. In particular, a semantic transition discovered while
     * the heartbeat surface is collapsed/hidden advances history silently; revealing
     * the surface later must not replay old motion. Platform animation disablement is
     * also authoritative and must not be routed around.</p>
     */
    public static Decision decideNode(
            boolean nodeTransitionMotion,
            boolean frameTransitionMotionAllowed,
            boolean heartbeatSurfaceVisible,
            boolean platformAnimatorsEnabled) {
        if (!nodeTransitionMotion) {
            return new Decision(false, Boundary.NODE_HAS_NO_TRANSITION);
        }
        if (!frameTransitionMotionAllowed) {
            return new Decision(false, Boundary.FRAME_MOTION_CLAMPED);
        }
        if (!heartbeatSurfaceVisible) {
            return new Decision(false, Boundary.SURFACE_NOT_PRESENTED);
        }
        if (!platformAnimatorsEnabled) {
            return new Decision(false, Boundary.PLATFORM_ANIMATORS_DISABLED);
        }
        return new Decision(true, Boundary.MATERIAL_TRANSITION);
    }

    /**
     * A pure removal changes frame structure but leaves no removed node to animate.
     * In that narrow case the existing heartbeat summary may receive the one-shot cue
     * instead. Additions and state/consequence changes already have at least one node
     * transition and therefore do not also pulse the summary.
     */
    public static Decision decideSummaryFallback(
            boolean frameTransitionMotionAllowed,
            boolean anyNodeTransitionMotion,
            boolean heartbeatSurfaceVisible,
            boolean platformAnimatorsEnabled) {
        if (!frameTransitionMotionAllowed || anyNodeTransitionMotion) {
            return new Decision(false, Boundary.NODE_HAS_NO_TRANSITION);
        }
        if (!heartbeatSurfaceVisible) {
            return new Decision(false, Boundary.SURFACE_NOT_PRESENTED);
        }
        if (!platformAnimatorsEnabled) {
            return new Decision(false, Boundary.PLATFORM_ANIMATORS_DISABLED);
        }
        return new Decision(true, Boundary.MATERIAL_TRANSITION);
    }
}
