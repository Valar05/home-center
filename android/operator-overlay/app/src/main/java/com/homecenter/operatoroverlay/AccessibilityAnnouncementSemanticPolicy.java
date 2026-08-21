package com.homecenter.operatoroverlay;

/**
 * Source-only decision policy for migrating legacy accessibility announcements.
 *
 * <p>Android 16 / API 36 deprecates {@code View.announceForAccessibility(...)}.
 * This policy deliberately does not replace that call mechanically. Different
 * consequences belong to different semantic channels, and an owner may retire a
 * legacy announcement only after the corresponding semantic consequence is wired.
 *
 * <p>This class owns no View, accessibility event, renderer, controller, phone
 * surface, transport, deployment, or P0 recovery path. {@code OperatorOverlayService}
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
        /** A changing TextView remains the semantic value; a polite live region may surface it. */
        POLITE_LIVE_REGION_VALUE,
        /** User-selected detail is exposed through the selected detail semantic value. */
        SELECTED_DETAIL_VALUE,
        /** A completed edit/action should use semantic state or a dedicated status value. */
        STATUS_OR_STATE_DESCRIPTION
    }

    public static final class Decision {
        public final SemanticChannel channel;
        public final boolean automaticUpdateAllowed;
        public final boolean requiresExplicitUserAction;
        public final boolean preserveNativeTextValue;
        public final boolean requiresMaterialTransition;
        public final boolean legacyAnnouncementMayBeRemovedOnlyAfterOwnerWiring;

        private Decision(
                SemanticChannel channel,
                boolean automaticUpdateAllowed,
                boolean requiresExplicitUserAction,
                boolean preserveNativeTextValue,
                boolean requiresMaterialTransition) {
            this.channel = channel;
            this.automaticUpdateAllowed = automaticUpdateAllowed;
            this.requiresExplicitUserAction = requiresExplicitUserAction;
            this.preserveNativeTextValue = preserveNativeTextValue;
            this.requiresMaterialTransition = requiresMaterialTransition;
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
                        false,
                        true,
                        true,
                        false);
            case HEARTBEAT_MATERIAL_TRANSITION:
                return new Decision(
                        SemanticChannel.POLITE_LIVE_REGION_VALUE,
                        true,
                        false,
                        true,
                        true);
            case HEARTBEAT_EXPLICIT_DETAIL_SELECTION:
                return new Decision(
                        SemanticChannel.SELECTED_DETAIL_VALUE,
                        false,
                        true,
                        true,
                        false);
            case ADAM_SEND_CONFIRMATION:
                return new Decision(
                        SemanticChannel.STATUS_OR_STATE_DESCRIPTION,
                        false,
                        true,
                        true,
                        false);
            default:
                throw new IllegalArgumentException("unsupported consequence: " + consequence);
        }
    }
}
