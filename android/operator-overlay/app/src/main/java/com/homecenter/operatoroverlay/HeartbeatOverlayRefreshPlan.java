package com.homecenter.operatoroverlay;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

/**
 * Pure render/announcement deduplication plan for the existing Operator Overlay.
 *
 * <p>The service refresh loop currently runs much faster than heartbeat semantics
 * change. Rebuilding a native button subtree or announcing TalkBack content on
 * every poll would turn a quiet heartbeat into focus churn. This source helper
 * composes the existing persisted projection and view-model organs, then exposes
 * deterministic identities the existing {@code OperatorOverlayService} can use
 * when it is wired later.</p>
 *
 * <p>This class owns no renderer, service, state store, transport, phone action,
 * queue, or P0 recovery authority. Callers retain the previous frame/identities.
 * Source presence is not runtime wiring or rendered UI proof.</p>
 */
public final class HeartbeatOverlayRefreshPlan {
    public static final class Plan {
        public final HeartbeatSceneGraph.Frame frame;
        public final HeartbeatOverlayViewModel.Model model;
        public final String selectedControlId;
        /** Changes when the visible/touchable contact or interruption wound changes. */
        public final String renderIdentity;
        /** Changes only for transition semantics or a new interruption wound. */
        public final String announcementIdentity;

        private Plan(
                HeartbeatSceneGraph.Frame frame,
                HeartbeatOverlayViewModel.Model model,
                String selectedControlId,
                String renderIdentity,
                String announcementIdentity) {
            this.frame = frame;
            this.model = model;
            this.selectedControlId = clean(selectedControlId);
            this.renderIdentity = clean(renderIdentity);
            this.announcementIdentity = clean(announcementIdentity);
        }
    }

    public static final class PersistedPlan {
        public final HeartbeatPersistedEnvelopeProjection.Result projection;
        public final Plan plan;

        private PersistedPlan(
                HeartbeatPersistedEnvelopeProjection.Result projection,
                Plan plan) {
            this.projection = projection;
            this.plan = plan;
        }
    }

    private HeartbeatOverlayRefreshPlan() {
    }

    /**
     * Compose exact persisted bytes through the existing integrity/parser/scene
     * pipeline and then into the UI-ready model. Storage/parser rejection therefore
     * inherits the existing last-good contact preservation and motion clamp.
     */
    public static PersistedPlan projectPersisted(
            byte[] payloadUtf8,
            long declaredBytes,
            String declaredSha256,
            long updatedMs,
            HeartbeatSceneGraph.Frame lastGood,
            String selectedControlId) {
        HeartbeatPersistedEnvelopeProjection.Result projection =
                HeartbeatPersistedEnvelopeProjection.projectBytes(
                        payloadUtf8,
                        declaredBytes,
                        declaredSha256,
                        updatedMs,
                        lastGood);
        return new PersistedPlan(
                projection,
                fromFrame(projection.frame, selectedControlId));
    }

    /**
     * Build deterministic UI work identities from an already accepted/preserved
     * scene. Selection is retained by semantic id rather than focus index so scene
     * reorder cannot silently move the user's detail target.
     */
    public static Plan fromFrame(
            HeartbeatSceneGraph.Frame frame,
            String selectedControlId) {
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(frame);
        String selected = clean(selectedControlId);
        if (!selected.isEmpty() && model.controlById(selected) == null) selected = "";

        String contact = HeartbeatFrameCheckpoint.contactSha256(frame);
        String transition = HeartbeatFrameCheckpoint.transitionSha256(frame);
        String interrupted = frame != null && frame.refreshInterrupted ? "1" : "0";
        String exactBoundary = frame == null ? "Heartbeat scene unavailable." : raw(frame.refreshBoundary);

        // Exact evidence/detail changes should rebuild touchable content, but a pure
        // evidence/provenance refresh must not become unsolicited speech.
        String renderIdentity = digest(
                "heartbeat-overlay-render.v1",
                contact,
                interrupted,
                exactBoundary);
        String announcementIdentity = digest(
                "heartbeat-overlay-announcement.v1",
                transition,
                interrupted,
                exactBoundary);
        return new Plan(frame, model, selected, renderIdentity, announcementIdentity);
    }

    public static boolean shouldRebuild(String previousRenderIdentity, Plan next) {
        if (next == null) return false;
        return !clean(previousRenderIdentity).equals(next.renderIdentity);
    }

    public static boolean shouldAnnounce(String previousAnnouncementIdentity, Plan next) {
        if (next == null) return false;
        return !clean(previousAnnouncementIdentity).equals(next.announcementIdentity);
    }

    private static String digest(String schema, String... values) {
        StringBuilder canonical = new StringBuilder();
        append(canonical, schema);
        for (String value : values) append(canonical, raw(value));
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(canonical.toString().getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(bytes.length * 2);
            for (byte value : bytes) {
                hex.append(String.format(Locale.ROOT, "%02x", value & 0xff));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable.", impossible);
        }
    }

    private static void append(StringBuilder out, String value) {
        String safe = raw(value);
        out.append(safe.length()).append(':').append(safe).append(';');
    }

    private static String raw(String value) {
        return value == null ? "" : value;
    }

    private static String clean(String value) {
        return raw(value).trim();
    }
}
