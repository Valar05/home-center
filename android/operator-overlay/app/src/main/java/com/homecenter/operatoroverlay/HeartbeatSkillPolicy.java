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
        public final State state;
        public final boolean changedThisPulse;
        public final String consequence;

        public Candidate(
                String id,
                String label,
                State state,
                boolean changedThisPulse,
                String consequence) {
            this.id = clean(id);
            this.label = clean(label);
            this.state = state == null ? State.DARK : state;
            this.changedThisPulse = changedThisPulse;
            this.consequence = clean(consequence);
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

    public static String contentDescription(Candidate candidate) {
        if (!isMaterial(candidate)) return "";
        return "Skill " + candidate.label + ", "
                + candidate.state.name().toLowerCase(Locale.ROOT)
                + ". " + candidate.consequence + ".";
    }

    /**
     * TalkBack description for the collapsed overlay.
     *
     * Collapsing the visual panel must not collapse away the material states. The
     * description reuses the same selected order/dedupe policy as the rendered
     * lights and carries each exact state + consequence instead of reporting only
     * a decorative count.
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

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
