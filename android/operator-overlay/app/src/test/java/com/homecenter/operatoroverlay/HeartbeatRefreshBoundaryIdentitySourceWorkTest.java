package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;

import java.util.Collections;

import org.junit.Test;

/** Source regression for bounded interrupted-refresh render/announcement identity work. */
public class HeartbeatRefreshBoundaryIdentitySourceWorkTest {
    @Test
    public void overCeilingBoundariesWithSameLengthShareBoundedUiIdentityButKeepExactEvidence() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.emptyList(),
                true,
                null);
        int hostileLength =
                HeartbeatOverlayRefreshPlan.MAX_REFRESH_BOUNDARY_IDENTITY_SOURCE_CODE_UNITS + 1;
        String firstExact = repeat("a", hostileLength);
        String secondExact = repeat("b", hostileLength);

        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt-one",
                lastGood,
                firstExact);
        HeartbeatSceneGraph.Frame secondFrame = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt-two",
                lastGood,
                secondExact);
        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "");
        HeartbeatOverlayRefreshPlan.Plan second =
                HeartbeatOverlayRefreshPlan.fromFrame(secondFrame, "");

        assertNotEquals(firstFrame.refreshBoundary, secondFrame.refreshBoundary);
        assertEquals(firstExact, firstFrame.refreshBoundary);
        assertEquals(secondExact, secondFrame.refreshBoundary);
        assertEquals(first.renderIdentity, second.renderIdentity);
        assertEquals(first.announcementIdentity, second.announcementIdentity);
    }

    @Test
    public void admittedBoundariesStillParticipateExactlyInUiIdentity() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-good",
                Collections.emptyList(),
                true,
                null);
        int admittedLength =
                HeartbeatOverlayRefreshPlan.MAX_REFRESH_BOUNDARY_IDENTITY_SOURCE_CODE_UNITS;
        HeartbeatSceneGraph.Frame firstFrame = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt-one",
                lastGood,
                repeat("a", admittedLength));
        HeartbeatSceneGraph.Frame secondFrame = HeartbeatSceneGraph.preserveRejectedRefresh(
                "attempt-two",
                lastGood,
                repeat("b", admittedLength));

        HeartbeatOverlayRefreshPlan.Plan first =
                HeartbeatOverlayRefreshPlan.fromFrame(firstFrame, "");
        HeartbeatOverlayRefreshPlan.Plan second =
                HeartbeatOverlayRefreshPlan.fromFrame(secondFrame, "");

        assertNotEquals(first.renderIdentity, second.renderIdentity);
        assertNotEquals(first.announcementIdentity, second.announcementIdentity);
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
