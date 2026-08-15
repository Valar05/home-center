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
        public final HeartbeatSkillPolicy.State state;
        public final String consequence;
        public final int focusIndex;
        public final int touchTargetDp;
        public final String stateToken;
        public final String contentDescription;
        public final boolean transitionMotion;

        private Node(
                HeartbeatSkillPolicy.Candidate candidate,
                int focusIndex,
                boolean transitionMotion) {
            this.id = candidate.id;
            this.label = candidate.label;
            this.state = candidate.state;
            this.consequence = candidate.consequence;
            this.focusIndex = focusIndex;
            this.touchTargetDp = MIN_TOUCH_TARGET_DP;
            this.stateToken = tokenFor(candidate.state);
            this.contentDescription = HeartbeatSkillPolicy.contentDescription(candidate);
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
        /** True only when at least one node changed state or consequence. */
        public final boolean transitionMotionAllowed;

        private Frame(
                String visiblePulseId,
                String attemptedPulseId,
                List<Node> nodes,
                boolean refreshInterrupted,
                boolean transitionMotionAllowed) {
            this.visiblePulseId = clean(visiblePulseId);
            this.attemptedPulseId = clean(attemptedPulseId);
            this.nodes = Collections.unmodifiableList(new ArrayList<>(nodes));
            this.refreshInterrupted = refreshInterrupted;
            this.transitionMotionAllowed = transitionMotionAllowed;
        }

        public String interruptedRefreshDescription() {
            if (!refreshInterrupted) return "";
            if (visiblePulseId.isEmpty()) {
                return "Heartbeat refresh interrupted. No complete heartbeat is available.";
            }
            return "Heartbeat refresh interrupted. Showing last complete heartbeat "
                    + visiblePulseId + ".";
        }
    }

    private HeartbeatSceneGraph() {
    }

    /**
     * Build the next semantic frame.
     *
     * If the pulse is incomplete, the last complete frame is preserved instead of
     * replacing it with partial or aspirational state. No animation is permitted
     * for an interrupted refresh.
     */
    public static Frame build(
            String pulseId,
            List<HeartbeatSkillPolicy.Candidate> candidates,
            boolean pulseComplete,
            Frame lastGood) {
        String attempted = clean(pulseId);
        if (!pulseComplete) {
            if (lastGood == null) {
                return new Frame("", attempted, Collections.emptyList(), true, false);
            }
            return new Frame(
                    lastGood.visiblePulseId,
                    attempted,
                    lastGood.nodes,
                    true,
                    false);
        }

        List<HeartbeatSkillPolicy.Candidate> selected =
                HeartbeatSkillPolicy.selectMaterialLights(candidates);
        Map<String, Node> previous = indexById(lastGood);
        List<Node> nodes = new ArrayList<>();
        boolean anyTransition = false;

        for (int index = 0; index < selected.size(); index++) {
            HeartbeatSkillPolicy.Candidate candidate = selected.get(index);
            Node prior = previous.get(candidate.id.toLowerCase(java.util.Locale.ROOT));
            boolean changed = prior == null
                    || prior.state != candidate.state
                    || !prior.consequence.equals(candidate.consequence);
            anyTransition |= changed;
            nodes.add(new Node(candidate, index, changed));
        }

        return new Frame(attempted, attempted, nodes, false, anyTransition);
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
