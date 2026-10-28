package com.homecenter.ritsucontrol;

/**
 * Aggregates multiple provider-finalized speech fragments into one user turn.
 *
 * A recognizer's onResults() is NOT the same as "send message". The human may
 * pause to think. Only prolonged inactivity after a finalized phrase allows
 * a local outbox commit, and any new speech cancels the countdown.
 *
 * Pure state, no Android dependencies. All calls serialized on service main.
 * Times use elapsed realtime milliseconds, never wall clock.
 */
final class SpokenTurnBuffer {
    static final int DEFAULT_PAUSE_MS = 5000;
    static final int MIN_PAUSE_MS = 1500;
    static final int MAX_PAUSE_MS = 6500;
    static final int MAX_CHARS = 5000;
    private final StringBuilder text = new StringBuilder();
    private int pauseMs;
    private long dueAtMs = -1;
    private boolean inSpeech;

    SpokenTurnBuffer(int pauseMs) { setPauseMs(pauseMs); }

    int pauseMs() { return pauseMs; }
    void setPauseMs(int value) {
        if (value < MIN_PAUSE_MS || value > MAX_PAUSE_MS)
            throw new IllegalArgumentException("pause threshold outside safe range");
        pauseMs = value;
    }

    boolean hasText() { return text.length() != 0; }
    String preview() { return text.toString(); }
    boolean isInSpeech() { return inSpeech; }

    /** Recognition of another phrase has begun: a thinking pause was not a
     * completed message. Never submit the old fragment during speech. */
    void speechStarted() {
        inSpeech = true;
        dueAtMs = -1;
    }

    void speechEnded(long nowMs) {
        inSpeech = false;
        if (hasText()) dueAtMs = nowMs + pauseMs;
    }

    boolean wouldOverflow(String newFragment) {
        String fragment = newFragment == null ? "" : newFragment.trim();
        return !fragment.isEmpty() && hasText()
                && text.length() + 1 + fragment.length() > MAX_CHARS;
    }

    /** A complete Android recognition result, not an interim transcript. */
    void appendFinal(String fragment, long nowMs) {
        String part = fragment == null ? "" : fragment.trim();
        if (part.isEmpty()) return;
        if (part.length() > MAX_CHARS || wouldOverflow(part))
            throw new IllegalArgumentException("speech fragment exceeds turn boundary");
        if (hasText()) text.append(' ');
        text.append(part);
        inSpeech = false;
        dueAtMs = nowMs + pauseMs;
    }

    boolean ready(long nowMs) {
        return hasText() && !inSpeech && dueAtMs >= 0 && nowMs >= dueAtMs;
    }

    long remainingMs(long nowMs) {
        if (!hasText() || inSpeech || dueAtMs < 0) return -1;
        return Math.max(0, dueAtMs - nowMs);
    }

    /** Explicit user mute/stop is an intentional boundary. */
    String flush() {
        String result = text.toString();
        clear();
        return result;
    }

    void clear() {
        text.setLength(0);
        dueAtMs = -1;
        inSpeech = false;
    }
}
