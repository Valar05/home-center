package com.homecenter.operatoroverlay;

import android.view.View;

/**
 * Source-only decision policy for migrating legacy accessibility announcements.
 *
 * <p>Android 16 / API 36 deprecates {@code View.announceForAccessibility(...)}.
 * This policy deliberately does not replace that call mechanically. Different
 * consequences belong to different semantic channels, timing gates, and owner
 * lifecycles. An owner may retire a legacy announcement only after the matching
 * semantic consequence is wired.</p>
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
        /** A changing TextView remains the semantic value and is gated as a polite live region. */
        POLITE_LIVE_REGION_VALUE,
        /** User-selected detail stays the semantic value and is surfaced only for explicit selection. */
        SELECTED_DETAIL_VALUE,
        /** A completed edit/action is represented by a dedicated status value. */
        STATUS_VALUE
    }

    public enum OwnerMechanism {
        /** Existing Spotify status value; polite only for an explicit command receipt. */
        SPOTIFY_STATUS_EXPLICIT_RECEIPT,
        /** Existing heartbeat summary value; polite only behind the material-transition gate. */
        HEARTBEAT_SUMMARY_MATERIAL_TRANSITION,
        /** Existing heartbeat detail value; polite only for explicit selection, never background refresh. */
        HEARTBEAT_DETAIL_EXPLICIT_SELECTION,
        /** Dedicated Adam completion status value updated only after a real send. */
        ADAM_DEDICATED_SEND_STATUS
    }

    public static final class Decision {
        public final SemanticChannel channel;
        public final OwnerMechanism ownerMechanism;
        public final boolean automaticUpdateAllowed;
        public final boolean requiresExplicitUserAction;
        public final boolean preserveNativeTextValue;
        public final boolean requiresMaterialTransition;
        public final boolean backgroundUpdateMustDisableLiveRegion;
        public final boolean requiresDedicatedStatusValue;
        public final boolean legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring;

        private Decision(
                SemanticChannel channel,
                OwnerMechanism ownerMechanism,
                boolean automaticUpdateAllowed,
                boolean requiresExplicitUserAction,
                boolean preserveNativeTextValue,
                boolean requiresMaterialTransition,
                boolean backgroundUpdateMustDisableLiveRegion,
                boolean requiresDedicatedStatusValue) {
            this.channel = channel;
            this.ownerMechanism = ownerMechanism;
            this.automaticUpdateAllowed = automaticUpdateAllowed;
            this.requiresExplicitUserAction = requiresExplicitUserAction;
            this.preserveNativeTextValue = preserveNativeTextValue;
            this.requiresMaterialTransition = requiresMaterialTransition;
            this.backgroundUpdateMustDisableLiveRegion = backgroundUpdateMustDisableLiveRegion;
            this.requiresDedicatedStatusValue = requiresDedicatedStatusValue;
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
            case SPOTIFY_COMMAND_RECEIPT:
                return new Decision(
                        SemanticChannel.POLITE_LIVE_REGION_VALUE,
                        OwnerMechanism.SPOTIFY_STATUS_EXPLICIT_RECEIPT,
                        false,
                        true,
                        true,
                        false,
                        true,
                        false);
            case HEARTBEAT_MATERIAL_TRANSITION:
                return new Decision(
                        SemanticChannel.POLITE_LIVE_REGION_VALUE,
                        OwnerMechanism.HEARTBEAT_SUMMARY_MATERIAL_TRANSITION,
                        true,
                        false,
                        true,
                        true,
                        true,
                        false);
            case HEARTBEAT_EXPLICIT_DETAIL_SELECTION:
                return new Decision(
                        SemanticChannel.SELECTED_DETAIL_VALUE,
                        OwnerMechanism.HEARTBEAT_DETAIL_EXPLICIT_SELECTION,
                        false,
                        true,
                        true,
                        false,
                        true,
                        false);
            case ADAM_SEND_CONFIRMATION:
                return new Decision(
                        SemanticChannel.STATUS_VALUE,
                        OwnerMechanism.ADAM_DEDICATED_SEND_STATUS,
                        false,
                        true,
                        true,
                        false,
                        false,
                        true);
            default:
                throw new IllegalArgumentException("unsupported consequence: " + consequence);
        }
    }

    /**
     * Return the live-region mode for the next semantic value update.
     *
     * <p>The owner must apply this mode before mutating the corresponding TextView.
     * Background/poll refreshes therefore explicitly disable a previously polite
     * surface before changing its value. Mute preserves the previous owner behavior:
     * it suppresses heartbeat transition/detail speech, but not explicit Spotify or
     * Adam action confirmations.</p>
     */
    public static int liveRegionModeFor(
            Consequence consequence,
            boolean explicitUserAction,
            boolean materialTransition,
            boolean muted) {
        Decision decision = decisionFor(consequence);
        boolean polite;
        switch (consequence) {
            case SPOTIFY_COMMAND_RECEIPT:
                polite = explicitUserAction;
                break;
            case HEARTBEAT_MATERIAL_TRANSITION:
                polite = materialTransition && !muted;
                break;
            case HEARTBEAT_EXPLICIT_DETAIL_SELECTION:
                polite = explicitUserAction && !muted;
                break;
            case ADAM_SEND_CONFIRMATION:
                polite = explicitUserAction;
                break;
            default:
                throw new IllegalArgumentException("unsupported consequence: " + consequence);
        }
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
