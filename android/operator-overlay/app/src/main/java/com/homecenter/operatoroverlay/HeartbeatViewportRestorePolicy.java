package com.homecenter.operatoroverlay;

/**
 * Pure source policy for one semantic heartbeat viewport restore ticket.
 *
 * <p>The existing {@link OperatorOverlayService} owns Android views and layout timing.
 * This helper only defines deterministic restore identity and stale-work rejection so
 * the service can invalidate an older pre-draw restore without inventing another
 * renderer/controller/state owner.</p>
 *
 * <p>Source wiring is not Android execution, runtime viewport proof, TalkBack
 * accessibility-focus proof, deployment, or phone delivery.</p>
 */
public final class HeartbeatViewportRestorePolicy {
    public static final class Ticket {
        public final long generation;
        public final String semanticId;
        public final int viewportOffsetPx;
        public final String selectedControlIdAtCapture;
        public final String keyboardFocusedControlIdAtCapture;

        private Ticket(
                long generation,
                String semanticId,
                int viewportOffsetPx,
                String selectedControlIdAtCapture,
                String keyboardFocusedControlIdAtCapture) {
            this.generation = generation;
            this.semanticId = semanticId == null ? "" : semanticId;
            this.viewportOffsetPx = viewportOffsetPx;
            this.selectedControlIdAtCapture = selectedControlIdAtCapture == null
                    ? "" : selectedControlIdAtCapture;
            this.keyboardFocusedControlIdAtCapture = keyboardFocusedControlIdAtCapture == null
                    ? "" : keyboardFocusedControlIdAtCapture;
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
        return ticket(
                generation,
                semanticId,
                viewportOffsetPx,
                selectedControlId,
                keyboardFocusedControlId,
                acceptedNextModel);
    }

    /**
     * Capture visible semantic contact from live native geometry before mutation.
     * A durable but fully offscreen selection cannot suppress a currently visible
     * direct-keyboard-focus fallback. TalkBack accessibility focus remains outside
     * this contract and is neither queried nor inferred.
     */
    public static Ticket captureVisible(
            long generation,
            String selectedControlId,
            boolean selectedHasVisibleContact,
            String keyboardFocusedControlId,
            boolean keyboardFocusHasVisibleContact,
            int viewportOffsetPx,
            HeartbeatOverlayViewModel.Model acceptedNextModel) {
        String semanticId = visibleViewportAnchorId(
                selectedControlId,
                selectedHasVisibleContact,
                keyboardFocusedControlId,
                keyboardFocusHasVisibleContact,
                acceptedNextModel);
        return ticket(
                generation,
                semanticId,
                viewportOffsetPx,
                selectedControlId,
                keyboardFocusedControlId,
                acceptedNextModel);
    }

    private static Ticket ticket(
            long generation,
            String semanticId,
            int viewportOffsetPx,
            String selectedControlId,
            String keyboardFocusedControlId,
            HeartbeatOverlayViewModel.Model acceptedNextModel) {
        String acceptedSemanticId = acceptedControlId(semanticId, acceptedNextModel);
        if (acceptedSemanticId.isEmpty()) return new Ticket(generation, "", 0, "", "");
        return new Ticket(
                generation,
                acceptedSemanticId,
                viewportOffsetPx,
                acceptedControlId(selectedControlId, acceptedNextModel),
                acceptedControlId(keyboardFocusedControlId, acceptedNextModel));
    }

    private static String acceptedControlId(
            String semanticId,
            HeartbeatOverlayViewModel.Model acceptedModel) {
        if (semanticId == null || semanticId.isEmpty() || acceptedModel == null) return "";
        HeartbeatOverlayViewModel.LightControl control = acceptedModel.controlById(semanticId);
        return control == null ? "" : control.id;
    }

    private static boolean sameId(String first, String second) {
        String left = first == null ? "" : first;
        String right = second == null ? "" : second;
        return left.equalsIgnoreCase(right);
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
     * Legacy semantic-owner revalidation. Selection wins over direct keyboard focus.
     * This remains useful where geometry-aware capture was not performed.
     */
    public static boolean shouldRestore(
            Ticket ticket,
            long currentGeneration,
            HeartbeatOverlayViewModel.Model currentAcceptedModel,
            String selectedControlId,
            String keyboardFocusedControlId) {
        if (!shouldRestore(ticket, currentGeneration, currentAcceptedModel)) return false;
        String currentOwner = HeartbeatOverlayRefreshPlan.viewportAnchorId(
                selectedControlId,
                keyboardFocusedControlId,
                currentAcceptedModel);
        return ticket.semanticId.equalsIgnoreCase(currentOwner);
    }

    /**
     * Backward-compatible captured-owner revalidation for source callers that cannot
     * distinguish mutation-caused native focus loss from focus moved elsewhere in the
     * overlay. Because that missing evidence can hide a newer non-heartbeat focus,
     * empty heartbeat-child focus fails closed here for both keyboard- and
     * selection-derived tickets. Callers that can prove mutation class plus overlay
     * focus scope must use the explicit overload below.
     */
    public static boolean shouldRestoreCapturedOwner(
            Ticket ticket,
            long currentGeneration,
            HeartbeatOverlayViewModel.Model currentAcceptedModel,
            String currentSelectedControlId,
            String currentKeyboardFocusedControlId) {
        String currentKeyboard = acceptedControlId(
                currentKeyboardFocusedControlId,
                currentAcceptedModel);
        if (currentKeyboard.isEmpty()) return false;
        return shouldRestoreCapturedOwner(
                ticket,
                currentGeneration,
                currentAcceptedModel,
                currentSelectedControlId,
                currentKeyboard,
                false,
                true);
    }

    /**
     * Revalidate the interaction owner recorded by a geometry-aware capture without
     * reinterpreting mutation-caused geometry or native focus destruction as user
     * intent.
     *
     * <p>A persistent selection is not absolute interaction ownership. If direct
     * keyboard focus changes after capture, that newer navigation supersedes a
     * selection-derived viewport ticket too. The captured keyboard-focus baseline is
     * therefore compared for both ownership modes.</p>
     *
     * <p>An empty heartbeat-child focus is ambiguous. It may be mutation-caused only
     * when {@code mutationMayDestroyKeyboardFocus} is true and there is no known direct
     * focus elsewhere in the overlay. Stable in-place refreshes must not use rebuild
     * amnesty, and a non-heartbeat focused overlay control is a real competing owner.
     * This still does not inspect or claim TalkBack accessibility focus.</p>
     */
    public static boolean shouldRestoreCapturedOwner(
            Ticket ticket,
            long currentGeneration,
            HeartbeatOverlayViewModel.Model currentAcceptedModel,
            String currentSelectedControlId,
            String currentKeyboardFocusedControlId,
            boolean mutationMayDestroyKeyboardFocus,
            boolean anyDirectKeyboardFocusPresent) {
        if (!shouldRestore(ticket, currentGeneration, currentAcceptedModel)) return false;
        String currentSelected = acceptedControlId(currentSelectedControlId, currentAcceptedModel);
        String currentKeyboard = acceptedControlId(currentKeyboardFocusedControlId, currentAcceptedModel);
        String capturedKeyboard = acceptedControlId(
                ticket.keyboardFocusedControlIdAtCapture,
                currentAcceptedModel);
        if (sameId(ticket.semanticId, ticket.selectedControlIdAtCapture)) {
            if (!sameId(ticket.selectedControlIdAtCapture, currentSelected)) return false;
            if (!currentKeyboard.isEmpty()) {
                return !capturedKeyboard.isEmpty() && sameId(capturedKeyboard, currentKeyboard);
            }
            if (anyDirectKeyboardFocusPresent) return false;
            if (!capturedKeyboard.isEmpty()) return mutationMayDestroyKeyboardFocus;
            return true;
        }
        if (sameId(ticket.semanticId, ticket.keyboardFocusedControlIdAtCapture)) {
            if (!sameId(ticket.selectedControlIdAtCapture, currentSelected)) return false;
            if (!currentKeyboard.isEmpty()) {
                return sameId(ticket.keyboardFocusedControlIdAtCapture, currentKeyboard);
            }
            if (anyDirectKeyboardFocusPresent) return false;
            return mutationMayDestroyKeyboardFocus;
        }
        return false;
    }

    /**
     * Whether a candidate native control actually has visible horizontal contact with
     * the current heartbeat viewport.
     *
     * <p>Semantic selection alone is not visible contact: a selected light may be
     * completely offscreen after the user scrolls elsewhere. Partial intersection is
     * sufficient; zero-width controls/viewports and fully offscreen geometry fail
     * closed. Long arithmetic prevents integer overflow from manufacturing contact.</p>
     */
    public static boolean hasVisibleViewportContact(
            int anchorLeftPx,
            int anchorWidthPx,
            int scrollXPx,
            int viewportWidthPx) {
        if (anchorWidthPx <= 0 || viewportWidthPx <= 0) return false;
        long anchorLeft = anchorLeftPx;
        long anchorRight = anchorLeft + (long) anchorWidthPx;
        long viewportLeft = Math.max(0L, (long) scrollXPx);
        long viewportRight = viewportLeft + (long) viewportWidthPx;
        return anchorRight > viewportLeft && anchorLeft < viewportRight;
    }

    /**
     * Choose visible semantic contact without letting an offscreen durable selection
     * suppress a currently visible keyboard-focused fallback.
     *
     * <p>The booleans must come from {@link #hasVisibleViewportContact(int, int, int, int)}
     * for the corresponding live native controls. Accepted-model membership and
     * selected-first/focus-fallback semantics remain delegated to the existing
     * {@link HeartbeatOverlayRefreshPlan#viewportAnchorId(String, String, HeartbeatOverlayViewModel.Model)}
     * authority. TalkBack accessibility focus remains outside this contract.</p>
     */
    public static String visibleViewportAnchorId(
            String selectedControlId,
            boolean selectedHasVisibleContact,
            String keyboardFocusedControlId,
            boolean keyboardFocusHasVisibleContact,
            HeartbeatOverlayViewModel.Model acceptedNextModel) {
        return HeartbeatOverlayRefreshPlan.viewportAnchorId(
                selectedHasVisibleContact ? selectedControlId : "",
                keyboardFocusHasVisibleContact ? keyboardFocusedControlId : "",
                acceptedNextModel);
    }

    /**
     * Delegate final geometry to the existing bounded anchor calculation. Callers
     * must first establish restore ownership.
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
