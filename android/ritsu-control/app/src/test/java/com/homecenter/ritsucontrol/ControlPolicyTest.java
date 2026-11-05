package com.homecenter.ritsucontrol;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import org.junit.Test;

public final class ControlPolicyTest {
    @Test public void microphoneAndSpeakerRequestsAreIndependent() {
        ControlPolicy.State first = new ControlPolicy.State(false, false);
        ControlPolicy.State mic = ControlPolicy.transition(first, ControlPolicy.ACTION_MIC_REQUEST);
        assertTrue(mic.microphoneRequested);
        assertFalse(mic.speakerMuted);
        ControlPolicy.State muted = ControlPolicy.transition(mic, ControlPolicy.ACTION_SPEAKER_PREFERENCE);
        assertTrue(muted.microphoneRequested);
        assertTrue(muted.speakerMuted);
        ControlPolicy.State micOff = ControlPolicy.transition(muted, ControlPolicy.ACTION_MIC_REQUEST);
        assertFalse(micOff.microphoneRequested);
        assertTrue(micOff.speakerMuted);
    }

    @Test public void sessionRestartFailsClosedForMicrophone() {
        ControlPolicy.State previous = new ControlPolicy.State(true, true);
        ControlPolicy.State restarted = ControlPolicy.transition(previous, ControlPolicy.ACTION_START);
        assertFalse(restarted.microphoneRequested);
        assertTrue(restarted.speakerMuted);
    }

    @Test public void stopDisablesMicRequestWithoutUnmutingOutput() {
        ControlPolicy.State stopped = ControlPolicy.transition(
                new ControlPolicy.State(true, true), ControlPolicy.ACTION_STOP);
        assertFalse(stopped.microphoneRequested);
        assertTrue(stopped.speakerMuted);
    }

    @Test(expected = IllegalArgumentException.class)
    public void unknownActionsAreRejected() {
        ControlPolicy.transition(new ControlPolicy.State(false, false), 999);
    }
}
