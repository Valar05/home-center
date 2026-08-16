package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

/**
 * Source-only regression fixtures for pending viewport restore lifecycle policy.
 * These tests do not prove Android layout timing, runtime viewport preservation,
 * TalkBack accessibility-focus behavior, deployment, or phone delivery.
 */
public class HeartbeatViewportRestorePolicyTest {
    private static HeartbeatSkillPolicy.Candidate typed(String id) {
        return new HeartbeatSkillPolicy.Candidate(
                id,
                id,
                "doctrine",
                "fixture:" + id,
                "Materially active in viewport restore fixture",
                HeartbeatSkillPolicy.State.ACTIVE,
                true,
                "Viewport contact matters",
                "Source-only fixture");
    }

    private static HeartbeatOverlayViewModel.Model model(String... ids) {
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(
                "restore-pulse",
                ids.length == 0
                        ? Collections.emptyList()
                        : Arrays.asList(Arrays.stream(ids)
                                .map(HeartbeatViewportRestorePolicyTest::typed)
                                .toArray(HeartbeatSkillPolicy.Candidate[]::new)),
                true,
                null);
        return HeartbeatOverlayViewModel.fromFrame(frame);
    }

    @Test
    public void selectedAnchorCanSurviveAChangedStructure() {
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        7L,
                        "KEEP",
                        "focused",
                        36,
                        model("new-before", "keep", "new-after"));

        assertTrue(ticket.hasAnchor());
        assertEquals("keep", ticket.semanticId);
        assertEquals(36, ticket.viewportOffsetPx);
        assertTrue(HeartbeatViewportRestorePolicy.shouldRestore(
                ticket,
                7L,
                model("new-before", "keep", "new-after")));
    }

    @Test
    public void keyboardFocusIsFallbackWhenSelectionDoesNotSurvive() {
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        8L,
                        "removed-selection",
                        "FOCUSED",
                        18,
                        model("focused", "other"));

        assertEquals("focused", ticket.semanticId);
        assertEquals(18, ticket.viewportOffsetPx);
    }

    @Test
    public void staleOrMissingSemanticAnchorProducesNoRestoreTicket() {
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        9L,
                        "removed-selection",
                        "removed-focus",
                        44,
                        model("other"));

        assertFalse(ticket.hasAnchor());
        assertFalse(HeartbeatViewportRestorePolicy.shouldRestore(ticket, 9L, model("other")));
    }

    @Test
    public void laterMutationInvalidatesOlderPendingRestore() {
        long first = HeartbeatViewportRestorePolicy.nextGeneration(10L);
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        first,
                        "keep",
                        "",
                        24,
                        model("keep", "other"));
        long later = HeartbeatViewportRestorePolicy.nextGeneration(first);

        assertTrue(HeartbeatViewportRestorePolicy.shouldRestore(ticket, first, model("keep", "other")));
        assertFalse(HeartbeatViewportRestorePolicy.shouldRestore(ticket, later, model("keep", "other")));
    }

    @Test
    public void removedAnchorCannotBeRestoredEvenWithCurrentGeneration() {
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        12L,
                        "keep",
                        "",
                        24,
                        model("keep", "other"));

        assertFalse(HeartbeatViewportRestorePolicy.shouldRestore(ticket, 12L, model("other")));
    }

    @Test
    public void keyboardFocusMoveSupersedesPendingRestoreWithoutGenerationChange() {
        HeartbeatOverlayViewModel.Model accepted = model("first", "second");
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        14L,
                        "",
                        "first",
                        20,
                        accepted);

        assertTrue(HeartbeatViewportRestorePolicy.shouldRestore(
                ticket,
                14L,
                accepted,
                "",
                "first"));
        assertFalse(HeartbeatViewportRestorePolicy.shouldRestore(
                ticket,
                14L,
                accepted,
                "",
                "second"));
    }

    @Test
    public void explicitSelectionSupersedesPendingKeyboardRestoreWithoutGenerationChange() {
        HeartbeatOverlayViewModel.Model accepted = model("first", "second");
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        15L,
                        "",
                        "first",
                        20,
                        accepted);

        assertFalse(HeartbeatViewportRestorePolicy.shouldRestore(
                ticket,
                15L,
                accepted,
                "second",
                "first"));
    }

    @Test
    public void durableSelectionRemainsOwnerWhenKeyboardFocusMoves() {
        HeartbeatOverlayViewModel.Model accepted = model("keep", "other");
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        16L,
                        "keep",
                        "other",
                        28,
                        accepted);

        assertTrue(HeartbeatViewportRestorePolicy.shouldRestore(
                ticket,
                16L,
                accepted,
                "keep",
                "other"));
    }

    @Test
    public void visibleViewportContactAcceptsWholeAndPartialIntersectionOnly() {
        assertTrue(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(120, 48, 100, 200));
        assertTrue(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(80, 48, 100, 200));
        assertTrue(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(280, 48, 100, 200));

        assertFalse(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(52, 48, 100, 200));
        assertFalse(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(300, 48, 100, 200));
        assertFalse(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(120, 0, 100, 200));
        assertFalse(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(120, 48, 100, 0));
    }

    @Test
    public void visibleViewportContactUsesLongGeometryAndClampsImpossibleNegativeScroll() {
        assertTrue(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(
                Integer.MAX_VALUE - 5,
                20,
                Integer.MAX_VALUE - 10,
                20));
        assertTrue(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(0, 48, -200, 48));
        assertFalse(HeartbeatViewportRestorePolicy.hasVisibleViewportContact(-80, 40, -200, 48));
    }

    @Test
    public void offscreenSelectionCannotSuppressVisibleKeyboardFallback() {
        HeartbeatOverlayViewModel.Model accepted = model("selected", "focused", "other");

        assertEquals("selected", HeartbeatViewportRestorePolicy.visibleViewportAnchorId(
                "selected",
                true,
                "focused",
                true,
                accepted));
        assertEquals("focused", HeartbeatViewportRestorePolicy.visibleViewportAnchorId(
                "selected",
                false,
                "focused",
                true,
                accepted));
        assertEquals("", HeartbeatViewportRestorePolicy.visibleViewportAnchorId(
                "selected",
                false,
                "focused",
                false,
                accepted));
    }

    @Test
    public void visibilityDoesNotResurrectSemanticIdsMissingFromAcceptedModel() {
        HeartbeatOverlayViewModel.Model accepted = model("other");

        assertEquals("", HeartbeatViewportRestorePolicy.visibleViewportAnchorId(
                "selected",
                true,
                "focused",
                true,
                accepted));
    }

    @Test
    public void boundedGeometryRemainsTheExistingAnchorPolicy() {
        HeartbeatViewportRestorePolicy.Ticket ticket =
                HeartbeatViewportRestorePolicy.capture(
                        13L,
                        "keep",
                        "",
                        36,
                        model("keep"));

        assertEquals(224, HeartbeatViewportRestorePolicy.targetScrollX(ticket, 260, 600));
        assertEquals(0, HeartbeatViewportRestorePolicy.targetScrollX(ticket, 20, 600));
        assertEquals(320, HeartbeatViewportRestorePolicy.targetScrollX(ticket, 900, 320));
    }

    @Test
    public void generationIsAnOrderingTokenNotWallClockEvidence() {
        assertEquals(43L, HeartbeatViewportRestorePolicy.nextGeneration(42L));
        assertEquals(Long.MIN_VALUE, HeartbeatViewportRestorePolicy.nextGeneration(Long.MAX_VALUE));
    }
}
