package com.homecenter.ritsucontrol;

import static org.junit.Assert.*;
import org.junit.Test;

public final class BargeInPolicyTest {
    @Test public void ritsuPlaybackSoundCannotInterruptHerself() {
        BargeInPolicy gate = new BargeInPolicy();
        gate.beginPlayback("reply-ritsu-0001");
        for (int i = 0; i < 500; i++) gate.onRawVoiceActivity();
        assertEquals(BargeInPolicy.State.PLAYING, gate.state());
        assertFalse(gate.shouldStopPlayback());
    }
    @Test public void verifiedNearEndVoiceRequestsStopWithoutClaimingItHappened() {
        BargeInPolicy gate = new BargeInPolicy();
        gate.beginPlayback("reply-ritsu-0001");
        assertTrue(gate.onVerifiedNearEndSpeech("reply-ritsu-0001"));
        assertEquals(BargeInPolicy.Trigger.VERIFIED_NEAR_END, gate.trigger());
        assertEquals(BargeInPolicy.State.STOP_PENDING, gate.state());
        assertTrue(gate.shouldStopPlayback());
        assertFalse(gate.canAcceptNextUserTurn());
        assertTrue(gate.confirmPlaybackStopped("reply-ritsu-0001", gate.attempt()));
        assertEquals(BargeInPolicy.State.INTERRUPTED, gate.state());
        assertTrue(gate.canAcceptNextUserTurn());
    }
    @Test public void manualBargeInWorksWithoutAcousticProof() {
        BargeInPolicy gate = new BargeInPolicy();
        gate.beginPlayback("reply-ritsu-0001");
        assertTrue(gate.interruptButton("reply-ritsu-0001"));
        assertEquals(BargeInPolicy.Trigger.INTERRUPT_BUTTON, gate.trigger());
        assertTrue(gate.confirmPlaybackStopped("reply-ritsu-0001", gate.attempt()));
    }
    @Test public void staleStopAcksAndEchoCannotAffectNextReply() {
        BargeInPolicy gate = new BargeInPolicy();
        gate.beginPlayback("reply-ritsu-0001");
        long olderAttempt = gate.attempt();
        assertTrue(gate.playbackNaturallyFinished("reply-ritsu-0001", olderAttempt));
        gate.beginPlayback("reply-ritsu-0002");
        assertFalse(gate.interruptButton("reply-ritsu-0001"));
        assertFalse(gate.onVerifiedNearEndSpeech("reply-ritsu-0001"));
        assertFalse(gate.confirmPlaybackStopped("reply-ritsu-0001", olderAttempt));
        assertEquals(BargeInPolicy.State.PLAYING, gate.state());
    }
    @Test public void timeoutIsUncertainRatherThanClaimingInterrupted() {
        BargeInPolicy gate = new BargeInPolicy();
        gate.beginPlayback("reply-ritsu-0001");
        gate.interruptButton("reply-ritsu-0001");
        assertTrue(gate.playbackStopFailed("reply-ritsu-0001", gate.attempt()));
        assertEquals(BargeInPolicy.State.UNCERTAIN, gate.state());
        assertFalse(gate.canAcceptNextUserTurn());
        assertFalse(gate.shouldStopPlayback());
        gate.resetAfterObservedStop();
        assertEquals(BargeInPolicy.State.IDLE, gate.state());
    }
    @Test(expected=IllegalStateException.class)
    public void cannotStartReplyWhileStopIsPending() {
        BargeInPolicy gate = new BargeInPolicy();
        gate.beginPlayback("reply-ritsu-0001");
        gate.interruptButton("reply-ritsu-0001");
        gate.beginPlayback("reply-ritsu-0002");
    }
}
