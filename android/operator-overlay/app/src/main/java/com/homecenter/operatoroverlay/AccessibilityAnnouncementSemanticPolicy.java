package com.homecenter.operatoroverlay;

import android.view.View;

/**
 * Source-only decision policy for migrating legacy accessibility announcements.
 *
 * <p>Android 16 / API 36 deprecates {@code View.announceForAccessibility(...)}.
 * This policy deliberately does not replace that call mechanically. A live region
 * represents a semantic value whose content changed; it is not a generic repeatable
 * event broadcaster. Consequences that can repeat with the same value therefore stay
 * owner-unready until they have an event/status design with a genuinely fresh semantic
 * value.</p>
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
        /** A changing TextView value may use a polite live region under a strict semantic gate. */
        LIVE_REGION_VALUE_CHANGE,
        /** Explicit consequence may repeat without changing the current value; exact event semantics unresolved. */
        REPEATABLE_ACTION_EVENT_UNRESOLVED
    }

    public enum OwnerMechanism {
        /** Existing heartbeat summary changes when material transition semantics change. */
        HEARTBEAT_SUMMARY_MATERIAL_TRANSITION,
        /** No exact owner mechanism is accepted yet for repeatable same-value action consequences. */
        UNRESOLVED_REPEATABLE_ACTION_EVENT
    }

    public static final class Decision {
        public final SemanticChannel channel;
        public final OwnerMechanism ownerMechanism;
        public final boolean automaticUpdateAllowed;
        public final boolean requiresExplicitUserAction;
        public final boolean preserveNativeTextValue;
        public final boolean requiresMaterialTransition;
        public final boolean repeatableIdenticalValuePossible;
        public final boolean ownerMigrationReady;
        public final boolean legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring;

        private Decision(
                SemanticChannel channel,
                OwnerMechanism ownerMechanism,
                boolean automaticUpdateAllowed,
                boolean requiresExplicitUserAction,
                boolean preserveNativeTextValue,
                boolean requiresMaterialTransition,
                boolean repeatableIdenticalValuePossible,
                boolean ownerMigrationReady) {
            this.channel = channel;
            this.ownerMechanism = ownerMechanism;
            this.automaticUpdateAllowed = automaticUpdateAllowed;
            this.requiresExplicitUserAction = requiresExplicitUserAction;
            this.preserveNativeTextValue = preserveNativeTextValue;
            this.requiresMaterialTransition = requiresMaterialTransition;
            this.repeatableIdenticalValuePossible = repeatableIdenticalValuePossible;
            this.ownerMigrationReady = ownerMigrationReady;
            this.legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring = true;
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
                        true);
            case SPOTIFY_COMMAND_RECEIPT:
            case HEARTBEAT_EXPLICIT_DETAIL_SELECTION:
            case ADAM_SEND_CONFIRMATION:
                return new Decision(
                        SemanticChannel.REPEATABLE_ACTION_EVENT_UNRESOLVED,
                        OwnerMechanism.UNRESOLVED_REPEATABLE_ACTION_EVENT,
                        false,
                        true,
                        true,
                        false,
                        true,
                        false);
            default:
                throw new IllegalArgumentException("unsupported consequence: " + consequence);
        }
    }

    /**
     * Return a live-region mode only for consequences that are already valid
     * value-change semantics.
     *
     * <p>Repeatable action consequences deliberately return NONE. Their deprecated
     * legacy calls may not be removed merely by setting POLITE on a value that can
     * remain byte-for-byte identical across two completed actions.</p>
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
        boolean polite = materialTransition && !muted;
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
