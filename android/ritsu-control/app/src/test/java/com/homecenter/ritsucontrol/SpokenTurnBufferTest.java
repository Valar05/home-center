package com.homecenter.ritsucontrol;

import static org.junit.Assert.*;
import org.junit.Test;

public final class SpokenTurnBufferTest {
    @Test public void aThinkingPauseDoesNotProduceTwoMessages() {
        SpokenTurnBuffer buffer = new SpokenTurnBuffer(3200);
        buffer.appendFinal("I think", 1000);
        assertFalse(buffer.ready(2900));
        buffer.speechStarted(); // User continues the thought before threshold.
        assertFalse(buffer.ready(5000));
        buffer.speechEnded(5200);
        buffer.appendFinal("what I want is a longer pause", 5800);
        assertFalse(buffer.ready(8999));
        assertTrue(buffer.ready(9000));
        assertEquals("I think what I want is a longer pause", buffer.flush());
        assertFalse(buffer.hasText());
    }

    @Test public void providerFinalIsNotImmediateSubmission() {
        SpokenTurnBuffer buffer = new SpokenTurnBuffer(3200);
        buffer.appendFinal("Ritsu darling", 100);
        assertFalse(buffer.ready(3299));
        assertTrue(buffer.ready(3300));
    }

    @Test public void speechBeginningCancelsPendingCommit() {
        SpokenTurnBuffer buffer = new SpokenTurnBuffer(3200);
        buffer.appendFinal("Wait", 1000);
        buffer.speechStarted();
        assertEquals(-1, buffer.remainingMs(9000));
        assertFalse(buffer.ready(9000));
    }

    @Test public void deliberateMuteCanFlushRecognizedWords() {
        SpokenTurnBuffer buffer = new SpokenTurnBuffer(5000);
        buffer.appendFinal("Can you hear me", 100);
        assertEquals("Can you hear me", buffer.flush());
        assertEquals("", buffer.preview());
    }

    @Test public void adjustingPreferenceDoesNotSilentlySubmit() {
        SpokenTurnBuffer buffer = new SpokenTurnBuffer(2000);
        buffer.appendFinal("I am thinking", 1000);
        buffer.setPauseMs(5000);
        buffer.speechEnded(2500);
        assertFalse(buffer.ready(7499));
        assertTrue(buffer.ready(7500));
    }

    @Test public void phraseBufferAcceptsFiveThousandCharactersExactly() {
        SpokenTurnBuffer buffer = new SpokenTurnBuffer(3200);
        StringBuilder b = new StringBuilder();
        for (int i=0;i<SpokenTurnBuffer.MAX_CHARS;i++) b.append('x');
        buffer.appendFinal(b.toString(), 500);
        assertEquals(SpokenTurnBuffer.MAX_CHARS, buffer.flush().length());
    }

    @Test(expected=IllegalArgumentException.class)
    public void rejectsMoreThanMaximumTurnLength() {
        SpokenTurnBuffer buffer = new SpokenTurnBuffer(3200);
        StringBuilder b = new StringBuilder();
        for (int i=0;i<SpokenTurnBuffer.MAX_CHARS+1;i++) b.append('x');
        buffer.appendFinal(b.toString(), 500);
    }

    @Test(expected=IllegalArgumentException.class)
    public void rejectsAccidentalZeroSecondPause() {
        new SpokenTurnBuffer(0);
    }
}
