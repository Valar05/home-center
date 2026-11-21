package com.homecenter.ritsucontrol;

import static org.junit.Assert.assertEquals;
import org.junit.Test;

public final class ListeningPolicyTest {
    @Test public void captureMustBeConfirmedBeforeListeningIsShown() {
        assertEquals(ListeningPolicy.Mode.LISTENING,
            ListeningPolicy.next(ListeningPolicy.Mode.OFF, ListeningPolicy.Event.CAPTURE_STARTED));
    }
    @Test public void mutingRequiresActualReleaseAndResumeRequiresCapture() {
        assertEquals(ListeningPolicy.Mode.MUTED,
            ListeningPolicy.next(ListeningPolicy.Mode.LISTENING, ListeningPolicy.Event.MUTED_RELEASED));
        assertEquals(ListeningPolicy.Mode.LISTENING,
            ListeningPolicy.next(ListeningPolicy.Mode.MUTED, ListeningPolicy.Event.RESUMED_CAPTURE));
    }
    @Test public void handoffToAndroidRecognizerDoesNotPretendAudioRecordIsRunning() {
        assertEquals(ListeningPolicy.Mode.RECOGNIZING,
            ListeningPolicy.next(ListeningPolicy.Mode.LISTENING,
                ListeningPolicy.Event.RECOGNITION_STARTED));
        assertEquals(ListeningPolicy.Mode.MUTED,
            ListeningPolicy.next(ListeningPolicy.Mode.RECOGNIZING,
                ListeningPolicy.Event.RECOGNITION_FINISHED));
        assertEquals(ListeningPolicy.Mode.LISTENING,
            ListeningPolicy.next(ListeningPolicy.Mode.MUTED,
                ListeningPolicy.Event.RESUMED_CAPTURE));
    }
    @Test(expected=IllegalStateException.class)
    public void neverStartRecognitionFromIdleOrMuted() {
        ListeningPolicy.next(ListeningPolicy.Mode.MUTED,
            ListeningPolicy.Event.RECOGNITION_STARTED);
    }
    @Test(expected=IllegalStateException.class)
    public void neverFinishRecognitionTwice() {
        ListeningPolicy.next(ListeningPolicy.Mode.MUTED,
            ListeningPolicy.Event.RECOGNITION_FINISHED);
    }
    @Test public void liveRecognizerOwnsMicrophoneDirectly() {
        assertEquals(ListeningPolicy.Mode.RECOGNIZING,
            ListeningPolicy.next(ListeningPolicy.Mode.OFF, ListeningPolicy.Event.PROVIDER_STARTED));
        assertEquals(ListeningPolicy.Mode.MUTED,
            ListeningPolicy.next(ListeningPolicy.Mode.RECOGNIZING,
                    ListeningPolicy.Event.RECOGNITION_FINISHED));
        assertEquals(ListeningPolicy.Mode.RECOGNIZING,
            ListeningPolicy.next(ListeningPolicy.Mode.MUTED, ListeningPolicy.Event.PROVIDER_STARTED));
    }
    @Test(expected=IllegalStateException.class)
    public void providerCannotBeRestartedWithoutStoppingPriorSession() {
        ListeningPolicy.next(ListeningPolicy.Mode.RECOGNIZING,
                ListeningPolicy.Event.PROVIDER_STARTED);
    }
    @Test public void stopAlwaysFailsClosed() {
        for (ListeningPolicy.Mode mode : ListeningPolicy.Mode.values()) {
            assertEquals(ListeningPolicy.Mode.OFF,
                ListeningPolicy.next(mode, ListeningPolicy.Event.STOPPED));
        }
    }
    @Test public void failureNeverClaimsListening() {
        assertEquals(ListeningPolicy.Mode.ERROR,
            ListeningPolicy.next(ListeningPolicy.Mode.LISTENING, ListeningPolicy.Event.FAILED));
    }
    @Test(expected=IllegalStateException.class)
    public void repeatedResumeWithoutMuteIsRejected() {
        ListeningPolicy.next(ListeningPolicy.Mode.LISTENING,
            ListeningPolicy.Event.RESUMED_CAPTURE);
    }
    @Test(expected=IllegalStateException.class)
    public void muteWithoutCaptureIsRejected() {
        ListeningPolicy.next(ListeningPolicy.Mode.OFF, ListeningPolicy.Event.MUTED_RELEASED);
    }
}
