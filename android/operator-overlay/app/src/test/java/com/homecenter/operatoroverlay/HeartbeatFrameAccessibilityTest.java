package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import org.junit.Test;

public class HeartbeatFrameAccessibilityTest {
    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            String consequence,
            String evidence) {
        return typed(
                id,
                "Contact Preservation",
                HeartbeatSkillPolicy.State.ACTIVE,
                consequence,
                evidence);
    }

    private static HeartbeatSkillPolicy.Candidate typed(
            String id,
            String label,
            HeartbeatSkillPolicy.State state,
            String consequence,
            String evidence) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                label,
                "doctrine",
                "Contact Preservation",
                "Preserve last-good heartbeat through refresh failure",
                state,
                state == HeartbeatSkillPolicy.State.ACTIVE
                        || state == HeartbeatSkillPolicy.State.RECOVERED,
                consequence,
                evidence);
    }

    @Test
    public void collapsedDescriptionComesFromVisibleSceneNodesWithoutReadingVerboseDetail() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed(
                        "contact",
                        "Last-good contact remains readable",
                        "Exact source fixture")),
                true,
                null);

        String description = HeartbeatFrameAccessibility.collapsedContentDescription(frame);
        assertTrue(description.contains("1 material skill light"));
        assertTrue(description.contains("States: active 1, blocked 0, fault 0, recovered 0"));
        assertTrue(description.contains("Contact Preservation, active"));
        assertFalse(description.contains("Last-good contact remains readable"));
    }

    @Test
    public void interruptedRefreshAnnouncesBoundaryWithoutDiscardedAttemptContent() {
        HeartbeatSceneGraph.Frame complete = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed(
                        "contact",
                        "Visible consequence",
                        "evidence-a")),
                true,
                null);
        HeartbeatSceneGraph.Frame interrupted = HeartbeatSceneGraph.build(
                "pulse-b",
                Collections.singletonList(typed(
                        "contact",
                        "Discarded attempted consequence",
                        "evidence-b")),
                false,
                complete);

        String description = HeartbeatFrameAccessibility.collapsedContentDescription(interrupted);
        assertTrue(description.contains("Contact Preservation, active"));
        assertTrue(description.contains("Heartbeat refresh interrupted"));
        assertTrue(description.contains("Showing last complete heartbeat pulse-a"));
        assertFalse(description.contains("Discarded attempted consequence"));
        assertFalse(description.contains("Visible consequence"));
    }

    @Test
    public void collapsedDescriptionBoundsBroadConstellationWithoutHidingStateTotals() {
        List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
        String hugeConsequence = repeat("long consequence ", 100);
        String longLabel = repeat("Label", 32);
        String compactPrefix = longLabel.substring(
                0,
                HeartbeatFrameAccessibility.MAX_COLLAPSED_LABEL_CODE_POINTS - 1) + "…";
        for (int index = 0; index < 20; index++) {
            HeartbeatSkillPolicy.State state;
            switch (index % 4) {
                case 1:
                    state = HeartbeatSkillPolicy.State.BLOCKED;
                    break;
                case 2:
                    state = HeartbeatSkillPolicy.State.FAULT;
                    break;
                case 3:
                    state = HeartbeatSkillPolicy.State.RECOVERED;
                    break;
                case 0:
                default:
                    state = HeartbeatSkillPolicy.State.ACTIVE;
                    break;
            }
            candidates.add(typed(
                    "light-" + index,
                    longLabel,
                    state,
                    hugeConsequence + index,
                    "evidence-" + index));
        }

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-broad",
                candidates,
                true,
                null);
        String description = HeartbeatFrameAccessibility.collapsedContentDescription(frame);

        assertTrue(description.contains("20 material skill lights"));
        assertTrue(description.contains("States: active 5, blocked 5, fault 5, recovered 5"));
        assertTrue(description.contains(compactPrefix + ", blocked"));
        assertTrue(description.contains(compactPrefix + ", fault"));
        assertTrue(description.contains("8 more material lights are available by touch"));
        assertFalse(description.contains("additional blocked or fault attention lights"));
        assertFalse(description.contains("long consequence"));
        assertFalse(description.contains(longLabel + ", active"));
        assertTrue(description.length() < 2048);
    }

    @Test
    public void attentionStatesAreNamedBeforeEarlierActiveLightsWithoutChangingFocusOrder() {
        List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
        for (int index = 0; index < 14; index++) {
            candidates.add(typed(
                    "active-" + index,
                    "Active " + index,
                    HeartbeatSkillPolicy.State.ACTIVE,
                    "Active source change " + index,
                    "active-evidence-" + index));
        }
        candidates.add(typed(
                "late-fault",
                "Late Fault",
                HeartbeatSkillPolicy.State.FAULT,
                "A serious boundary must not be buried by speech order",
                "fault-evidence"));

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-attention",
                candidates,
                true,
                null);
        String description = HeartbeatFrameAccessibility.collapsedContentDescription(frame);

        assertTrue(description.contains("States: active 14, blocked 0, fault 1, recovered 0"));
        assertTrue(description.contains("Late Fault, fault"));
        assertTrue(description.indexOf("Late Fault, fault") < description.indexOf("Active 0, active"));
        assertTrue(description.contains("3 more material lights are available by touch"));
        assertFalse(description.contains("additional blocked or fault attention light"));
        assertEquals(14, HeartbeatFrameAccessibility.focusIndexForId(frame, "late-fault"));
    }

    @Test
    public void attentionOverflowReportsExactOmittedUrgentCount() {
        List<HeartbeatSkillPolicy.Candidate> candidates = new ArrayList<>();
        for (int index = 0; index < 14; index++) {
            candidates.add(typed(
                    "attention-" + index,
                    "Attention " + index,
                    index % 2 == 0
                            ? HeartbeatSkillPolicy.State.FAULT
                            : HeartbeatSkillPolicy.State.BLOCKED,
                    "Urgent boundary " + index,
                    "attention-evidence-" + index));
        }
        candidates.add(typed(
                "active-tail",
                "Active Tail",
                HeartbeatSkillPolicy.State.ACTIVE,
                "A non-attention change follows the urgent queue",
                "active-tail-evidence"));

        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-attention-overflow",
                candidates,
                true,
                null);
        String description = HeartbeatFrameAccessibility.collapsedContentDescription(frame);

        assertTrue(description.contains("States: active 1, blocked 7, fault 7, recovered 0"));
        assertTrue(description.contains("3 more material lights are available by touch"));
        assertTrue(description.contains(
                "2 of those are additional blocked or fault attention lights"));
        assertFalse(description.contains("Attention 12, fault"));
        assertFalse(description.contains("Attention 13, blocked"));
        assertTrue(description.length() < 2048);
    }

    @Test
    public void attentionFirstSummaryPreservesVisibleOrderWithinAttentionGroup() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-attention-order",
                Arrays.asList(
                        typed(
                                "active-first",
                                "Active First",
                                HeartbeatSkillPolicy.State.ACTIVE,
                                "Active change",
                                "active-evidence"),
                        typed(
                                "blocked-first",
                                "Blocked First",
                                HeartbeatSkillPolicy.State.BLOCKED,
                                "Blocked boundary",
                                "blocked-evidence"),
                        typed(
                                "fault-second",
                                "Fault Second",
                                HeartbeatSkillPolicy.State.FAULT,
                                "Fault boundary",
                                "fault-evidence")),
                true,
                null);

        String description = HeartbeatFrameAccessibility.collapsedContentDescription(frame);
        assertTrue(description.indexOf("Blocked First, blocked")
                < description.indexOf("Fault Second, fault"));
        assertTrue(description.indexOf("Fault Second, fault")
                < description.indexOf("Active First, active"));
        assertEquals(0, HeartbeatFrameAccessibility.focusIndexForId(frame, "active-first"));
        assertEquals(1, HeartbeatFrameAccessibility.focusIndexForId(frame, "blocked-first"));
        assertEquals(2, HeartbeatFrameAccessibility.focusIndexForId(frame, "fault-second"));
    }

    @Test
    public void collapsedLabelHardBudgetDoesNotSplitUnicodeCodePoint() {
        String emoji = "🦢";
        String longLabel = repeat(emoji, 70);
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-unicode",
                Collections.singletonList(typed(
                        "swan",
                        longLabel,
                        HeartbeatSkillPolicy.State.ACTIVE,
                        "Unicode remains inert semantic data",
                        "unicode-fixture")),
                true,
                null);

        String description = HeartbeatFrameAccessibility.collapsedContentDescription(frame);
        assertTrue(description.contains(
                repeat(emoji, HeartbeatFrameAccessibility.MAX_COLLAPSED_LABEL_CODE_POINTS - 1)
                        + "…, active"));
        assertFalse(description.contains(
                repeat(emoji, HeartbeatFrameAccessibility.MAX_COLLAPSED_LABEL_CODE_POINTS)));
    }

    @Test
    public void detailLookupUsesCurrentVisibleFocusIndexOnly() {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "pulse-a",
                Collections.singletonList(typed(
                        "contact",
                        "Visible consequence",
                        "evidence-a")),
                true,
                null);

        String detail = HeartbeatFrameAccessibility.detailContentDescription(frame, 0);
        assertTrue(detail.contains("Why: Preserve last-good heartbeat through refresh failure"));
        assertTrue(detail.contains("Evidence: evidence-a"));
        assertTrue(HeartbeatFrameAccessibility.detailContentDescription(frame, 99).isEmpty());
    }

    @Test
    public void stableIdLookupSurvivesSceneReorderWithoutIndexConfusion() {
        HeartbeatSkillPolicy.Candidate contact = typed(
                "contact",
                "Contact Preservation",
                HeartbeatSkillPolicy.State.ACTIVE,
                "Contact remains exact",
                "contact-evidence");
        HeartbeatSkillPolicy.Candidate regnet = typed(
                "regnet",
                "Regnet QA",
                HeartbeatSkillPolicy.State.BLOCKED,
                "TESTED remains unresolved",
                "actions-budget-boundary");

        HeartbeatSceneGraph.Frame first = HeartbeatSceneGraph.build(
                "pulse-first",
                Arrays.asList(contact, regnet),
                true,
                null);
        HeartbeatSceneGraph.Frame reordered = HeartbeatSceneGraph.build(
                "pulse-reordered",
                Arrays.asList(regnet, contact),
                true,
                first);

        assertEquals(0, HeartbeatFrameAccessibility.focusIndexForId(first, "contact"));
        assertEquals(1, HeartbeatFrameAccessibility.focusIndexForId(reordered, "CONTACT"));
        String detail = HeartbeatFrameAccessibility.detailContentDescription(reordered, "contact");
        assertTrue(detail.contains("Skill Contact Preservation, active"));
        assertTrue(detail.contains("Evidence: contact-evidence"));
        assertFalse(detail.contains("TESTED remains unresolved"));
        assertEquals(-1, HeartbeatFrameAccessibility.focusIndexForId(reordered, "missing"));
        assertTrue(HeartbeatFrameAccessibility.detailContentDescription(reordered, "missing").isEmpty());
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
