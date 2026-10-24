package com.homecenter.ritsucontrol;

/**
 * Pure deterministic control gate for interrupting Ritsu's spoken reply.
 *
 * This is deliberately NOT an acoustic echo canceller, voice recognizer,
 * phone-audio transport, or a guarantee of full-duplex capture.
 *
 * The audio front-end must attest NEAR_END_VERIFIED using an echo-resistant
 * near-end detector. Raw energy/VAD or a matching transcript MUST NOT call it.
 * Manual INTERRUPT_BUTTON requires no acoustic evidence.
 *
 * A STOP_PENDING state cannot be mistaken for stopped playback, and
 * completed/failed acknowledgments must match the active reply identity.
 */
final class BargeInPolicy {
    enum State { IDLE, PLAYING, STOP_PENDING, INTERRUPTED, UNCERTAIN }
    enum Trigger { VERIFIED_NEAR_END, INTERRUPT_BUTTON }

    private State state = State.IDLE;
    private String replyId = "";
    private long attempt;
    private Trigger trigger;

    State state() { return state; }
    String replyId() { return replyId; }
    long attempt() { return attempt; }
    Trigger trigger() { return trigger; }
    boolean canAcceptNextUserTurn() { return state == State.IDLE || state == State.INTERRUPTED; }
    boolean shouldStopPlayback() { return state == State.STOP_PENDING; }

    void beginPlayback(String id) {
        if (id == null || !id.matches("[A-Za-z0-9_.:-]{8,100}"))
            throw new IllegalArgumentException("stable reply ID required");
        if (state != State.IDLE && state != State.INTERRUPTED)
            throw new IllegalStateException("cannot overlap replies or lose stop outcome");
        replyId = id;
        trigger = null;
        ++attempt;
        state = State.PLAYING;
    }

    /** Raw VAD cannot distinguish TTS leaking from speakers. */
    void onRawVoiceActivity() {
        // Intentional no-op. Acoustic validation is an independent gate.
    }

    /** An acoustic front-end must *prove* near-end speech before calling. */
    boolean onVerifiedNearEndSpeech(String forReplyId) {
        if (!replyId.equals(forReplyId) || state != State.PLAYING) return false;
        trigger = Trigger.VERIFIED_NEAR_END;
        state = State.STOP_PENDING;
        return true;
    }

    boolean interruptButton(String forReplyId) {
        if (!replyId.equals(forReplyId) || state != State.PLAYING) return false;
        trigger = Trigger.INTERRUPT_BUTTON;
        state = State.STOP_PENDING;
        return true;
    }

    boolean confirmPlaybackStopped(String forReplyId, long forAttempt) {
        if (!replyId.equals(forReplyId) || attempt != forAttempt ||
                state != State.STOP_PENDING) return false;
        state = State.INTERRUPTED;
        return true;
    }

    boolean playbackStopFailed(String forReplyId, long forAttempt) {
        if (!replyId.equals(forReplyId) || attempt != forAttempt ||
                state != State.STOP_PENDING) return false;
        state = State.UNCERTAIN; // Never claim a successful interrupt.
        return true;
    }

    boolean playbackNaturallyFinished(String forReplyId, long forAttempt) {
        if (!replyId.equals(forReplyId) || attempt != forAttempt ||
                state != State.PLAYING) return false;
        state = State.IDLE;
        replyId = "";
        trigger = null;
        return true;
    }

    void resetAfterObservedStop() {
        if (state != State.INTERRUPTED && state != State.UNCERTAIN)
            throw new IllegalStateException("reset requires an observed or reconciled stop");
        state = State.IDLE;
        replyId = "";
        trigger = null;
    }
}
