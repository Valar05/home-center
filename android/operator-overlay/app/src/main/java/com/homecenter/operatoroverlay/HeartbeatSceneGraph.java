package com.homecenter.operatoroverlay;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Pure, non-rendering scene specimen for heartbeat skill lights.
 *
 * This class deliberately does not own the overlay, transport, or phone runtime.
 * It converts {@link HeartbeatSkillPolicy} output into a deterministic semantic
 * scene that an existing renderer may consume later.
 */
public final class HeartbeatSceneGraph {
    public static final int MIN_TOUCH_TARGET_DP = 48;

    public static final class Node {
        public final String id;
        public final String label;
        public final String provenanceKind;
        public final String provenanceLocator;
        public final String activationReason;
        public final HeartbeatSkillPolicy.State state;
        public final String consequence;
        public final String evidenceBoundary;
        public final int focusIndex;
        public final int touchTargetDp;
        public final String stateToken;
        public final String contentDescription;
        public final String detailContentDescription;
        public final boolean transitionMotion;

        private Node(
                HeartbeatSkillPolicy.Candidate candidate,
                int focusIndex,
                boolean transitionMotion) {
            this.id = candidate.id;
            this.label = candidate.label;
            this.provenanceKind = candidate.provenanceKind;
            this.provenanceLocator = candidate.provenanceLocator;
            this.activationReason = candidate.activationReason;
            this.state = candidate.state;
            this.consequence = candidate.consequence;
            this.evidenceBoundary = candidate.evidenceBoundary;
            this.focusIndex = focusIndex;
            this.touchTargetDp = MIN_TOUCH_TARGET_DP;
            this.stateToken = tokenFor(candidate.state);
            this.contentDescription = HeartbeatSkillPolicy.contentDescription(candidate);
            this.detailContentDescription = HeartbeatSkillPolicy.detailContentDescription(candidate);
            this.transitionMotion = transitionMotion;
        }
    }

    public static final class Frame {
        /** Last complete pulse that remains visible. */
        public final String visiblePulseId;
        /** Pulse currently being attempted; differs when refresh was interrupted. */
        public final String attemptedPulseId;
        public final List<Node> nodes;
        public final boolean refreshInterrupted;
        /** Exact source-side reason why an attempted refresh was rejected. */
        public final String refreshBoundary;
        /** True only when a node was added/removed or changed state/consequence. */
        public final boolean transitionMotionAllowed;

        private Frame(
                String visiblePulseId,
                String attemptedPulseId,
                List<Node> nodes,
                boolean refreshInterrupted,
                String refreshBoundary,
                boolean transitionMotionAllowed) {
            this.visiblePulseId = clean(visiblePulseId);
            this.attemptedPulseId = clean(attemptedPulseId);
            this.nodes = Collections.unmodifiableList(new ArrayList<>(nodes));
            this.refreshInterrupted = refreshInterrupted;
            this.refreshBoundary = clean(refreshBoundary);
            this.transitionMotionAllowed = transitionMotionAllowed;
        }

        public String interruptedRefreshDescription() {
            if (!refreshInterrupted) return "";
            String boundary = refreshBoundary.isEmpty() ? "" : " Boundary: " + refreshBoundary;
            if (visiblePulseId.isEmpty()) {
                return "Heartbeat refresh interrupted. No complete heartbeat is available." + boundary;
            }
            return "Heartbeat refresh interrupted. Showing last complete heartbeat "
                    + visiblePulseId + "." + boundary;
        }
    }

    private HeartbeatSceneGraph() {
    }

    /**
     * Build the next semantic frame.
     *
     * Incomplete or semantically invalid pulses preserve the last complete frame
     * instead of replacing it with partial, anonymous, or untyped state. No motion
     * is permitted for a rejected refresh.
     */
    public static Frame build(
            String pulseId,
            List<HeartbeatSkillPolicy.Candidate> candidates,
            boolean pulseComplete,
            Frame lastGood) {
        String attempted = clean(pulseId);
        if (!pulseComplete) {
            return preserveLastGood(attempted, lastGood, "Pulse is incomplete.");
        }
        if (attempted.isEmpty()) {
            return preserveLastGood("", lastGood, "Pulse identity is missing.");
        }

        List<HeartbeatSkillPolicy.Candidate> material =
                HeartbeatSkillPolicy.selectMaterialLights(candidates);
        List<HeartbeatSkillPolicy.Candidate> selected =
                HeartbeatSkillPolicy.selectDisplayReadyLights(candidates);
        if (material.size() != selected.size()) {
            return preserveLastGood(
                    attempted,
                    lastGood,
                    "At least one material light lacks the complete typed source/evidence contract.");
        }

        Map<String, Node> previous = indexById(lastGood);
        List<Node> nodes = new ArrayList<>();
        boolean anyTransition = previous.size() != selected.size();

        for (int index = 0; index < selected.size(); index++) {
            HeartbeatSkillPolicy.Candidate candidate = selected.get(index);
            Node prior = previous.get(candidate.id.toLowerCase(java.util.Locale.ROOT));
            boolean changed = prior == null
                    || prior.state != candidate.state
                    || !prior.consequence.equals(candidate.consequence);
            anyTransition |= changed;
            nodes.add(new Node(candidate, index, changed));
        }

        return new Frame(attempted, attempted, nodes, false, "", anyTransition);
    }

    private static Frame preserveLastGood(String attempted, Frame lastGood, String boundary) {
        if (lastGood == null) {
            return new Frame(
                    "",
                    attempted,
                    Collections.emptyList(),
                    true,
                    boundary,
                    false);
        }
        return new Frame(
                lastGood.visiblePulseId,
                attempted,
                lastGood.nodes,
                true,
                boundary,
                false);
    }

    private static Map<String, Node> indexById(Frame frame) {
        if (frame == null || frame.nodes.isEmpty()) return Collections.emptyMap();
        Map<String, Node> byId = new HashMap<>();
        for (Node node : frame.nodes) {
            byId.put(node.id.toLowerCase(java.util.Locale.ROOT), node);
        }
        return byId;
    }

    private static String tokenFor(HeartbeatSkillPolicy.State state) {
        if (state == null) return "·";
        switch (state) {
            case ACTIVE:
                return "●";
            case BLOCKED:
                return "□";
            case FAULT:
                return "×";
            case RECOVERED:
                return "◇";
            case DARK:
            default:
                return "·";
        }
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
