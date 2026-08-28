package com.homecenter.operatoroverlay;

import java.util.Locale;

/**
 * On-demand heartbeat detail projection for the existing Operator Overlay detail surface.
 *
 * <p>Compact/routine speech remains owned by {@link HeartbeatSkillPolicy#contentDescription}
 * and {@link HeartbeatFrameAccessibility#collapsedContentDescription}. This projection is
 * intentionally stronger only after an operator explicitly selects one visible heartbeat
 * light: legitimate invisible semantic controls become collision-safe evidence markers,
 * and the projected output is bounded <em>after</em> marker expansion.</p>
 *
 * <p>Exact canonical source/scene fields remain untouched. This class is the single typed
 * explicit-detail formatter for both Candidate-level compatibility callers and accepted
 * scene nodes. It owns no parser, renderer, controller, storage, transport, phone surface,
 * deployment, or P0 action.</p>
 */
public final class HeartbeatEvidenceDetailProjection {
    private HeartbeatEvidenceDetailProjection() {
    }

    /**
     * Bounded explicit evidence/TalkBack detail for one fully typed material Candidate.
     *
     * <p>Legacy candidates deliberately fall back to compact speech rather than inventing
     * typed provenance/evidence. Typed candidates use the same formatter as accepted scene
     * nodes, closing the older public Candidate bypass around invisible-control markers and
     * post-projection bounds.</p>
     */
    public static String detailContentDescription(HeartbeatSkillPolicy.Candidate candidate) {
        if (!HeartbeatSkillPolicy.isMaterial(candidate)) return "";
        if (!HeartbeatSkillPolicy.hasTypedSourceContract(candidate)) {
            return HeartbeatSkillPolicy.contentDescription(candidate);
        }
        return detailContentDescription(
                candidate.label,
                candidate.state,
                candidate.activationReason,
                candidate.consequence,
                candidate.evidenceBoundary,
                candidate.provenanceKind,
                candidate.provenanceLocator);
    }

    /**
     * Bounded explicit evidence/TalkBack detail for one already-accepted scene node.
     *
     * <p>Every human semantic field goes through the reserved evidence-marker namespace.
     * That means literal source backslashes are doubled even when no invisible control is
     * present, so literal marker-looking text cannot alias a projected invisible control.</p>
     */
    public static String detailContentDescription(HeartbeatSceneGraph.Node node) {
        if (node == null) return "";
        return detailContentDescription(
                node.label,
                node.state,
                node.activationReason,
                node.consequence,
                node.evidenceBoundary,
                node.provenanceKind,
                node.provenanceLocator);
    }

    private static String detailContentDescription(
            String label,
            HeartbeatSkillPolicy.State state,
            String activationReason,
            String consequence,
            String evidenceBoundary,
            String provenanceKind,
            String provenanceLocator) {
        return "Skill " + field(label, HeartbeatSkillPolicy.MAX_SPOKEN_LABEL_CODE_POINTS)
                + ", " + stateName(state)
                + ". Why: " + field(
                        activationReason,
                        HeartbeatSkillPolicy.MAX_DETAIL_REASON_CODE_POINTS)
                + ". Consequence: " + field(
                        consequence,
                        HeartbeatSkillPolicy.MAX_DETAIL_CONSEQUENCE_CODE_POINTS)
                + ". Evidence: " + field(
                        evidenceBoundary,
                        HeartbeatSkillPolicy.MAX_DETAIL_EVIDENCE_CODE_POINTS)
                + ". Source: " + humanizeProvenanceKind(provenanceKind)
                + " " + field(
                        provenanceLocator,
                        HeartbeatSkillPolicy.MAX_DETAIL_SOURCE_LOCATOR_CODE_POINTS)
                + ".";
    }

    private static String field(String value, int projectedCodePointBudget) {
        return HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection(
                clean(value),
                projectedCodePointBudget);
    }

    private static String stateName(HeartbeatSkillPolicy.State state) {
        return state == null ? "unknown" : state.name().toLowerCase(Locale.ROOT);
    }

    private static String humanizeProvenanceKind(String provenanceKind) {
        return clean(provenanceKind).replace('_', ' ');
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
