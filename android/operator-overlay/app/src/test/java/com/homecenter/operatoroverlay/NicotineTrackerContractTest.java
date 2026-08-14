package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

import org.junit.Test;

public class NicotineTrackerContractTest {
    @Test
    public void exactGrammarAcceptsOnlyFourEventKinds() {
        for (String value : new String[]{
                "none", "mild", "moderate", "strong", "overwhelming"}) {
            assertValid("/track hunger " + value, NicotineTrackerContract.Kind.HUNGER, value);
        }
        for (String value : new String[]{
                "unknown", "empty", "low", "about-half", "high"}) {
            assertValid("/track tank " + value, NicotineTrackerContract.Kind.TANK, value);
        }
        for (int value = 0; value <= 100; value++) {
            assertValid("/track puffs " + value,
                    NicotineTrackerContract.Kind.PUFFS, Integer.toString(value));
        }
        for (String value : new String[]{
                "mouth", "swallowed", "skin", "eye", "unknown"}) {
            assertValid("/track exposure " + value,
                    NicotineTrackerContract.Kind.EXPOSURE, value);
        }
    }

    @Test
    public void rejectMatrixStaysUnsavedAndNeverBecomesOrdinaryText() {
        String[] rejected = new String[]{
                "/track",
                "/track hunger",
                "/track hunger severe",
                "/track hunger strong note",
                "/track tank half",
                "/track tank about half",
                "/track puffs -1",
                "/track puffs 101",
                "/track puffs 1.5",
                "/track puffs 00",
                "/track puffs 01",
                "/track puffs ten",
                "/track exposure lungs",
                "/track exposure eye note",
                "/TRACK hunger strong",
                " /track hunger strong",
                "/track  hunger strong",
                "/track hunger  strong",
                "/track hunger strong ",
                "track hunger strong",
                "hunger: strong",
                "tank low",
                "puff 4",
                "exposure unknown"
        };
        for (String value : rejected) {
            NicotineTrackerContract.ParseResult result = NicotineTrackerContract.parse(value);
            assertEquals(value, NicotineTrackerContract.State.UNSAVED_LOCAL_DRAFT, result.state);
            assertNull(value, result.draft);
        }
    }

    @Test
    public void unrelatedLanguageRemainsAvailableToTheExistingBeardRouter() {
        for (String value : new String[]{
                "How does this work?",
                "Keep working on the game",
                "Play music for dinner",
                "Recent text messages"
        }) {
            assertEquals(
                    value,
                    NicotineTrackerContract.State.NOT_TRACKER,
                    NicotineTrackerContract.parse(value).state);
        }
    }

    @Test
    public void exposureNeverCollapsesIntoAnotherKind() {
        NicotineTrackerContract.ParseResult result =
                NicotineTrackerContract.parse("/track exposure mouth");
        assertEquals(NicotineTrackerContract.Kind.EXPOSURE, result.draft.kind);
    }

    private static void assertValid(
            String command, NicotineTrackerContract.Kind kind, String value) {
        NicotineTrackerContract.ParseResult result = NicotineTrackerContract.parse(command);
        assertEquals(command, NicotineTrackerContract.State.VALID, result.state);
        assertNotNull(command, result.draft);
        assertEquals(command, kind, result.draft.kind);
        assertEquals(command, value, result.draft.value);
    }
}
