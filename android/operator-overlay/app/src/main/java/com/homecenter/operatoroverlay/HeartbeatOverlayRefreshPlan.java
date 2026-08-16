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
 * deterministic identities consumed by the existing {@code OperatorOverlayService}
 * source path.</p>
 *
 * <p>This class owns no renderer, service, state store, transport, phone action,
 * queue, or P0 recovery authority. Callers retain the previous frame/identities.
 * Existing-owner source composition is not Android execution, runtime rendering,
 * deployment, or delivery proof.</p>
 */
public final class HeartbeatOverlayRefreshPlan {
    public static final class Plan {
        public final HeartbeatSceneGraph.Frame frame;
        public final HeartbeatOverlayViewModel.Model model;
        public final String selectedControlId;
        /**
         * Changes only when the ordered semantic control identities change.
         *
         * <p>This is deliberately narrower than {@link #renderIdentity}. A stable
         * control structure can refresh text/detail in place without destroying and
         * recreating the native Button objects that may currently hold keyboard or
         * accessibility focus.</p>
         */
        public final String structureIdentity;
        /** Changes when the visible/touchable contact or interruption wound changes. */
        public final String renderIdentity;
        /** Changes only for transition semantics or a new interruption wound. */
        public final String announcementIdentity;

        private Plan(
                HeartbeatSceneGraph.Frame frame,
                HeartbeatOverlayViewModel.Model model,
                String selectedControlId,
                String structureIdentity,
                String renderIdentity,
                String announcementIdentity) {
            this.frame = frame;
            this.model = model;
            this.selectedControlId = clean(selectedControlId);
            this.structureIdentity = clean(structureIdentity);
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

        // Ordered semantic ids define whether the native child structure itself
        // must change. Label/state/detail/touch semantics can be updated on the
        // existing child object when this identity is stable, preserving focus.
        String structureIdentity = structureIdentity(model);

        // Exact evidence/detail changes should refresh touchable content, but a pure
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
        return new Plan(
                frame,
                model,
                selected,
                structureIdentity,
                renderIdentity,
                announcementIdentity);
    }

    /**
     * Whether the native child structure must be rebuilt.
     *
     * <p>A stable ordered semantic-id set means existing buttons can be refreshed in
     * place. This narrow identity exists specifically to avoid unnecessary
     * keyboard/TalkBack focus churn on evidence, state, consequence, or label-only
     * refreshes.</p>
     */
    public static boolean shouldRebuildStructure(
            String previousStructureIdentity,
            Plan next) {
        if (next == null) return false;
        return !clean(previousStructureIdentity).equals(next.structureIdentity);
    }

    /** Whether visible/touchable content changed and should be refreshed. */
    public static boolean shouldRefreshContent(
            String previousRenderIdentity,
            Plan next) {
        if (next == null) return false;
        return !clean(previousRenderIdentity).equals(next.renderIdentity);
    }

    /**
     * Existing service compatibility: until the owner consumes structureIdentity,
     * a render-identity change still means its current full rebuild path should run.
     * New wiring should prefer shouldRebuildStructure + shouldRefreshContent.
     */
    public static boolean shouldRebuild(String previousRenderIdentity, Plan next) {
        return shouldRefreshContent(previousRenderIdentity, next);
    }

    /**
     * Automatic speech requires an established prior semantic baseline. An empty
     * previous identity means cold start/unknown history, not a proven transition;
     * the renderer may still show the current model, but it must not announce it as
     * though a state change was observed.
     */
    public static boolean shouldAnnounce(String previousAnnouncementIdentity, Plan next) {
        if (next == null) return false;
        String previous = clean(previousAnnouncementIdentity);
        if (previous.isEmpty()) return false;
        return !previous.equals(next.announcementIdentity);
    }

    /**
     * Existing-overlay runtime gate for automatic heartbeat speech.
     *
     * <p>Mute and visibility are presentation policy, not semantic identity. The
     * caller should still advance the remembered announcement identity while muted
     * or hidden so unmuting/restoring later does not replay a stale transition as a
     * new event. This helper only decides whether the current semantic transition is
     * allowed to speak now.</p>
     */
    public static boolean shouldAnnounce(
            String previousAnnouncementIdentity,
            Plan next,
            boolean muted,
            boolean overlayVisible) {
        if (muted || !overlayVisible) return false;
        return shouldAnnounce(previousAnnouncementIdentity, next);
    }

    private static String structureIdentity(HeartbeatOverlayViewModel.Model model) {
        StringBuilder canonical = new StringBuilder();
        append(canonical, "heartbeat-overlay-structure.v1");
        if (model == null) {
            append(canonical, "<no-model>");
        } else {
            canonical.append('#').append(model.controls.size()).append(';');
            for (HeartbeatOverlayViewModel.LightControl control : model.controls) {
                append(canonical, raw(control.id).toLowerCase(Locale.ROOT));
            }
        }
        return sha256(canonical.toString());
    }

    private static String digest(String schema, String... values) {
        StringBuilder canonical = new StringBuilder();
        append(canonical, schema);
        for (String value : values) append(canonical, raw(value));
        return sha256(canonical.toString());
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
