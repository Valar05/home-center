package com.homecenter.operatoroverlay;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * Pure source-side checkpoint fingerprints for heartbeat scenes.
 *
 * This class does not persist checkpoints, own a renderer, touch transport, or
 * mutate the phone/P0 execution path. It only gives existing scene consumers a
 * deterministic identity for the visible contact surface and for transition
 * semantics so retries can be compared without guessing from timestamps.
 */
public final class HeartbeatFrameCheckpoint {
    private HeartbeatFrameCheckpoint() {
    }

    /**
     * Exact semantic identity of the visible last-good contact surface.
     *
     * Attempted pulse identity and refresh failure text are deliberately excluded:
     * an interrupted refresh must not change the fingerprint of the contact that
     * remains visible. Provenance/evidence detail is included because it is part of
     * the touch/TalkBack surface even when it does not earn transition motion.
     */
    public static String contactSha256(HeartbeatSceneGraph.Frame frame) {
        Canonical out = new Canonical("heartbeat-contact.v1");
        if (frame == null) {
            out.value("<no-frame>");
            return sha256(out.text());
        }

        out.value(frame.visiblePulseId);
        out.integer(frame.nodes.size());
        for (HeartbeatSceneGraph.Node node : frame.nodes) {
            out.value(node.id);
            out.value(node.label);
            out.value(node.provenanceKind);
            out.value(node.provenanceLocator);
            out.value(node.activationReason);
            out.value(node.state == null ? "" : node.state.name());
            out.value(node.consequence);
            out.value(node.evidenceBoundary);
            out.integer(node.focusIndex);
            out.integer(node.touchTargetDp);
        }
        return sha256(out.text());
    }

    /**
     * Identity of only the fields allowed to earn Christmas-light transition
     * motion. Pulse IDs, evidence/provenance refreshes, and pure scene reorder are
     * excluded on purpose.
     *
     * Scene order is a visible/contact concern because it changes focus positions,
     * so contactSha256 remains order-sensitive. HeartbeatSceneGraph deliberately
     * does not grant transition motion for reorder alone, however; this fingerprint
     * therefore canonicalizes nodes by stable semantic id before hashing state and
     * consequence so sameTransitionState agrees with transitionMotionAllowed.
     */
    public static String transitionSha256(HeartbeatSceneGraph.Frame frame) {
        Canonical out = new Canonical("heartbeat-transition.v1");
        if (frame == null) {
            out.value("<no-frame>");
            return sha256(out.text());
        }

        List<HeartbeatSceneGraph.Node> ordered = new ArrayList<>(frame.nodes);
        Collections.sort(ordered, new Comparator<HeartbeatSceneGraph.Node>() {
            @Override
            public int compare(HeartbeatSceneGraph.Node left, HeartbeatSceneGraph.Node right) {
                int folded = left.id.compareToIgnoreCase(right.id);
                return folded != 0 ? folded : left.id.compareTo(right.id);
            }
        });

        out.integer(ordered.size());
        for (HeartbeatSceneGraph.Node node : ordered) {
            out.value(node.id.toLowerCase(java.util.Locale.ROOT));
            out.value(node.state == null ? "" : node.state.name());
            out.value(node.consequence);
        }
        return sha256(out.text());
    }

    public static boolean sameVisibleContact(
            HeartbeatSceneGraph.Frame left,
            HeartbeatSceneGraph.Frame right) {
        return contactSha256(left).equals(contactSha256(right));
    }

    public static boolean sameTransitionState(
            HeartbeatSceneGraph.Frame left,
            HeartbeatSceneGraph.Frame right) {
        return transitionSha256(left).equals(transitionSha256(right));
    }

    private static String sha256(String canonical) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(canonical.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(bytes.length * 2);
            for (byte value : bytes) {
                hex.append(String.format(java.util.Locale.ROOT, "%02x", value & 0xff));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable.", impossible);
        }
    }

    /** Length-prefixed encoding avoids delimiter ambiguity without JSON machinery. */
    private static final class Canonical {
        private final StringBuilder out = new StringBuilder();

        Canonical(String schema) {
            value(schema);
        }

        void value(String value) {
            String safe = value == null ? "" : value;
            out.append(safe.length()).append(':').append(safe).append(';');
        }

        void integer(int value) {
            out.append('#').append(value).append(';');
        }

        String text() {
            return out.toString();
        }
    }
}
