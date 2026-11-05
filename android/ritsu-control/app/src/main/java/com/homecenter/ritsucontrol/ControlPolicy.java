package com.homecenter.ritsucontrol;

/** Pure state machine; these are control REQUESTS, not a claim of active audio. */
final class ControlPolicy {
    static final int ACTION_START = 0;
    static final int ACTION_MIC_REQUEST = 1;
    static final int ACTION_SPEAKER_PREFERENCE = 2;
    static final int ACTION_STOP = 3;

    static final class State {
        final boolean microphoneRequested;
        final boolean speakerMuted;
        State(boolean microphoneRequested, boolean speakerMuted) {
            this.microphoneRequested = microphoneRequested;
            this.speakerMuted = speakerMuted;
        }
    }

    static State transition(State prior, int action) {
        switch (action) {
            case ACTION_START:
                // Never silently resume a microphone request after process restart.
                return new State(false, prior.speakerMuted);
            case ACTION_MIC_REQUEST:
                return new State(!prior.microphoneRequested, prior.speakerMuted);
            case ACTION_SPEAKER_PREFERENCE:
                return new State(prior.microphoneRequested, !prior.speakerMuted);
            case ACTION_STOP:
                return new State(false, prior.speakerMuted);
            default:
                throw new IllegalArgumentException("Unsupported Ritsu control action");
        }
    }
    private ControlPolicy() {}
}
