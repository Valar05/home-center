package com.homecenter.ritsucontrol;

/** Deterministic microphone lifecycle. "Listening" means AudioRecord is ACTIVE,
 * never "requested". All mutating operations are serialized on the service main thread. */
final class ListeningPolicy {
    enum Mode { OFF, LISTENING, RECOGNIZING, MUTED, ERROR }
    enum Event { CAPTURE_STARTED, RECOGNITION_STARTED, RECOGNITION_FINISHED, PROVIDER_STARTED, MUTED_RELEASED, RESUMED_CAPTURE, STOPPED, FAILED }
    static Mode next(Mode previous, Event event) {
        switch (event) {
            case CAPTURE_STARTED:
                if (previous != Mode.OFF && previous != Mode.ERROR)
                    throw new IllegalStateException("capture may start only from OFF or ERROR");
                return Mode.LISTENING;
            case PROVIDER_STARTED:
                if (previous != Mode.OFF && previous != Mode.MUTED && previous != Mode.ERROR)
                    throw new IllegalStateException("provider may start only from OFF, MUTED or ERROR");
                return Mode.RECOGNIZING;
            case RECOGNITION_STARTED:
                if (previous != Mode.LISTENING)
                    throw new IllegalStateException("recognition handoff requires active capture");
                return Mode.RECOGNIZING;
            case RECOGNITION_FINISHED:
                if (previous != Mode.RECOGNIZING)
                    throw new IllegalStateException("recognition must be pending");
                return Mode.MUTED;
            case MUTED_RELEASED:
                if (previous != Mode.LISTENING)
                    throw new IllegalStateException("mute requires an active capture");
                return Mode.MUTED;
            case RESUMED_CAPTURE:
                if (previous != Mode.MUTED)
                    throw new IllegalStateException("resume requires a muted session");
                return Mode.LISTENING;
            case STOPPED: return Mode.OFF;
            case FAILED: return Mode.ERROR;
            default: throw new IllegalArgumentException("unknown microphone event");
        }
    }
    private ListeningPolicy() {}
}
