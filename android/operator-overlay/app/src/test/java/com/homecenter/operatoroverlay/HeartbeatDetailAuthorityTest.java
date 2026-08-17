package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.Collections;

import org.junit.Test;

public class HeartbeatDetailAuthorityTest {
    @Test
    public void sceneNodeDoesNotCacheLegacyDetailProjection() {
        try {
            HeartbeatSceneGraph.Node.class.getDeclaredField("detailContentDescription");
            fail("HeartbeatSceneGraph.Node must not cache a second detail projection.");
        } catch (NoSuchFieldException expected) {
            // One explicit-detail authority: HeartbeatEvidenceDetailProjection.
        }
    }

    @Test
    public void explicitConsumersShareCollisionSafeBoundedProjection() {
        String literalMarker = "\\" + "u{200B ZWSP}";
        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                "swan-veil-authority",
                "Swan\u200BVeil",
                "doctrine",
                "Swan\\Veil",
                "Warm\u2060wall",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Contact\u200Dholds",
                "Literal " + literalMarker + " versus actual \u200B");

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-detail-authority",
                Collections.singletonList(candidate),
                true,
                null);
        HeartbeatSceneGraph.Node node = frame.nodes.get(0);
        String expected = HeartbeatEvidenceDetailProjection.detailContentDescription(node);
        HeartbeatOverlayViewModel.LightControl control =
                HeartbeatOverlayViewModel.fromFrame(frame).controls.get(0);

        assertEquals(expected, control.detailContentDescription);
        assertEquals(
                expected,
                HeartbeatFrameAccessibility.detailContentDescription(frame, node.focusIndex));
        assertEquals(
                expected,
                HeartbeatFrameAccessibility.detailContentDescription(frame, node.id));
        assertTrue(expected.contains("Swan\\u{200B ZWSP}Veil"));
        assertTrue(expected.contains("Warm\\u{2060 WJ}wall"));
        assertTrue(expected.contains("Contact\\u{200D ZWJ}holds"));
        assertTrue(expected.contains(
                "Literal \\\\" + "u{200B ZWSP} versus actual \\u{200B ZWSP}"));
        assertFalse(control.contentDescription.contains("\\u{200B ZWSP}"));
    }
}
