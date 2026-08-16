package com.homecenter.operatoroverlay;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * Pure source-side checkpoint fingerprints for heartbeat scenes.
 *
 * This class does not persist checkpoints, own a renderer, touch transport, or
 * mutate the phone/P0 execution path. It only gives existing scene consumers a
 * deterministic identity for exact visible contact, for the presented/touchable
 * surface, and for transition semantics so retries can be compared without guessing
 * from timestamps.
 */
public final class HeartbeatFrameCheckpoint {
    private HeartbeatFrameCheckpoint() {
    }

    /**
     * Exact semantic identity of the visible last-good contact surface.
     *
     * Attempted pulse identity and refresh failure text are deliberately excluded:
     * an interrupted refresh must not change the fingerprint of the contact that
     * remains visible. The accepted visible pulse identity stays included here
     * because this checkpoint is also evidence/idempotence identity. Provenance and
     * evidence detail are included because they are part of the touch/TalkBack
     * surface even when they do not earn transition motion.
     *
     * <p>Semantic light ids retain their exact source spelling here. A producer that
     * changes only id case therefore advances exact contact/checkpoint evidence even
     * though the case-insensitive UI identity may remain presentation-equivalent.</p>
     */
    public static String contactSha256(HeartbeatSceneGraph.Frame frame) {
        Canonical out = new Canonical("heartbeat-contact.v1");
        if (frame == null) {
            out.value("<no-frame>");
            return sha256(out.text());
        }

        out.value(frame.visiblePulseId);
        appendNodes(out, frame, false);
        return sha256(out.text());
    }

    /**
     * Identity of only the currently presented/touchable last-good surface.
     *
     * <p>The accepted pulse id is deliberately excluded. A producer may emit a new
     * pulse id whose visible controls, order, detail, touch targets, and evidence are
     * byte-for-byte equivalent at the Java String level. That is a new exact
     * checkpoint, but it is not new UI work and must not churn native controls or
     * TalkBack just because an otherwise invisible pulse id advanced.</p>
     *
     * <p>Semantic light ids are case-insensitive throughout material-light dedupe,
     * model lookup, native-child tags, selection retention, and structure identity.
     * Presentation identity therefore folds only the semantic id field to lower case
     * while preserving every actually presented label/detail/state/touch field
     * exactly. `Regnet` -> `regnet` may advance exact checkpoint evidence, but it does
     * not earn a native content refresh when every presented semantic field is
     * otherwise unchanged.</p>
     *
     * <p>If a later refresh is interrupted, interruption state/boundary live outside
     * this fingerprint and the scene can still expose the exact current visible
     * pulse id in its bounded interruption description.</p>
     */
    public static String presentationSha256(HeartbeatSceneGraph.Frame frame) {
        Canonical out = new Canonical("heartbeat-presentation.v1");
        if (frame == null) {
            out.value("<no-frame>");
            return sha256(out.text());
        }

        appendNodes(out, frame, true);
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
            out.value(node.id.toLowerCase(Locale.ROOT));
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

    public static boolean samePresentation(
            HeartbeatSceneGraph.Frame left,
            HeartbeatSceneGraph.Frame right) {
        return presentationSha256(left).equals(presentationSha256(right));
    }

    public static boolean sameTransitionState(
            HeartbeatSceneGraph.Frame left,
            HeartbeatSceneGraph.Frame right) {
        return transitionSha256(left).equals(transitionSha256(right));
    }

    /**
     * Append the complete presented node surface.
     *
     * <p>Exact checkpoint identity keeps the source id spelling. Presentation
     * identity folds only that semantic identity field because all downstream
     * heartbeat id ownership is case-insensitive. Every visible/spoken/touchable
     * field remains exact in both paths.</p>
     */
    private static void appendNodes(
            Canonical out,
            HeartbeatSceneGraph.Frame frame,
            boolean foldSemanticIds) {
        out.integer(frame.nodes.size());
        for (HeartbeatSceneGraph.Node node : frame.nodes) {
            out.value(foldSemanticIds ? node.id.toLowerCase(Locale.ROOT) : node.id);
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
    }

    private static String sha256(String canonical) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(canonical.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(bytes.length * 2);
            for (byte value : bytes) {
                hex.append(String.format(Locale.ROOT, "%02x", value & 0xff));
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
