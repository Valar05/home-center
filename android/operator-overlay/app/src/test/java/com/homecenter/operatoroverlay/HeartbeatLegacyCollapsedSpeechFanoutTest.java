package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.List;
import org.junit.Test;

public final class HeartbeatLegacyCollapsedSpeechFanoutTest {
    @Test
    public void broadLegacyConstellationNamesOnlySharedCollapsedBudgetAndReportsRemainder() {
        List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
        int total = HeartbeatSkillPolicy.MAX_COLLAPSED_NAMED_LIGHTS + 8;
        for (int index = 0; index < total; index++) {
            candidates.add(blocked(index, "Light " + twoDigits(index)));
        }

        String speech = HeartbeatSkillPolicy.collapsedContentDescription(candidates);

        assertTrue(speech.startsWith(total + " material skill lights. "));
        for (int index = 0; index < HeartbeatSkillPolicy.MAX_COLLAPSED_NAMED_LIGHTS; index++) {
            assertTrue(speech.contains("Skill Light " + twoDigits(index) + ", blocked."));
        }
        assertFalse(speech.contains(
                "Skill Light " + twoDigits(HeartbeatSkillPolicy.MAX_COLLAPSED_NAMED_LIGHTS)
                        + ", blocked."));
        assertTrue(speech.contains(
                "8 additional material light descriptions are omitted from collapsed speech by the naming budget."));
    }

    @Test
    public void unsafeOmissionRemainsSeparateFromSafeFanoutOmission() {
        List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
        int safeCount = HeartbeatSkillPolicy.MAX_COLLAPSED_NAMED_LIGHTS + 1;
        for (int index = 0; index < safeCount; index++) {
            candidates.add(blocked(index, "Safe " + twoDigits(index)));
        }
        candidates.add(new HeartbeatSkillPolicy.Candidate(
                "unsafe",
                "\u202Epoison",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Unsafe semantic text must never be spoken"));

        String speech = HeartbeatSkillPolicy.collapsedContentDescription(candidates);

        assertTrue(speech.startsWith(safeCount + " material skill lights. "));
        assertTrue(speech.contains(
                "1 additional material light description is omitted from collapsed speech by the naming budget."));
        assertTrue(speech.contains(
                "1 material light was omitted from speech because its semantic text was rejected."));
        assertFalse(speech.contains("poison"));
    }

    @Test
    public void withinBudgetCompatibilityStringDoesNotGrowNewFanoutProse() {
        List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
        candidates.add(blocked(0, "Regnet QA"));
        candidates.add(blocked(1, "Venice"));

        String speech = HeartbeatSkillPolicy.collapsedContentDescription(candidates);

        assertTrue(speech.contains("2 material skill lights."));
        assertTrue(speech.contains("Skill Regnet QA, blocked. Boundary 00."));
        assertTrue(speech.contains("Skill Venice, blocked. Boundary 01."));
        assertFalse(speech.contains("naming budget"));
    }

    private static HeartbeatSkillPolicy.Candidate blocked(int index, String label) {
        return new HeartbeatSkillPolicy.Candidate(
                "light-" + index,
                label,
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Boundary " + twoDigits(index));
    }

    private static String twoDigits(int value) {
        return value < 10 ? "0" + value : Integer.toString(value);
    }
}
