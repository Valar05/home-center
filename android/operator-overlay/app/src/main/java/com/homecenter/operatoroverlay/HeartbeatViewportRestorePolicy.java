package com.homecenter.operatoroverlay;

/**
 * Pure source policy for one semantic heartbeat viewport restore ticket.
 *
 * <p>The existing {@link OperatorOverlayService} owns Android views and layout timing.
 * This helper only defines deterministic restore identity and stale-work rejection so
 * a later service mutation can invalidate an older pre-draw restore without inventing
 * another renderer/controller/state owner.</p>
 *
 * <p>Source presence is not existing-service wiring, Android execution, runtime
 * viewport proof, TalkBack accessibility-focus proof, deployment, or phone delivery.</p>
 */
public final class HeartbeatViewportRestorePolicy {
    public static final class Ticket {
        public final long generation;
        public final String semanticId;
        public final int viewportOffsetPx;

        private Ticket(long generation, String semanticId, int viewportOffsetPx) {
            this.generation = generation;
            this.semanticId = semanticId == null ? "" : semanticId;
            this.viewportOffsetPx = viewportOffsetPx;
        }

        public boolean hasAnchor() {
            return !semanticId.isEmpty();
        }
    }

    private HeartbeatViewportRestorePolicy() {
    }

    /**
     * Advance restore ownership whenever a later mutation or explicit selection
     * supersedes older pending after-layout work. This is an ordering token, not a
     * wall-clock timestamp and not evidence that Android performed the restore.
     */
    public static long nextGeneration(long currentGeneration) {
        return currentGeneration + 1L;
    }

    /**
     * Capture at most one accepted semantic anchor for a pending mutation.
     * Selection wins; direct keyboard focus is fallback; both must survive in the
     * accepted next model. TalkBack accessibility focus is deliberately not queried.
     */
    public static Ticket capture(
            long generation,
            String selectedControlId,
            String keyboardFocusedControlId,
            int viewportOffsetPx,
            HeartbeatOverlayViewModel.Model acceptedNextModel) {
        String semanticId = HeartbeatOverlayRefreshPlan.viewportAnchorId(
                selectedControlId,
                keyboardFocusedControlId,
                acceptedNextModel);
        if (semanticId.isEmpty()) return new Ticket(generation, "", 0);
        HeartbeatOverlayViewModel.LightControl control =
                acceptedNextModel == null ? null : acceptedNextModel.controlById(semanticId);
        if (control == null) return new Ticket(generation, "", 0);
        return new Ticket(generation, control.id, viewportOffsetPx);
    }

    /**
     * A scheduled restore may act only if no later mutation/selection superseded its
     * generation and the exact semantic anchor still exists in the accepted model.
     */
    public static boolean shouldRestore(
            Ticket ticket,
            long currentGeneration,
            HeartbeatOverlayViewModel.Model currentAcceptedModel) {
        if (ticket == null || !ticket.hasAnchor()) return false;
        if (ticket.generation != currentGeneration) return false;
        return currentAcceptedModel != null
                && currentAcceptedModel.controlById(ticket.semanticId) != null;
    }

    /**
     * Delegate final geometry to the existing bounded anchor calculation. Callers
     * must first establish {@link #shouldRestore(Ticket, long, HeartbeatOverlayViewModel.Model)}.
     */
    public static int targetScrollX(
            Ticket ticket,
            int nextAnchorLeftPx,
            int maxScrollXPx) {
        if (ticket == null || !ticket.hasAnchor()) return 0;
        return HeartbeatOverlayRefreshPlan.anchoredScrollX(
                nextAnchorLeftPx,
                ticket.viewportOffsetPx,
                maxScrollXPx);
    }
}
