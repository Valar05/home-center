package com.homecenter.operatoroverlay;

import java.util.Locale;

/**
 * Accessibility projection derived from the already-built heartbeat scene.
 *
 * This deliberately consumes {@link HeartbeatSceneGraph.Frame} rather than raw
 * candidates so TalkBack cannot announce a light that the fail-closed scene did
 * not preserve for presentation. It owns no renderer, transport, phone action,
 * focus mutation, or P0 execution authority.
 */
public final class HeartbeatFrameAccessibility {
    /**
     * Keep the collapsed surface useful even when the heartbeat legitimately
     * contains a broad constellation. The exact total/state counts remain spoken;
     * verbose consequence/evidence stays reachable on the individual light.
     */
    public static final int MAX_COLLAPSED_NAMED_LIGHTS = 12;

    private HeartbeatFrameAccessibility() {
    }

    /**
     * Compact collapsed-overlay description of the exact visible scene.
     *
     * A broad valid pulse may contain up to 64 lights and multi-kilobyte semantic
     * fields. Reading every consequence in the collapsed label would turn TalkBack
     * into an unbounded monologue. This summary therefore preserves the exact total,
     * exact state histogram, and a deterministic prefix of label/state identities.
     * Full reason/consequence/evidence/provenance remains available through node
     * detail. Interrupted refresh detail is appended after the last-good summary;
     * discarded attempted candidate content is never announced as current state.
     */
    public static String collapsedContentDescription(HeartbeatSceneGraph.Frame frame) {
        if (frame == null) return "Heartbeat scene unavailable.";

        StringBuilder out = new StringBuilder();
        if (frame.nodes.isEmpty()) {
            out.append("No material skill lights.");
        } else {
            int active = 0;
            int blocked = 0;
            int fault = 0;
            int recovered = 0;
            for (HeartbeatSceneGraph.Node node : frame.nodes) {
                if (node.state == null) continue;
                switch (node.state) {
                    case ACTIVE:
                        active++;
                        break;
                    case BLOCKED:
                        blocked++;
                        break;
                    case FAULT:
                        fault++;
                        break;
                    case RECOVERED:
                        recovered++;
                        break;
                    case DARK:
                    default:
                        break;
                }
            }

            out.append(frame.nodes.size())
                    .append(frame.nodes.size() == 1
                            ? " material skill light. "
                            : " material skill lights. ")
                    .append("States: active ").append(active)
                    .append(", blocked ").append(blocked)
                    .append(", fault ").append(fault)
                    .append(", recovered ").append(recovered)
                    .append(". Lights: ");

            int named = Math.min(frame.nodes.size(), MAX_COLLAPSED_NAMED_LIGHTS);
            for (int index = 0; index < named; index++) {
                HeartbeatSceneGraph.Node node = frame.nodes.get(index);
                if (index > 0) out.append("; ");
                out.append(node.label)
                        .append(", ")
                        .append(stateName(node.state));
            }
            out.append('.');

            int remaining = frame.nodes.size() - named;
            if (remaining > 0) {
                out.append(' ')
                        .append(remaining)
                        .append(remaining == 1
                                ? " more material light is available by touch."
                                : " more material lights are available by touch.");
            }
        }

        if (frame.refreshInterrupted) {
            String interrupted = frame.interruptedRefreshDescription();
            if (!interrupted.isEmpty()) {
                if (out.length() > 0 && out.charAt(out.length() - 1) != ' ') out.append(' ');
                out.append(interrupted);
            }
        }
        return out.toString().trim();
    }

    /**
     * Full touch/TalkBack detail for the node whose current scene focus index was
     * selected. Returns an empty string for an index not present in the visible
     * scene; it never falls back to attempted or discarded refresh data.
     *
     * Focus index is intentionally retained for compatibility. Consumers that need
     * to keep a selection across scene reorder should persist the stable node id and
     * use {@link #detailContentDescription(HeartbeatSceneGraph.Frame, String)}.
     */
    public static String detailContentDescription(
            HeartbeatSceneGraph.Frame frame,
            int focusIndex) {
        if (frame == null || focusIndex < 0) return "";
        for (HeartbeatSceneGraph.Node node : frame.nodes) {
            if (node.focusIndex == focusIndex) return node.detailContentDescription;
        }
        return "";
    }

    /**
     * Full detail by stable semantic light identity.
     *
     * Scene focus order may legitimately change when the auto-selected constellation
     * changes. A renderer can therefore retain the selected light by id without
     * accidentally reading detail for whichever light later occupies the old index.
     */
    public static String detailContentDescription(
            HeartbeatSceneGraph.Frame frame,
            String nodeId) {
        if (frame == null) return "";
        String target = clean(nodeId).toLowerCase(Locale.ROOT);
        if (target.isEmpty()) return "";
        for (HeartbeatSceneGraph.Node node : frame.nodes) {
            if (node.id.toLowerCase(Locale.ROOT).equals(target)) {
                return node.detailContentDescription;
            }
        }
        return "";
    }

    /** Current focus index for a stable semantic id, or -1 when absent. */
    public static int focusIndexForId(HeartbeatSceneGraph.Frame frame, String nodeId) {
        if (frame == null) return -1;
        String target = clean(nodeId).toLowerCase(Locale.ROOT);
        if (target.isEmpty()) return -1;
        for (HeartbeatSceneGraph.Node node : frame.nodes) {
            if (node.id.toLowerCase(Locale.ROOT).equals(target)) return node.focusIndex;
        }
        return -1;
    }

    private static String stateName(HeartbeatSkillPolicy.State state) {
        return state == null ? "unknown" : state.name().toLowerCase(Locale.ROOT);
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
