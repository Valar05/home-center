package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

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

    @Test
    public void sharedAdversarialCorpusNeverFallsThrough() throws Exception {
        InputStream stream = getClass().getResourceAsStream(
                "/nicotine_tracker_adversarial_vectors.tsv");
        assertNotNull("shared adversarial vector corpus missing", stream);
        int rows = 0;
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            for (String line; (line = reader.readLine()) != null;) {
                if (line.isEmpty() || line.startsWith("#")) continue;
                String[] fields = line.split("\\t", -1);
                assertEquals("invalid shared corpus row: " + line, 3, fields.length);
                String text = decodeEscapes(fields[1]);
                NicotineTrackerContract.ParseResult result =
                        NicotineTrackerContract.parse(text);
                if ("QUARANTINE".equals(fields[0])) {
                    assertEquals(
                            text,
                            true,
                            result.state != NicotineTrackerContract.State.NOT_TRACKER);
                } else if ("ORDINARY".equals(fields[0])) {
                    assertEquals(
                            text,
                            NicotineTrackerContract.State.NOT_TRACKER,
                            result.state);
                } else {
                    throw new AssertionError("unknown corpus expectation: " + fields[0]);
                }
                rows++;
            }
        }
        assertEquals(33, rows);
    }

    private static String decodeEscapes(String value) {
        StringBuilder decoded = new StringBuilder(value.length());
        for (int index = 0; index < value.length();) {
            if (index + 9 < value.length()
                    && value.charAt(index) == '\\'
                    && value.charAt(index + 1) == 'U') {
                decoded.appendCodePoint(Integer.parseInt(
                        value.substring(index + 2, index + 10), 16));
                index += 10;
            } else if (index + 5 < value.length()
                    && value.charAt(index) == '\\'
                    && value.charAt(index + 1) == 'u') {
                decoded.append((char) Integer.parseInt(
                        value.substring(index + 2, index + 6), 16));
                index += 6;
            } else {
                decoded.append(value.charAt(index++));
            }
        }
        return decoded.toString();
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
