package com.homecenter.operatoroverlay;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Pure source projection from the semantic heartbeat scene into UI-ready controls.
 *
 * <p>This class is deliberately not a renderer, controller, service, transport,
 * phone action, or P0 owner. It exists so the existing Operator Overlay can later
 * consume one deterministic accessible model instead of re-deriving state, touch,
 * speech, and motion semantics inside Android view code.</p>
 */
public final class HeartbeatOverlayViewModel {
    /** Hard returned budget for one visible button label before state framing. */
    public static final int MAX_VISIBLE_LABEL_CODE_POINTS = 72;

    public static final class LightControl {
        public final String id;
        public final String visibleLabel;
        public final String contentDescription;
        public final String detailContentDescription;
        public final int focusIndex;
        public final int minTouchTargetDp;
        public final boolean transitionMotion;

        private LightControl(HeartbeatSceneGraph.Node node) {
            this.id = node.id;
            this.visibleLabel = visibleLabel(node);
            this.contentDescription = node.contentDescription;
            this.detailContentDescription = HeartbeatEvidenceDetailProjection.detailContentDescription(node);
            this.focusIndex = node.focusIndex;
            this.minTouchTargetDp = node.touchTargetDp;
            this.transitionMotion = node.transitionMotion;
        }
    }

    public static final class Model {
        public final String visiblePulseId;
        public final boolean refreshInterrupted;
        /** Exact source-side boundary retained separately from bounded speech projection. */
        public final String refreshBoundary;
        public final boolean transitionMotionAllowed;
        /** True when at least one currently visible node owns this frame's one-shot cue. */
        public final boolean anyNodeTransitionMotion;
        /**
         * True only for a material frame transition with no surviving/added node cue.
         * This is the pure-removal case: the summary is the only remaining native
         * surface capable of honestly representing that structural transition.
         */
        public final boolean summaryTransitionMotion;
        /**
         * Compact attention-only status for surviving collapsed-owner speech.
         * Empty when no blocked/fault light exists; active/recovered breadth remains
         * behind explicit expansion instead of becoming routine action-control speech.
         */
        public final String attentionStatusDescription;
        public final String collapsedContentDescription;
        public final List<LightControl> controls;

        private Model(
                String visiblePulseId,
                boolean refreshInterrupted,
                String refreshBoundary,
                boolean transitionMotionAllowed,
                String attentionStatusDescription,
                String collapsedContentDescription,
                List<LightControl> controls) {
            this.visiblePulseId = raw(visiblePulseId);
            this.refreshInterrupted = refreshInterrupted;
            this.refreshBoundary = raw(refreshBoundary);
            this.transitionMotionAllowed = transitionMotionAllowed;
            this.attentionStatusDescription = raw(attentionStatusDescription);
            this.collapsedContentDescription = raw(collapsedContentDescription);
            this.controls = Collections.unmodifiableList(new ArrayList<>(controls));
            boolean anyNodeMotion = false;
            for (LightControl control : this.controls) {
                anyNodeMotion |= control.transitionMotion;
            }
            this.anyNodeTransitionMotion = anyNodeMotion;
            this.summaryTransitionMotion = transitionMotionAllowed && !anyNodeMotion;
        }

        /** Stable semantic lookup for selection retention across scene reordering. */
        public LightControl controlById(String id) {
            String target = clean(id).toLowerCase(Locale.ROOT);
            if (target.isEmpty()) return null;
            for (LightControl control : controls) {
                if (control.id.toLowerCase(Locale.ROOT).equals(target)) return control;
            }
            return null;
        }

        /**
         * Compact visible summary label derived from actual visible contact truth.
         *
         * <p>An interrupted frame with no visible pulse is a blocked refresh, not
         * "contact held". This distinction matters especially before first contact:
         * a coherent storage-read wound must not claim that an old heartbeat remains
         * visible when none has ever been accepted. A zero-material accepted pulse
         * still has contact because {@code visiblePulseId} is non-empty, so ordinary
         * {@code HEARTBEAT • waiting} is reserved for a model with no visible contact.</p>
         */
        public String summaryVisibleLabel() {
            int count = controls.size();
            boolean hasVisibleContact = hasVisibleContact();
            if (count == 0) {
                if (!refreshInterrupted) {
                    return hasVisibleContact
                            ? "HEARTBEAT • 0 LIGHTS"
                            : "HEARTBEAT • waiting";
                }
                return hasVisibleContact
                        ? "HEARTBEAT • CONTACT HELD"
                        : "HEARTBEAT • REFRESH BLOCKED";
            }
            return "HEARTBEAT • " + count + " LIGHT" + (count == 1 ? "" : "S")
                    + (refreshInterrupted && hasVisibleContact ? " • CONTACT HELD" : "");
        }

        /**
         * Detail prose for an interrupted refresh, derived from the same visible-contact
         * truth as the summary. This prevents a pre-contact storage/read/projection wound
         * from claiming that a last-good heartbeat is being held when no pulse has ever
         * been accepted into the visible scene.
         */
        public String interruptionDetailContentDescription() {
            if (!refreshInterrupted) return "";
            if (hasVisibleContact()) {
                return "Refresh rejected. Last good heartbeat contact is preserved; "
                        + "no discarded attempted light is current.";
            }
            return "Refresh blocked before any heartbeat contact was accepted; "
                    + "no discarded attempted light is current.";
        }

        /**
         * UI-ready one-shot motion decision for one semantic control. The platform
         * animator bit must come from the existing Android owner at the moment it
         * applies the view update; this source model does not query Android settings.
         */
        public HeartbeatNativeMotionPolicy.Decision motionDecisionFor(
                String id,
                boolean heartbeatSurfaceVisible,
                boolean platformAnimatorsEnabled) {
            LightControl control = controlById(id);
            return HeartbeatNativeMotionPolicy.decideNode(
                    control != null && control.transitionMotion,
                    transitionMotionAllowed,
                    heartbeatSurfaceVisible,
                    platformAnimatorsEnabled);
        }

        /**
         * UI-ready fallback for a pure-removal transition where the removed control
         * no longer exists to receive the cue. A later owner may apply this only to
         * the existing heartbeat summary; it must not synthesize a replacement light.
         */
        public HeartbeatNativeMotionPolicy.Decision summaryMotionDecision(
                boolean heartbeatSurfaceVisible,
                boolean platformAnimatorsEnabled) {
            return HeartbeatNativeMotionPolicy.decideSummaryFallback(
                    transitionMotionAllowed,
                    anyNodeTransitionMotion,
                    heartbeatSurfaceVisible,
                    platformAnimatorsEnabled);
        }

        private boolean hasVisibleContact() {
            return !clean(visiblePulseId).isEmpty();
        }
    }

    private HeartbeatOverlayViewModel() {
    }

    /**
     * Project only the already-accepted/preserved scene.
     *
     * <p>When a refresh fails closed, the frame already contains the last-good nodes
     * with motion clamped. This projection must not inspect discarded attempted
     * candidates or invent weaker fallback semantics.</p>
     */
    public static Model fromFrame(HeartbeatSceneGraph.Frame frame) {
        if (frame == null) {
            return new Model(
                    "",
                    true,
                    "Heartbeat scene unavailable.",
                    false,
                    "",
                    "Heartbeat scene unavailable.",
                    Collections.emptyList());
        }

        List<LightControl> controls = new ArrayList<>(frame.nodes.size());
        for (HeartbeatSceneGraph.Node node : frame.nodes) {
            controls.add(new LightControl(node));
        }
        return new Model(
                frame.visiblePulseId,
                frame.refreshInterrupted,
                frame.refreshBoundary,
                frame.transitionMotionAllowed,
                attentionStatusDescription(frame),
                HeartbeatFrameAccessibility.collapsedContentDescription(frame),
                controls);
    }

    private static String attentionStatusDescription(HeartbeatSceneGraph.Frame frame) {
        if (frame == null || frame.nodes.isEmpty()) return "";
        int blocked = 0;
        int fault = 0;
        for (HeartbeatSceneGraph.Node node : frame.nodes) {
            if (node.state == HeartbeatSkillPolicy.State.BLOCKED) blocked++;
            else if (node.state == HeartbeatSkillPolicy.State.FAULT) fault++;
        }
        if (blocked == 0 && fault == 0) return "";
        return "Attention: blocked " + blocked + ", fault " + fault + ".";
    }

    private static String visibleLabel(HeartbeatSceneGraph.Node node) {
        String label = boundedLabel(node.label);
        String state = node.state == null
                ? "unknown"
                : node.state.name().toLowerCase(Locale.ROOT);
        return node.stateToken + " " + label + " — " + state;
    }

    private static String boundedLabel(String value) {
        return HeartbeatPlainTextBudget.boundedWithEllipsis(
                clean(value),
                MAX_VISIBLE_LABEL_CODE_POINTS);
    }

    private static String raw(String value) {
        return value == null ? "" : value;
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
