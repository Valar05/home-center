package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/** Source-only regression for collapsed-owner status work before trim/composition. */
public class HeartbeatCollapsedOwnerStatusSourceWorkTest {
    @Test
    public void broadStatusCeilingKeepsOrdinaryTrimAndHeartbeatContact() {
        HeartbeatOverlayViewModel.Model model = oneLightModel();
        String status = "   Home Center active   ";

        String collapsed = HeartbeatCollapsedOwnerAccessibility.contentDescription(
                true,
                status,
                model);

        assertTrue(collapsed.contains("Home Center active."));
        assertTrue(collapsed.contains("HEARTBEAT • 1 LIGHT"));
    }

    @Test
    public void maxPlusOneTailCannotForceTrimPastFiniteSourceWindow() {
        HeartbeatOverlayViewModel.Model model = oneLightModel();
        String hostile = repeat(
                " ",
                HeartbeatCollapsedOwnerAccessibility.MAX_OPERATOR_STATUS_SOURCE_CODE_UNITS)
                + "UNBOUNDED-TAIL";

        String collapsed = HeartbeatCollapsedOwnerAccessibility.contentDescription(
                true,
                hostile,
                model);

        assertFalse(collapsed.contains("UNBOUNDED-TAIL"));
        assertTrue(collapsed.contains("…"));
        assertTrue(collapsed.contains("HEARTBEAT • 1 LIGHT"));
        assertTrue(collapsed.codePointCount(0, collapsed.length())
                <= HeartbeatCollapsedOwnerAccessibility.MAX_COLLAPSED_OWNER_CODE_POINTS);
    }

    @Test
    public void expandedOwnerDoesNotTouchOversizedCollapsedStatusInput() {
        String hostile = repeat(
                " ",
                HeartbeatCollapsedOwnerAccessibility.MAX_OPERATOR_STATUS_SOURCE_CODE_UNITS + 1)
                + "UNREAD";

        assertTrue(HeartbeatCollapsedOwnerAccessibility.contentDescription(
                false,
                hostile,
                oneLightModel()).equals(
                        HeartbeatCollapsedOwnerAccessibility.OVERLAY_ACTION_DESCRIPTION));
    }

    private static HeartbeatOverlayViewModel.Model oneLightModel() {
        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                "collapsed-status-source-work",
                "Collapsed status source work",
                "accessibility",
                "fixture:collapsed-status-source-work",
                "Direct collapsed owner status work must be finite before trim.",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Heartbeat contact remains visible after bounded status projection.",
                "Regression remains source-only until an authorized runner executes it.");
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-collapsed-status-source-work",
                Collections.singletonList(candidate),
                true,
                null);
        return HeartbeatOverlayViewModel.fromFrame(frame);
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder(value.length() * count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
