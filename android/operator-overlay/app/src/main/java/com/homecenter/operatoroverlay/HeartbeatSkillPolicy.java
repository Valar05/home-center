package com.homecenter.operatoroverlay;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Pure policy for selecting semantic heartbeat skill lights.
 *
 * The overlay must not render a skill merely because it exists. A rendered light
 * must expose a material consequence from the current heartbeat, or a current
 * blocked/fault boundary that the operator needs to know about.
 */
public final class HeartbeatSkillPolicy {
    /** Maximum consequence speech in the compact focus description. */
    public static final int MAX_COMPACT_CONSEQUENCE_CODE_POINTS = 160;
    /** Expanded detail is on-demand, but still must not become a multi-kilobyte speech burst. */
    public static final int MAX_DETAIL_REASON_CODE_POINTS = 256;
    public static final int MAX_DETAIL_CONSEQUENCE_CODE_POINTS = 320;
    public static final int MAX_DETAIL_EVIDENCE_CODE_POINTS = 384;
    public static final int MAX_DETAIL_SOURCE_LOCATOR_CODE_POINTS = 192;

    public enum State {
        DARK,
        ACTIVE,
        BLOCKED,
        FAULT,
        RECOVERED
    }

    public static final class Candidate {
        public final String id;
        public final String label;
        public final String provenanceKind;
        public final String provenanceLocator;
        public final String activationReason;
        public final State state;
        public final boolean changedThisPulse;
        public final String consequence;
        public final String evidenceBoundary;

        /**
         * Legacy source-only constructor. Typed provenance remains explicitly empty
         * until an upstream owner supplies the full heartbeat source contract.
         */
        public Candidate(
                String id,
                String label,
                State state,
                boolean changedThisPulse,
                String consequence) {
            this(id, label, "", "", "", state, changedThisPulse, consequence, "");
        }

        public Candidate(
                String id,
                String label,
                String provenanceKind,
                String provenanceLocator,
                String activationReason,
                State state,
                boolean changedThisPulse,
                String consequence,
                String evidenceBoundary) {
            this.id = clean(id);
            this.label = clean(label);
            this.provenanceKind = clean(provenanceKind);
            this.provenanceLocator = clean(provenanceLocator);
            this.activationReason = clean(activationReason);
            this.state = state == null ? State.DARK : state;
            this.changedThisPulse = changedThisPulse;
            this.consequence = clean(consequence);
            this.evidenceBoundary = clean(evidenceBoundary);
        }
    }

    private HeartbeatSkillPolicy() {
    }

    public static List<Candidate> selectMaterialLights(List<Candidate> candidates) {
        if (candidates == null || candidates.isEmpty()) return Collections.emptyList();

        List<Candidate> selected = new ArrayList<>();
        Set<String> seenIds = new HashSet<>();
        for (Candidate candidate : candidates) {
            if (!isMaterial(candidate)) continue;
            String dedupeKey = candidate.id.toLowerCase(Locale.ROOT);
            if (!seenIds.add(dedupeKey)) continue;
            selected.add(candidate);
        }
        return Collections.unmodifiableList(selected);
    }

    /**
     * Strict source-side gate for candidates that are both materially relevant and
     * complete enough to be rendered later.
     *
     * This does not wire the overlay and does not change legacy material selection;
     * it gives the future renderer/parser a fail-closed path that cannot silently
     * promote legacy candidates with missing provenance/evidence into display-ready
     * state.
     */
    public static List<Candidate> selectDisplayReadyLights(List<Candidate> candidates) {
        List<Candidate> material = selectMaterialLights(candidates);
        if (material.isEmpty()) return material;

        List<Candidate> displayReady = new ArrayList<>();
        for (Candidate candidate : material) {
            if (hasTypedSourceContract(candidate)) displayReady.add(candidate);
        }
        return Collections.unmodifiableList(displayReady);
    }

    public static boolean isMaterial(Candidate candidate) {
        if (candidate == null || candidate.id.isEmpty() || candidate.label.isEmpty()) return false;
        if (candidate.consequence.isEmpty()) return false;

        switch (candidate.state) {
            case ACTIVE:
            case RECOVERED:
                return candidate.changedThisPulse;
            case BLOCKED:
            case FAULT:
                return true;
            case DARK:
            default:
                return false;
        }
    }

    /**
     * True only when the candidate carries the complete typed source envelope.
     *
     * This deliberately does not change legacy materiality. Legacy candidates stay
     * selectable until the existing ingress owner is migrated, but callers can now
     * distinguish them from records that satisfy the durable source contract.
     */
    public static boolean hasTypedSourceContract(Candidate candidate) {
        if (candidate == null
                || candidate.id.isEmpty()
                || candidate.label.isEmpty()
                || candidate.consequence.isEmpty()) return false;
        if (!isAllowedProvenanceKind(candidate.provenanceKind)) return false;
        if (!isAllowedProvenanceLocator(candidate.provenanceKind, candidate.provenanceLocator)) {
            return false;
        }
        return !candidate.activationReason.isEmpty()
                && !candidate.evidenceBoundary.isEmpty();
    }

    /**
     * Compact focus description. The consequence is deliberately bounded so focus
     * movement across a broad constellation cannot trigger a multi-kilobyte speech
     * burst. Expanded typed speech detail is available through
     * {@link #detailContentDescription(Candidate)} while the exact typed fields stay
     * on {@link Candidate} for non-speech inspection and evidence handling.
     */
    public static String contentDescription(Candidate candidate) {
        if (!isMaterial(candidate)) return "";
        return "Skill " + candidate.label + ", "
                + candidate.state.name().toLowerCase(Locale.ROOT)
                + ". " + compactSpeechField(
                        candidate.consequence,
                        MAX_COMPACT_CONSEQUENCE_CODE_POINTS)
                + ".";
    }

    /**
     * Expanded TalkBack/touch detail for a fully typed heartbeat source record.
     *
     * <p>The Candidate retains the complete typed fields for explicit non-speech
     * inspection and evidence handling. This spoken projection independently caps
     * each large semantic field by Unicode code point and marks truncation, so a
     * legal parser-bounded record cannot turn one focus action into a multi-kilobyte
     * TalkBack monologue or split a surrogate pair.</p>
     *
     * <p>Legacy candidates intentionally fall back to the compact description rather
     * than inventing provenance, activation reason, or evidence they do not carry.</p>
     */
    public static String detailContentDescription(Candidate candidate) {
        if (!isMaterial(candidate)) return "";
        if (!hasTypedSourceContract(candidate)) return contentDescription(candidate);
        return "Skill " + candidate.label + ", "
                + candidate.state.name().toLowerCase(Locale.ROOT)
                + ". Why: " + boundedDetailSpeechField(
                        candidate.activationReason,
                        MAX_DETAIL_REASON_CODE_POINTS)
                + ". Consequence: " + boundedDetailSpeechField(
                        candidate.consequence,
                        MAX_DETAIL_CONSEQUENCE_CODE_POINTS)
                + ". Evidence: " + boundedDetailSpeechField(
                        candidate.evidenceBoundary,
                        MAX_DETAIL_EVIDENCE_CODE_POINTS)
                + ". Source: " + humanizeProvenanceKind(candidate.provenanceKind)
                + " " + boundedDetailSpeechField(
                        candidate.provenanceLocator,
                        MAX_DETAIL_SOURCE_LOCATOR_CODE_POINTS)
                + ".";
    }

    /**
     * TalkBack description for the collapsed overlay.
     *
     * This legacy candidate-level projection is retained for compatibility. New
     * scene consumers should use HeartbeatFrameAccessibility so interrupted contact,
     * broad-summary bounds, and attention-first naming are derived from the exact
     * visible frame.
     */
    public static String collapsedContentDescription(List<Candidate> candidates) {
        List<Candidate> selected = selectMaterialLights(candidates);
        if (selected.isEmpty()) return "No material skill lights.";

        StringBuilder out = new StringBuilder();
        out.append(selected.size())
                .append(selected.size() == 1 ? " material skill light. " : " material skill lights. ");
        for (Candidate candidate : selected) {
            out.append(contentDescription(candidate)).append(' ');
        }
        return out.toString().trim();
    }

    private static boolean isAllowedProvenanceKind(String provenanceKind) {
        switch (provenanceKind) {
            case "repository_skill":
            case "doctrine":
            case "jar":
            case "reviewer":
            case "runtime_boundary":
                return true;
            default:
                return false;
        }
    }

    /**
     * Source-side provenance shape validation. Repository existence is deliberately
     * not claimed here: the pure policy cannot query GitHub. It can, however, reject
     * a repository-skill record whose locator is not an exact skill-file-shaped path.
     */
    private static boolean isAllowedProvenanceLocator(
            String provenanceKind,
            String provenanceLocator) {
        String locator = clean(provenanceLocator);
        if (locator.isEmpty()) return false;
        if (!"repository_skill".equals(provenanceKind)) return true;
        return locator.startsWith("skills/")
                && locator.endsWith("/SKILL.md")
                && locator.indexOf('\\') < 0
                && !locator.contains("../")
                && !locator.contains("/./")
                && !locator.contains("//");
    }

    private static String humanizeProvenanceKind(String provenanceKind) {
        return provenanceKind.replace('_', ' ');
    }

    private static String compactSpeechField(String value, int maxCodePoints) {
        String clean = clean(value);
        if (clean.isEmpty() || maxCodePoints <= 0) return clean;
        int codePoints = clean.codePointCount(0, clean.length());
        if (codePoints <= maxCodePoints) return clean;
        int end = clean.offsetByCodePoints(0, maxCodePoints);
        return clean.substring(0, end) + "…";
    }

    private static String boundedDetailSpeechField(String value, int maxCodePoints) {
        String clean = clean(value);
        if (clean.isEmpty() || maxCodePoints <= 0) return clean;
        int codePoints = clean.codePointCount(0, clean.length());
        if (codePoints <= maxCodePoints) return clean;
        int end = clean.offsetByCodePoints(0, maxCodePoints);
        return clean.substring(0, end) + "… (truncated)";
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
