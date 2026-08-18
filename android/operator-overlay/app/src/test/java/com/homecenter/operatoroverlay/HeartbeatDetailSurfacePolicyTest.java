package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatDetailSurfacePolicyTest {
    @Test
    public void longExplicitDetailRemainsExactAndScrollInspectable() {
        String detail = "Skill Regnet, fault. Why: source review. Consequence: boundary held. "
                + "Evidence: exact source identity remains visible after several lines of operator detail. "
                + "Source: repository skill skills/regnet/SKILL.md.";

        HeartbeatDetailSurfacePolicy.Presentation presentation =
                HeartbeatDetailSurfacePolicy.fromDetail(detail);

        assertEquals(detail, presentation.text);
        assertEquals(detail, presentation.contentDescription);
        assertEquals(HeartbeatDetailSurfacePolicy.MAX_VISIBLE_LINES, presentation.maxVisibleLines);
        assertFalse(presentation.ellipsizeEnd);
        assertTrue(presentation.verticallyScrollable);
        assertEquals(OverlayUiPolicy.MIN_TOUCH_TARGET_DP, presentation.minTouchTargetDp);
    }

    @Test
    public void emptyDetailUsesOneDeterministicInspectableFallback() {
        HeartbeatDetailSurfacePolicy.Presentation presentation =
                HeartbeatDetailSurfacePolicy.fromDetail("   ");

        assertEquals(HeartbeatDetailSurfacePolicy.EMPTY_DETAIL, presentation.text);
        assertEquals(presentation.text, presentation.contentDescription);
        assertFalse(presentation.ellipsizeEnd);
        assertTrue(presentation.verticallyScrollable);
    }

    @Test
    public void viewportPolicyDoesNotRewriteInteriorUnicodeOrEvidence() {
        String detail = "Why: warm\u200Bwall. Evidence: 👩‍💻 exact. Source: swan/veil.";

        HeartbeatDetailSurfacePolicy.Presentation presentation =
                HeartbeatDetailSurfacePolicy.fromDetail("  " + detail + "  ");

        assertEquals(detail, presentation.text);
        assertEquals(detail, presentation.contentDescription);
    }
}
