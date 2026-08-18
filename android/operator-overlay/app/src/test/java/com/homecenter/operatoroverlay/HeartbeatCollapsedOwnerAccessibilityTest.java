package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.junit.Test;

/**
 * Regression source for the accessibility projection consumed by the existing
 * drag handle while the heartbeat details subtree is collapsed.
 */
public class HeartbeatCollapsedOwnerAccessibilityTest {
    @Test
    public void acceptedZeroMaterialContactMustReachCollapsedOwnerSurface() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-zero-collapsed-owner",
                Collections.emptyList(),
                true,
                null);
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(accepted);

        String collapsed = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, model);

        assertTrue(collapsed.startsWith(
                HeartbeatCollapsedOwnerAccessibility.COLLAPSED_ACTION_DESCRIPTION));
        assertTrue(collapsed.contains("HEARTBEAT • 0 LIGHTS"));
        assertTrue(collapsed.contains(
                HeartbeatCollapsedOwnerAccessibility.ACCEPTED_ZERO_MATERIAL_DESCRIPTION));
        assertFalse(collapsed.toLowerCase(java.util.Locale.ROOT).contains("waiting"));
        assertTrue(model.attentionStatusDescription.isEmpty());
    }

    @Test
    public void broadPulseKeepsAttentionCountsButPerLightEnumerationBehindExpansion() {
        List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
        for (int index = 0; index < 20; index++) {
            HeartbeatSkillPolicy.State state = index == 0
                    ? HeartbeatSkillPolicy.State.BLOCKED
                    : index == 1
                            ? HeartbeatSkillPolicy.State.FAULT
                            : HeartbeatSkillPolicy.State.ACTIVE;
            candidates.add(typed(
                    "broad-" + index,
                    "Long broad label " + index + " " + repeat("🦢", 55),
                    state));
        }
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-broad-collapsed-owner",
                candidates,
                true,
                null);
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(frame);

        String expandedDetail = model.collapsedContentDescription;
        String collapsedOwner = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, model);

        assertEquals(20, model.controls.size());
        assertEquals("Attention: blocked 1, fault 1.", model.attentionStatusDescription);
        assertTrue(expandedDetail.contains("Long broad label 0"));
        assertTrue(expandedDetail.codePointCount(0, expandedDetail.length())
                > HeartbeatCollapsedOwnerAccessibility.MAX_COLLAPSED_OWNER_CODE_POINTS);
        assertTrue(collapsedOwner.contains("HEARTBEAT • 20 LIGHTS"));
        assertTrue(collapsedOwner.contains("Attention: blocked 1, fault 1."));
        assertTrue(collapsedOwner.contains("Tap to expand for heartbeat details."));
        assertFalse(collapsedOwner.contains("Long broad label 0"));
        assertFalse(collapsedOwner.contains("States:"));
        assertTrue(collapsedOwner.codePointCount(0, collapsedOwner.length())
                <= HeartbeatCollapsedOwnerAccessibility.MAX_COLLAPSED_OWNER_CODE_POINTS);
    }

    @Test
    public void rejectedAttemptCannotLeakDiscardedFaultIntoCollapsedAttention() {
        HeartbeatSceneGraph.Frame lastGood = HeartbeatSceneGraph.build(
                "pulse-attention-last-good",
                Collections.singletonList(typed(
                        "steady",
                        "Steady last-good light",
                        HeartbeatSkillPolicy.State.ACTIVE)),
                true,
                null);
        HeartbeatSceneGraph.Frame rejected = HeartbeatSceneGraph.build(
                "pulse-attention-rejected",
                Collections.singletonList(typed(
                        "discarded-fault",
                        "Discarded attempted fault",
                        HeartbeatSkillPolicy.State.FAULT)),
                false,
                lastGood);
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(rejected);

        String collapsed = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, model);

        assertTrue(model.refreshInterrupted);
        assertEquals("pulse-attention-last-good", model.visiblePulseId);
        assertTrue(model.attentionStatusDescription.isEmpty());
        assertTrue(collapsed.contains("CONTACT HELD"));
        assertFalse(collapsed.contains("fault 1"));
        assertFalse(collapsed.contains("Discarded attempted fault"));
    }

    @Test
    public void preContactWaitingIsDistinctOnTheSameCollapsedSurface() {
        String collapsed = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, null);

        assertTrue(collapsed.startsWith(
                HeartbeatCollapsedOwnerAccessibility.COLLAPSED_ACTION_DESCRIPTION));
        assertTrue(collapsed.contains(
                HeartbeatCollapsedOwnerAccessibility.WAITING_DESCRIPTION));
        assertFalse(collapsed.contains("HEARTBEAT • 0 LIGHTS"));
        assertFalse(collapsed.contains("CONTACT HELD"));
        assertFalse(collapsed.contains("REFRESH BLOCKED"));
    }

    @Test
    public void heldAndBlockedWoundsRemainDistinctOnCollapsedSurface() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-zero-held-owner",
                Collections.emptyList(),
                true,
                null);
        HeartbeatOverlayViewModel.Model held = HeartbeatOverlayViewModel.fromFrame(
                HeartbeatSceneGraph.preserveRejectedRefresh(
                        "",
                        accepted,
                        "fixture held wound"));
        HeartbeatOverlayViewModel.Model blocked = HeartbeatOverlayViewModel.fromFrame(
                HeartbeatSceneGraph.preserveRejectedRefresh(
                        "",
                        null,
                        "fixture pre-contact wound"));

        String heldDescription = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, held);
        String blockedDescription = HeartbeatCollapsedOwnerAccessibility.contentDescription(true, blocked);

        assertTrue(heldDescription.contains("HEARTBEAT • CONTACT HELD"));
        assertTrue(heldDescription.contains(
                HeartbeatCollapsedOwnerAccessibility.HELD_ZERO_MATERIAL_DESCRIPTION));
        assertTrue(heldDescription.contains("Last good heartbeat contact is preserved"));
        assertTrue(blockedDescription.contains("HEARTBEAT • REFRESH BLOCKED"));
        assertTrue(blockedDescription.contains(
                "Refresh blocked before any heartbeat contact was accepted"));
        assertTrue(heldDescription.codePointCount(0, heldDescription.length())
                <= HeartbeatCollapsedOwnerAccessibility.MAX_COLLAPSED_OWNER_CODE_POINTS);
        assertTrue(blockedDescription.codePointCount(0, blockedDescription.length())
                <= HeartbeatCollapsedOwnerAccessibility.MAX_COLLAPSED_OWNER_CODE_POINTS);
    }

    @Test
    public void expandedOwnerKeepsOrdinaryOverlayActionDescription() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-expanded-owner",
                Collections.emptyList(),
                true,
                null);
        HeartbeatOverlayViewModel.Model model = HeartbeatOverlayViewModel.fromFrame(accepted);

        assertEquals(
                HeartbeatCollapsedOwnerAccessibility.OVERLAY_ACTION_DESCRIPTION,
                HeartbeatCollapsedOwnerAccessibility.contentDescription(false, model));
    }

    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            String label,
            HeartbeatSkillPolicy.State state) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                label,
                "doctrine",
                "fixture:collapsed-owner-speech-load",
                "Broad collapsed-owner speech-load fixture is material.",
                state,
                true,
                "Fixture changed the broad collapsed-owner consequence.",
                "Fixture evidence remains source-only until the runner executes.");
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder(value.length() * count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
