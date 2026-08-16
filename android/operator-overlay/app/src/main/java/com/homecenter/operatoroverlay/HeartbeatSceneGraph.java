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
    /** Spoken interrupted-refresh pulse identity stays bounded; exact frame identity remains unchanged. */
    public static final int MAX_SPOKEN_PULSE_ID_CODE_POINTS = 96;
    /** Spoken rejection boundary stays bounded; exact refreshBoundary remains available as evidence. */
    public static final int MAX_SPOKEN_REFRESH_BOUNDARY_CODE_POINTS = 320;

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

        /**
         * Re-materialize preserved contact while overriding ephemeral motion state.
         * Semantic/touch/TalkBack fields remain byte-for-byte equivalent at the
         * Java String level; an interrupted refresh must not inherit a prior pulse's
         * one-shot animation bit merely because the last-good node object is reused.
         */
        private Node(Node source, boolean transitionMotion) {
            this.id = source.id;
            this.label = source.label;
            this.provenanceKind = source.provenanceKind;
            this.provenanceLocator = source.provenanceLocator;
            this.activationReason = source.activationReason;
            this.state = source.state;
            this.consequence = source.consequence;
            this.evidenceBoundary = source.evidenceBoundary;
            this.focusIndex = source.focusIndex;
            this.touchTargetDp = source.touchTargetDp;
            this.stateToken = source.stateToken;
            this.contentDescription = source.contentDescription;
            this.detailContentDescription = source.detailContentDescription;
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

        /**
         * Human-facing interrupted-refresh projection.
         *
         * Exact visiblePulseId/refreshBoundary fields remain untouched for evidence
         * and checkpoint handling. Speech/display projection is independently bounded
         * by Unicode code point, and an unsafe arbitrary pre-parser boundary is not
         * echoed into TalkBack or operator-visible prose.
         */
        public String interruptedRefreshDescription() {
            if (!refreshInterrupted) return "";
            String spokenBoundary = safeBoundedSpeech(
                    refreshBoundary,
                    MAX_SPOKEN_REFRESH_BOUNDARY_CODE_POINTS,
                    "Heartbeat refresh boundary contains unsafe semantic text.");
            String boundary = spokenBoundary.isEmpty() ? "" : " Boundary: " + spokenBoundary;
            if (visiblePulseId.isEmpty()) {
                return "Heartbeat refresh interrupted. No complete heartbeat is available." + boundary;
            }
            String spokenPulseId = safeBoundedSpeech(
                    visiblePulseId,
                    MAX_SPOKEN_PULSE_ID_CODE_POINTS,
                    "<unsafe pulse identity>");
            return "Heartbeat refresh interrupted. Showing last complete heartbeat "
                    + spokenPulseId + "." + boundary;
        }
    }

    private HeartbeatSceneGraph() {
    }

    /**
     * Compose the canonical parser result into the existing semantic scene.
     * Parser rejection preserves last-good contact and carries the exact parse
     * boundary forward. This remains pure source composition; it does not wire a
     * renderer, transport, phone surface, or P0 owner.
     */
    public static Frame build(HeartbeatEnvelopeParser.Result parsed, Frame lastGood) {
        if (parsed == null) {
            return preserveLastGood("", lastGood, "Heartbeat envelope result is missing.");
        }
        if (!parsed.accepted()) {
            String boundary = parsed.boundary.isEmpty()
                    ? "Heartbeat envelope was rejected."
                    : parsed.boundary;
            return preserveLastGood("", lastGood, boundary);
        }
        if (parsed.pulse == null) {
            return preserveLastGood("", lastGood, "Heartbeat envelope pulse is missing.");
        }
        return build(
                parsed.pulse.pulseId,
                parsed.pulse.candidates,
                parsed.pulse.complete,
                lastGood);
    }

    /**
     * Preserve last-good visible contact for a rejection that happens before the
     * canonical parser can safely produce a pulse (for example persisted-byte/SHA
     * identity failure). This delegates to the same preservation organ used by
     * parser and scene rejection, so all one-shot node motion is re-materialized
     * off and the exact rejection boundary remains visible.
     *
     * <p>An attempted id is diagnostic semantics too. If a pre-parser caller passes
     * an unsafe id containing controls, malformed UTF-16, or directional bidi
     * controls, suppress that id rather than echoing it into a visible/TalkBack frame.
     * The original rejection boundary remains unchanged.</p>
     *
     * <p>This is pure source composition only. It does not own storage, transport,
     * rendering, phone execution, or P0 recovery.</p>
     */
    public static Frame preserveRejectedRefresh(
            String attemptedPulseId,
            Frame lastGood,
            String boundary) {
        String exactBoundary = clean(boundary);
        if (exactBoundary.isEmpty()) exactBoundary = "Heartbeat refresh was rejected.";
        String safeAttempted = HeartbeatSkillPolicy.isSafeSemanticText(attemptedPulseId)
                ? attemptedPulseId
                : "";
        return preserveLastGood(safeAttempted, lastGood, exactBoundary);
    }

    /**
     * Build the next semantic frame.
     *
     * Incomplete or semantically invalid pulses preserve the last complete frame
     * instead of replacing it with partial, anonymous, or untyped state. No motion
     * is permitted for a rejected refresh.
     *
     * A pulse id is also an idempotent semantic identity. Reusing the currently
     * visible pulse id is permitted only for an exact visible-contact retry. If the
     * same id arrives with different contact semantics, fail closed instead of
     * allowing one identity to mutate underneath checkpoints or retry logic.
     */
    public static Frame build(
            String pulseId,
            List<HeartbeatSkillPolicy.Candidate> candidates,
            boolean pulseComplete,
            Frame lastGood) {
        if (!HeartbeatSkillPolicy.isSafeSemanticText(pulseId)) {
            return preserveLastGood(
                    "",
                    lastGood,
                    "Pulse identity contains a control, malformed surrogate, or bidi-direction control.");
        }
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

        Frame next = new Frame(attempted, attempted, nodes, false, "", anyTransition);
        if (lastGood != null
                && attempted.equals(lastGood.visiblePulseId)
                && !HeartbeatFrameCheckpoint.sameVisibleContact(lastGood, next)) {
            return preserveLastGood(
                    attempted,
                    lastGood,
                    "Pulse identity collision: the visible pulse id was reused with different contact semantics.");
        }
        return next;
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
                withoutMotion(lastGood.nodes),
                true,
                boundary,
                false);
    }

    /**
     * Preserve all visible semantics while clearing one-shot motion flags.
     *
     * Frame.transitionMotionAllowed=false is the aggregate contract, but later
     * renderers may reasonably inspect node.transitionMotion. Returning stale node
     * objects would therefore leave contradictory source truth inside an interrupted
     * frame. Re-materialization keeps contact identity while making the no-motion
     * contract true at both levels.
     */
    private static List<Node> withoutMotion(List<Node> nodes) {
        if (nodes == null || nodes.isEmpty()) return Collections.emptyList();
        List<Node> preserved = new ArrayList<>(nodes.size());
        for (Node node : nodes) preserved.add(new Node(node, false));
        return preserved;
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

    private static String safeBoundedSpeech(
            String value,
            int maxCodePoints,
            String unsafePlaceholder) {
        String clean = clean(value);
        if (clean.isEmpty()) return clean;
        if (!HeartbeatSkillPolicy.isSafeSemanticText(clean)) return unsafePlaceholder;
        int codePoints = clean.codePointCount(0, clean.length());
        if (codePoints <= maxCodePoints) return clean;
        int end = clean.offsetByCodePoints(0, maxCodePoints);
        return clean.substring(0, end) + "… (truncated)";
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
