package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Test;

/**
 * Source regression for the direct previous refresh-identity work throat.
 *
 * <p>Generated identities are small, but the public decision helpers are callable
 * with arbitrary Strings. The broad gate must run before trim/equality while
 * preserving the established at-or-below-ceiling behavior and fail-closed speech
 * semantics above the ceiling.</p>
 *
 * <p>SOURCE ONLY until an authorized runner executes this fixture.</p>
 */
public class HeartbeatPreviousRefreshIdentitySourceWorkTest {
    @Test
    public void atCeilingPreservesTrimmedIdentityWhileMaxPlusOneFailsClosed() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-source-work",
                Collections.singletonList(new HeartbeatSkillPolicy.Candidate(
                        "contact",
                        "Contact Preservation",
                        "doctrine",
                        "fixture:previous-refresh-identity",
                        "Previous identity source work is bounded",
                        HeartbeatSkillPolicy.State.ACTIVE,
                        true,
                        "Existing contact remains stable",
                        "Exact fixture boundary")),
                true,
                null);
        HeartbeatOverlayRefreshPlan.Plan plan =
                HeartbeatOverlayRefreshPlan.fromFrame(frame, "contact");

        int max = HeartbeatOverlayRefreshPlan.MAX_DIRECT_SELECTION_ID_SOURCE_CODE_UNITS;
        String structureAtMax = leftPadToLength(plan.structureIdentity, max);
        String renderAtMax = leftPadToLength(plan.renderIdentity, max);
        String announceAtMax = leftPadToLength(plan.announcementIdentity, max);

        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(structureAtMax, plan));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRefreshContent(renderAtMax, plan));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldRebuild(renderAtMax, plan));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(announceAtMax, plan));

        String structureTooLong = " " + structureAtMax;
        String renderTooLong = " " + renderAtMax;
        String announceTooLong = " " + announceAtMax;

        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuildStructure(structureTooLong, plan));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRefreshContent(renderTooLong, plan));
        assertTrue(HeartbeatOverlayRefreshPlan.shouldRebuild(renderTooLong, plan));
        assertFalse(HeartbeatOverlayRefreshPlan.shouldAnnounce(announceTooLong, plan));
    }

    private static String leftPadToLength(String value, int length) {
        StringBuilder out = new StringBuilder(length);
        for (int i = value.length(); i < length; i++) out.append(' ');
        out.append(value);
        return out.toString();
    }
}
