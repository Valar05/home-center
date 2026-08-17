package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

public class HeartbeatEvidenceDetailProjectionTest {
    @Test
    public void boundedProjectionReservesTruncationSuffixInsideBudget() {
        String marker = "\\u{200B ZWSP}";
        String suffix = "… (truncated)";
        int budget = marker.codePointCount(0, marker.length())
                + suffix.codePointCount(0, suffix.length());
        String projected = HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection(
                "\u200B\u200B",
                budget);

        assertEquals(marker + suffix, projected);
        assertTrue(projected.codePointCount(0, projected.length()) <= budget);
    }

    @Test
    public void boundedProjectionNeverLetsTruncationIndicatorEscapeTheBudget() {
        String suffix = "… (truncated)";
        int budget = suffix.codePointCount(0, suffix.length());
        String projected = HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection(
                "A\u200B",
                budget);

        assertEquals(suffix, projected);
        assertEquals(budget, projected.codePointCount(0, projected.length()));
        assertEquals(
                "…",
                HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection("\u200B", 1));
    }

    @Test
    public void onDemandDetailRevealsInvisibleSemanticsWithoutChangingCompactSpeech() {
        String literalMarker = "\\" + "u{200B ZWSP}";
        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                "swan-veil",
                "Swan\u200BVeil",
                "doctrine",
                "Swan\\Veil",
                "Warm\u2060wall",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Contact\u200Dholds",
                "Literal " + literalMarker + " versus actual \u200B");

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-detail",
                Collections.singletonList(candidate),
                true,
                null);
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(frame);
        HeartbeatOverlayViewModel.LightControl control = model.controls.get(0);

        assertEquals(HeartbeatSkillPolicy.contentDescription(candidate), control.contentDescription);
        assertTrue(control.contentDescription.contains("Swan\u200BVeil"));
        assertTrue(control.detailContentDescription.contains("Swan\\u{200B ZWSP}Veil"));
        assertTrue(control.detailContentDescription.contains("Warm\\u{2060 WJ}wall"));
        assertTrue(control.detailContentDescription.contains("Contact\\u{200D ZWJ}holds"));
        assertTrue(control.detailContentDescription.contains(
                "Literal \\\\" + "u{200B ZWSP} versus actual \\u{200B ZWSP}"));
    }

    @Test
    public void markerExpansionIsBoundedAfterProjectionAndExactSceneEvidenceSurvives() {
        String manyInvisible = repeat("\u200B", 100);
        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                "bounded-veil",
                "Bounded Veil",
                "doctrine",
                "Swan Veil",
                manyInvisible,
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "Projection expansion is bounded",
                "Exact source remains in the scene");

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-bounded",
                Collections.singletonList(candidate),
                true,
                null);
        HeartbeatOverlayViewModel.LightControl control =
                HeartbeatOverlayViewModel.fromFrame(frame).controls.get(0);

        assertTrue(control.detailContentDescription.contains("Why: \\u{200B ZWSP}"));
        assertTrue(control.detailContentDescription.contains("… (truncated). Consequence:"));
        assertFalse(control.detailContentDescription.contains(manyInvisible));
        assertEquals(manyInvisible, frame.nodes.get(0).activationReason);
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
