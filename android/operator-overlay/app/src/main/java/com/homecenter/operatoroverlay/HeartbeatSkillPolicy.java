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
    /** Hard returned label-speech budget from one focused light. Exact candidate text remains unchanged. */
    public static final int MAX_SPOKEN_LABEL_CODE_POINTS = 96;
    /** Hard returned consequence-speech budget in the compact focus description. */
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
        /** Captures decoded safety before constructor trim can normalize edge controls away. */
        private final boolean semanticTextSafeAtIngress;

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
            this.semanticTextSafeAtIngress = isSafeSemanticText(id)
                    && isSafeSemanticText(label)
                    && isSafeSemanticText(provenanceKind)
                    && isSafeSemanticText(provenanceLocator)
                    && isSafeSemanticText(activationReason)
                    && isSafeSemanticText(consequence)
                    && isSafeSemanticText(evidenceBoundary);
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
     *
     * Canonical typed fields also have to be safe for visible/touch/speech use.
     * Directional-format controls are rejected rather than normalized so exact
     * canonical source identity cannot silently change before checkpointing or
     * evidence review. Ordinary human-facing Unicode remains data, including ZWJ
     * sequences. The machine semantic id is intentionally narrower: display-ready
     * ids use an ASCII token alphabet so Locale.ROOT folding and equalsIgnoreCase
     * ownership cannot disagree about which native control one id names.
     *
     * Direct source construction is held to the same field-size contract as the
     * canonical wire parser. Speech has its own tighter projection bounds, but those
     * do not make oversized source records safe for scene hashing, native ownership,
     * touch detail, or checkpoint/evidence work. Reusing the parser constants keeps
     * parser and direct-scene ingress from drifting into two different contracts.
     */
    public static boolean hasTypedSourceContract(Candidate candidate) {
        if (candidate == null
                || candidate.id.isEmpty()
                || candidate.label.isEmpty()
                || candidate.consequence.isEmpty()) return false;
        if (!hasSafeSemanticSurface(candidate)) return false;
        if (!isWithinTypedSourceBounds(candidate)) return false;
        if (!isDeterministicSemanticId(candidate.id)) return false;
        if (!isAllowedProvenanceKind(candidate.provenanceKind)) return false;
        if (!isAllowedProvenanceLocator(candidate.provenanceKind, candidate.provenanceLocator)) {
            return false;
        }
        return !candidate.activationReason.isEmpty()
                && !candidate.evidenceBoundary.isEmpty();
    }

    /**
     * Keep direct Candidate ingress byte-for-byte aligned with the canonical parser's
     * post-trim Java String bounds. These are source/evidence bounds, not speech
     * limits, so do not replace them with the smaller TalkBack projection constants.
     */
    private static boolean isWithinTypedSourceBounds(Candidate candidate) {
        return candidate.id.length() <= HeartbeatEnvelopeParser.MAX_ID_CHARS
                && candidate.label.length() <= HeartbeatEnvelopeParser.MAX_LABEL_CHARS
                && candidate.provenanceKind.length()
                        <= HeartbeatEnvelopeParser.MAX_PROVENANCE_KIND_CHARS
                && candidate.provenanceLocator.length()
                        <= HeartbeatEnvelopeParser.MAX_PROVENANCE_LOCATOR_CHARS
                && candidate.activationReason.length()
                        <= HeartbeatEnvelopeParser.MAX_ACTIVATION_REASON_CHARS
                && candidate.consequence.length()
                        <= HeartbeatEnvelopeParser.MAX_CONSEQUENCE_CHARS
                && candidate.evidenceBoundary.length()
                        <= HeartbeatEnvelopeParser.MAX_EVIDENCE_BOUNDARY_CHARS;
    }

    /**
     * Compact focus description. Spoken label and consequence are deliberately
     * hard-bounded over the returned projection, including any ellipsis, so a direct
     * source caller cannot turn one focus action into an unbounded TalkBack burst.
     * Exact candidate fields remain unchanged for explicit inspection/evidence handling.
     */
    public static String contentDescription(Candidate candidate) {
        if (!isMaterial(candidate) || !hasSafeSemanticSurface(candidate)) return "";
        return "Skill " + compactSpeechField(
                        candidate.label,
                        MAX_SPOKEN_LABEL_CODE_POINTS)
                + ", " + candidate.state.name().toLowerCase(Locale.ROOT)
                + ". " + compactSpeechField(
                        candidate.consequence,
                        MAX_COMPACT_CONSEQUENCE_CODE_POINTS)
                + ".";
    }

    /**
     * Expanded TalkBack/touch detail for a fully typed heartbeat source record.
     *
     * <p>Legacy candidates intentionally fall back to compact speech rather than
     * inventing provenance, activation reason, or evidence they do not carry. Fully
     * typed candidates delegate to the single collision-safe, post-projection-bounded
     * {@link HeartbeatEvidenceDetailProjection} authority used by accepted scene nodes.
     * Exact Candidate fields remain unchanged for non-speech inspection/evidence.</p>
     */
    public static String detailContentDescription(Candidate candidate) {
        if (!isMaterial(candidate) || !hasSafeSemanticSurface(candidate)) return "";
        if (!hasTypedSourceContract(candidate)) return contentDescription(candidate);
        return HeartbeatEvidenceDetailProjection.detailContentDescription(candidate);
    }

    /**
     * TalkBack description for the collapsed overlay.
     *
     * This legacy candidate-level projection is retained for compatibility. New
     * scene consumers should use HeartbeatFrameAccessibility so interrupted contact,
     * broad-summary bounds, and attention-first naming are derived from the exact
     * visible frame. Unsafe legacy candidates are never named; the summary reports
     * an exact omission count instead of claiming a count and then silently speaking
     * nothing for a spoofable material light.
     */
    public static String collapsedContentDescription(List<Candidate> candidates) {
        List<Candidate> selected = selectMaterialLights(candidates);
        if (selected.isEmpty()) return "No material skill lights.";

        List<String> descriptions = new ArrayList<>();
        int rejected = 0;
        for (Candidate candidate : selected) {
            String description = contentDescription(candidate);
            if (description.isEmpty()) rejected++;
            else descriptions.add(description);
        }

        StringBuilder out = new StringBuilder();
        if (!descriptions.isEmpty()) {
            out.append(descriptions.size())
                    .append(descriptions.size() == 1
                            ? " material skill light. "
                            : " material skill lights. ");
            for (String description : descriptions) out.append(description).append(' ');
        }
        if (rejected > 0) {
            out.append(rejected)
                    .append(rejected == 1
                            ? " material light was omitted from speech because its semantic text was rejected."
                            : " material lights were omitted from speech because their semantic text was rejected.");
        }
        return out.toString().trim();
    }

    /**
     * Deterministic machine identity for heartbeat ownership.
     *
     * <p>Human labels/reasons/evidence remain Unicode. The semantic id is different:
     * it is used by parser dedupe, scene/model lookup, native Button tags, selection,
     * viewport restore, structure hashing, and transition hashing. Those paths have
     * historically mixed Locale.ROOT lowercase keys with String.equalsIgnoreCase.
     * Their Unicode equivalence sets are not identical. Restricting the typed id to
     * ASCII letters/digits plus a small path/token punctuation set makes both
     * operations agree while preserving existing ASCII case-tolerant behavior.</p>
     *
     * <p>Canonical producers should still emit stable lowercase ids. Uppercase ASCII
     * remains accepted so case-only producer drift stays an evidence change rather
     * than suddenly becoming a parser migration break.</p>
     */
    static boolean isDeterministicSemanticId(String value) {
        String id = clean(value);
        if (id.isEmpty()) return false;
        for (int index = 0; index < id.length(); index++) {
            char c = id.charAt(index);
            boolean asciiLetter = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
            boolean digit = c >= '0' && c <= '9';
            boolean punctuation = c == '-' || c == '_' || c == '.' || c == '/' || c == ':';
            if (!(asciiLetter || digit || punctuation)) return false;
        }
        return true;
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

    /**
     * Decoded semantic text that can later become visible, spoken, or fingerprinted.
     *
     * Empty text is structurally safe here; callers separately decide which fields
     * are required. ISO controls, malformed UTF-16, and directional bidi controls
     * fail closed. We intentionally do not reject every Unicode FORMAT code point:
     * U+200D ZERO WIDTH JOINER is legitimate inside emoji/grapheme sequences and is
     * not itself a directional spoofing control.
     */
    static boolean isSafeSemanticText(String value) {
        if (value == null || value.isEmpty()) return true;
        for (int index = 0; index < value.length();) {
            char c = value.charAt(index);
            if (Character.isHighSurrogate(c)) {
                if (index + 1 >= value.length()
                        || !Character.isLowSurrogate(value.charAt(index + 1))) {
                    return false;
                }
                int codePoint = Character.toCodePoint(c, value.charAt(index + 1));
                if (isBidiDirectionalControl(codePoint)) return false;
                index += 2;
                continue;
            }
            if (Character.isLowSurrogate(c)) return false;
            if (Character.isISOControl(c)) return false;
            if (isBidiDirectionalControl(c)) return false;
            index++;
        }
        return true;
    }

    private static boolean hasSafeSemanticSurface(Candidate candidate) {
        return candidate != null
                && candidate.semanticTextSafeAtIngress
                && isSafeSemanticText(candidate.id)
                && isSafeSemanticText(candidate.label)
                && isSafeSemanticText(candidate.provenanceKind)
                && isSafeSemanticText(candidate.provenanceLocator)
                && isSafeSemanticText(candidate.activationReason)
                && isSafeSemanticText(candidate.consequence)
                && isSafeSemanticText(candidate.evidenceBoundary);
    }

    private static boolean isBidiDirectionalControl(int codePoint) {
        return codePoint == 0x061C
                || codePoint == 0x200E
                || codePoint == 0x200F
                || (codePoint >= 0x202A && codePoint <= 0x202E)
                || (codePoint >= 0x2066 && codePoint <= 0x2069);
    }

    private static String compactSpeechField(String value, int maxCodePoints) {
        return HeartbeatPlainTextBudget.boundedWithEllipsis(
                clean(value),
                maxCodePoints);
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
