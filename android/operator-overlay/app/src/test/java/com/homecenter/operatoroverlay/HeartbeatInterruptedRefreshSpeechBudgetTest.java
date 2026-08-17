package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

public class HeartbeatInterruptedRefreshSpeechBudgetTest {
    @Test
    public void visiblePulseSpeechKeepsEllipsisInsideNinetySixCodePointBudget() {
        String longPulseId = repeat("p", 120);
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                longPulseId,
                Collections.emptyList(),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "attempt",
                Collections.emptyList(),
                false,
                lastGood);

        String description = interrupted.interruptedRefreshDescription();
        String expectedProjection = repeat(
                "p",
                HeartbeatSceneGraph.MAX_SPOKEN_PULSE_ID_CODE_POINTS - 1) + "…";

        assertTrue(description.contains(
                "Showing last complete heartbeat " + expectedProjection + "."));
        assertFalse(description.contains(repeat(
                "p",
                HeartbeatSceneGraph.MAX_SPOKEN_PULSE_ID_CODE_POINTS) + "…"));
        assertEquals(longPulseId, interrupted.visiblePulseId);
    }

    @Test
    public void refreshBoundarySpeechKeepsUnicodeEllipsisInsideThreeTwentyCodePointBudget() {
        String swan = "🦢";
        String exactBoundary = repeat(swan, 400);
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.emptyList(),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt",
                lastGood,
                exactBoundary);

        String description = interrupted.interruptedRefreshDescription();
        String expectedProjection = repeat(
                swan,
                HeartbeatSceneGraph.MAX_SPOKEN_REFRESH_BOUNDARY_CODE_POINTS - 1) + "…";

        assertTrue(description.contains("Boundary: " + expectedProjection));
        assertFalse(description.contains(repeat(
                swan,
                HeartbeatSceneGraph.MAX_SPOKEN_REFRESH_BOUNDARY_CODE_POINTS) + "…"));
        assertEquals(exactBoundary, interrupted.refreshBoundary);
        assertEquals(
                HeartbeatSceneGraph.MAX_SPOKEN_REFRESH_BOUNDARY_CODE_POINTS,
                expectedProjection.codePointCount(0, expectedProjection.length()));
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
