package com.homecenter.operatoroverlay;

/**
 * Pure ordering/error policy for one ACTION_HEARTBEAT delivery.
 *
 * <p>The heartbeat-light envelope is optional telemetry layered on top of the
 * independent liveness heartbeat. A caller-invalid optional payload must not
 * suppress liveness or erase the previously durable payload. Internal/storage
 * failures are different: they are not swallowed or relabeled as a healthy
 * heartbeat.</p>
 *
 * <p>This class owns no Android receiver registration, storage, renderer,
 * transport, phone action, queue, or P0 recovery path. The existing
 * {@link OverlayUpdateReceiver} supplies the existing {@link OperatorState}
 * operations through {@link Sink}.</p>
 */
public final class HeartbeatIngressPolicy {
    public interface Sink {
        void persistHeartbeatLights(String payloadJson);
        void heartbeat();
    }

    public static final class Result {
        public final boolean payloadPresent;
        public final boolean payloadAccepted;
        public final boolean heartbeatAccepted;
        public final String boundary;

        private Result(
                boolean payloadPresent,
                boolean payloadAccepted,
                boolean heartbeatAccepted,
                String boundary) {
            this.payloadPresent = payloadPresent;
            this.payloadAccepted = payloadAccepted;
            this.heartbeatAccepted = heartbeatAccepted;
            this.boundary = cleanBoundary(boundary);
        }
    }

    private HeartbeatIngressPolicy() {
    }

    /**
     * Apply one heartbeat event through the existing state owner.
     *
     * <p>Only {@link IllegalArgumentException} from optional payload persistence is
     * classified as caller-invalid telemetry. That rejection preserves the old
     * payload and still advances the independent heartbeat. Other runtime failures
     * (for example a SharedPreferences commit failure) propagate unchanged instead
     * of being hidden behind a healthy liveness claim.</p>
     */
    public static Result apply(String payloadJson, Sink sink) {
        if (sink == null) throw new IllegalArgumentException("heartbeat ingress sink is required");

        boolean payloadPresent = payloadJson != null && !payloadJson.trim().isEmpty();
        if (!payloadPresent) {
            sink.heartbeat();
            return new Result(false, false, true, "");
        }

        try {
            sink.persistHeartbeatLights(payloadJson);
        } catch (IllegalArgumentException invalidPayload) {
            sink.heartbeat();
            return new Result(
                    true,
                    false,
                    true,
                    rejectionBoundary(invalidPayload));
        }

        sink.heartbeat();
        return new Result(true, true, true, "");
    }

    private static String rejectionBoundary(IllegalArgumentException failure) {
        String message = failure == null ? "" : failure.getMessage();
        String clean = cleanBoundary(message);
        if (clean.isEmpty()) {
            return "Heartbeat skill-light payload was rejected by ingress validation.";
        }
        return "Heartbeat skill-light payload rejected: " + clean;
    }

    private static String cleanBoundary(String value) {
        String clean = value == null ? "" : value.trim();
        clean = clean.replace('\r', ' ').replace('\n', ' ');
        while (clean.contains("  ")) clean = clean.replace("  ", " ");
        if (clean.length() > 320) clean = clean.substring(0, 320);
        return clean;
    }
}
