package com.homecenter.operatoroverlay;

/**
 * Accessibility projection derived from the already-built heartbeat scene.
 *
 * This deliberately consumes {@link HeartbeatSceneGraph.Frame} rather than raw
 * candidates so TalkBack cannot announce a light that the fail-closed scene did
 * not preserve for presentation. It owns no renderer, transport, phone action,
 * focus mutation, or P0 execution authority.
 */
public final class HeartbeatFrameAccessibility {
    private HeartbeatFrameAccessibility() {
    }

    /**
     * Compact collapsed-overlay description of the exact visible scene.
     * Interrupted refresh detail is appended after the last-good visible lights;
     * discarded attempted candidate content is never announced as current state.
     */
    public static String collapsedContentDescription(HeartbeatSceneGraph.Frame frame) {
        if (frame == null) return "Heartbeat scene unavailable.";

        StringBuilder out = new StringBuilder();
        if (frame.nodes.isEmpty()) {
            out.append("No material skill lights.");
        } else {
            out.append(frame.nodes.size())
                    .append(frame.nodes.size() == 1
                            ? " material skill light. "
                            : " material skill lights. ");
            for (HeartbeatSceneGraph.Node node : frame.nodes) {
                out.append(node.contentDescription).append(' ');
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
     * Full touch/TalkBack detail for the node whose stable scene focus index was
     * selected. Returns an empty string for an index not present in the visible
     * scene; it never falls back to attempted or discarded refresh data.
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
}
