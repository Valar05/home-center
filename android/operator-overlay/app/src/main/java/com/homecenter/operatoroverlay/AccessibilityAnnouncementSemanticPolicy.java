package com.homecenter.operatoroverlay;

import android.view.View;

/**
 * Source-only decision policy for migrating legacy accessibility announcements.
 *
 * <p>Android 16 / API 36 deprecates {@code View.announceForAccessibility(...)}.
 * This policy deliberately does not replace that call mechanically. It distinguishes
 * automatic semantic value changes from explicit actions whose native control/state
 * semantics already describe the action. A repeated identical action does not need a
 * fake fresh announcement merely to prove the press happened.</p>
 *
 * <p>This class owns no View instance, renderer, controller, phone surface,
 * transport, deployment, or P0 recovery path. {@code OperatorOverlayService}
 * remains the sole native owner.</p>
 */
public final class AccessibilityAnnouncementSemanticPolicy {
    public enum Consequence {
        SPOTIFY_COMMAND_RECEIPT,
        HEARTBEAT_MATERIAL_TRANSITION,
        HEARTBEAT_EXPLICIT_DETAIL_SELECTION,
        ADAM_SEND_CONFIRMATION
    }

    public enum SemanticChannel {
        /** A changing semantic value may use a polite live region under a strict gate. */
        LIVE_REGION_VALUE_CHANGE,
        /** The selected control state plus persistent detail value is the semantic receipt. */
        NATIVE_SELECTION_AND_DETAIL,
        /** The native action plus a persistent result/state surface is the semantic receipt. */
        NATIVE_ACTION_AND_RESULT_STATE
    }

    public enum OwnerMechanism {
        HEARTBEAT_SUMMARY_MATERIAL_TRANSITION,
        SPOTIFY_ACTION_AND_STATUS_VALUE,
        HEARTBEAT_SELECTED_CONTROL_AND_DETAIL,
        ADAM_MODED_SEND_AND_INPUT_RESULT
    }

    /**
     * Exact source-review reason why an otherwise designed consequence is not ready for
     * existing-owner migration. This is not runtime evidence and must not be inferred from
     * a missing patch or a failed workflow.
     */
    public enum MigrationBlocker {
        NONE,
        SPOTIFY_REPEATABLE_RECEIPT_UNRESOLVED,
        DETAIL_REPEAT_SELECTION_RECEIPT_UNRESOLVED,
        ADAM_REPEAT_SEND_RESULT_UNRESOLVED
    }

    public static final class Decision {
        public final SemanticChannel channel;
        public final OwnerMechanism ownerMechanism;
        public final boolean automaticUpdateAllowed;
        public final boolean requiresExplicitUserAction;
        public final boolean preserveNativeTextValue;
        public final boolean requiresMaterialTransition;
        public final boolean repeatableIdenticalValuePossible;
        public final boolean syntheticRepeatReceiptRequired;
        public final boolean ownerMigrationReady;
        public final MigrationBlocker migrationBlocker;
        public final boolean legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring;

        private Decision(
                SemanticChannel channel,
                OwnerMechanism ownerMechanism,
                boolean automaticUpdateAllowed,
                boolean requiresExplicitUserAction,
                boolean preserveNativeTextValue,
                boolean requiresMaterialTransition,
                boolean repeatableIdenticalValuePossible,
                boolean syntheticRepeatReceiptRequired,
                boolean ownerMigrationReady,
                MigrationBlocker migrationBlocker) {
            this.channel = channel;
            this.ownerMechanism = ownerMechanism;
            this.automaticUpdateAllowed = automaticUpdateAllowed;
            this.requiresExplicitUserAction = requiresExplicitUserAction;
            this.preserveNativeTextValue = preserveNativeTextValue;
            this.requiresMaterialTransition = requiresMaterialTransition;
            this.repeatableIdenticalValuePossible = repeatableIdenticalValuePossible;
            this.syntheticRepeatReceiptRequired = syntheticRepeatReceiptRequired;
            this.ownerMigrationReady = ownerMigrationReady;
            this.migrationBlocker = migrationBlocker;
            this.legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring = true;
            if (ownerMigrationReady != (migrationBlocker == MigrationBlocker.NONE)) {
                throw new IllegalArgumentException(
                        "owner migration readiness must agree with the explicit blocker");
            }
        }
    }

    private AccessibilityAnnouncementSemanticPolicy() {
    }

    public static Decision decisionFor(Consequence consequence) {
        if (consequence == null) {
            throw new IllegalArgumentException("consequence is required");
        }
        switch (consequence) {
            case HEARTBEAT_MATERIAL_TRANSITION:
                return new Decision(
                        SemanticChannel.LIVE_REGION_VALUE_CHANGE,
                        OwnerMechanism.HEARTBEAT_SUMMARY_MATERIAL_TRANSITION,
                        true,
                        false,
                        true,
                        true,
                        false,
                        false,
                        true,
                        MigrationBlocker.NONE);
            case SPOTIFY_COMMAND_RECEIPT:
                return new Decision(
                        SemanticChannel.LIVE_REGION_VALUE_CHANGE,
                        OwnerMechanism.SPOTIFY_ACTION_AND_STATUS_VALUE,
                        false,
                        true,
                        true,
                        true,
                        true,
                        false,
                        false,
                        MigrationBlocker.SPOTIFY_REPEATABLE_RECEIPT_UNRESOLVED);
            case HEARTBEAT_EXPLICIT_DETAIL_SELECTION:
                return new Decision(
                        SemanticChannel.NATIVE_SELECTION_AND_DETAIL,
                        OwnerMechanism.HEARTBEAT_SELECTED_CONTROL_AND_DETAIL,
                        false,
                        true,
                        true,
                        false,
                        true,
                        false,
                        false,
                        MigrationBlocker.DETAIL_REPEAT_SELECTION_RECEIPT_UNRESOLVED);
            case ADAM_SEND_CONFIRMATION:
                return new Decision(
                        SemanticChannel.NATIVE_ACTION_AND_RESULT_STATE,
                        OwnerMechanism.ADAM_MODED_SEND_AND_INPUT_RESULT,
                        false,
                        true,
                        true,
                        false,
                        true,
                        false,
                        false,
                        MigrationBlocker.ADAM_REPEAT_SEND_RESULT_UNRESOLVED);
            default:
                throw new IllegalArgumentException("unsupported consequence: " + consequence);
        }
    }

    /**
     * Return a live-region mode only when a consequence is represented by a changed
     * semantic value, is currently migration-ready, and all of that consequence's
     * source-level gates are satisfied.
     *
     * <p>The repeatable Spotify/detail/Adam consequence shapes remain deliberately
     * migration-unready until their existing-owner event semantics are reviewed as a
     * complete contract. Supporting design is not permission to remove a working legacy
     * receipt.</p>
     */
    public static int liveRegionModeFor(
            Consequence consequence,
            boolean explicitUserAction,
            boolean materialTransition,
            boolean muted) {
        Decision decision = decisionFor(consequence);
        if (!decision.ownerMigrationReady
                || decision.channel != SemanticChannel.LIVE_REGION_VALUE_CHANGE) {
            return View.ACCESSIBILITY_LIVE_REGION_NONE;
        }
        boolean polite = !muted;
        if (decision.requiresExplicitUserAction && !explicitUserAction) {
            polite = false;
        }
        if (decision.requiresMaterialTransition && !materialTransition) {
            polite = false;
        }
        return polite
                ? View.ACCESSIBILITY_LIVE_REGION_POLITE
                : View.ACCESSIBILITY_LIVE_REGION_NONE;
    }
}
