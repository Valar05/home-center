package com.homecenter.ritsucontrol;

/** Deterministic microphone lifecycle. "Listening" means AudioRecord is ACTIVE,
 * never "requested". All mutating operations are serialized on the service main thread. */
final class ListeningPolicy {
    enum Mode { OFF, LISTENING, MUTED, ERROR }
    enum Event { CAPTURE_STARTED, MUTED_RELEASED, RESUMED_CAPTURE, STOPPED, FAILED }
    static Mode next(Mode previous, Event event) {
        switch (event) {
            case CAPTURE_STARTED:
                if (previous != Mode.OFF && previous != Mode.ERROR)
                    throw new IllegalStateException("capture may start only from OFF or ERROR");
                return Mode.LISTENING;
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
