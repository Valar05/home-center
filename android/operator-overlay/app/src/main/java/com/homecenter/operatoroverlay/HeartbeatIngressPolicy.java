package com.homecenter.operatoroverlay;

/**
 * Pure ordering/error policy for one ACTION_HEARTBEAT delivery.
 *
 * <p>The heartbeat-light envelope is optional telemetry layered on top of the
 * independent liveness heartbeat. A caller-invalid optional payload must not
 * suppress liveness or erase the previously stored payload. Internal/storage
 * failures are different: they are not swallowed or relabeled as a healthy
 * heartbeat.</p>
 *
 * <p>This class owns no Android receiver registration, storage, renderer,
 * transport, phone action, queue, or P0 recovery path. The existing
 * {@link OverlayUpdateReceiver} supplies the existing {@link OperatorState}
 * operations through {@link Sink}.</p>
 */
public final class HeartbeatIngressPolicy {
    /** Maximum Unicode code points in a human-facing/loggable ingress boundary. */
    public static final int MAX_BOUNDARY_CODE_POINTS = 320;

    /**
     * Exact failure class for caller-invalid optional heartbeat-light telemetry.
     *
     * <p>This is deliberately narrower than {@link IllegalArgumentException}. A
     * persistence implementation may throw an unrelated argument/programmer error;
     * treating that as bad caller telemetry would hide an internal wound and then
     * incorrectly advance the independent heartbeat.</p>
     */
    public static final class CallerInvalidPayloadException extends IllegalArgumentException {
        public CallerInvalidPayloadException(String message) {
            super(message);
        }

        public CallerInvalidPayloadException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    public interface Sink {
        void persistHeartbeatLights(String payloadJson);
        void heartbeat();
    }

    public static final class Result {
        public final boolean payloadPresent;
        public final boolean payloadAccepted;
        /** True only when the heartbeat sink returned normally; this is not a disk-durability claim. */
        public final boolean heartbeatInvoked;
        public final String boundary;

        private Result(
                boolean payloadPresent,
                boolean payloadAccepted,
                boolean heartbeatInvoked,
                String boundary) {
            this.payloadPresent = payloadPresent;
            this.payloadAccepted = payloadAccepted;
            this.heartbeatInvoked = heartbeatInvoked;
            this.boundary = cleanBoundary(boundary);
        }
    }

    private HeartbeatIngressPolicy() {
    }

    /**
     * Apply one heartbeat event through the existing state owner.
     *
     * <p>Only {@link CallerInvalidPayloadException} from optional payload
     * persistence is classified as caller-invalid telemetry. That rejection
     * preserves the old payload and still invokes the independent heartbeat sink.
     * Unrelated {@link IllegalArgumentException}s and other runtime/storage failures
     * propagate unchanged instead of being hidden behind a healthy liveness claim.</p>
     *
     * <p>A returned {@code heartbeatInvoked=true} proves only that the supplied
     * heartbeat operation returned normally. The current OperatorState heartbeat
     * uses SharedPreferences.apply(), so this source result deliberately does not
     * claim durable disk persistence, deployment, runtime observation, or phone
     * acceptance.</p>
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
        } catch (CallerInvalidPayloadException invalidPayload) {
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

    private static String rejectionBoundary(CallerInvalidPayloadException failure) {
        String message = failure == null ? "" : failure.getMessage();
        String clean = cleanBoundary(message);
        if (clean.isEmpty()) {
            return "Heartbeat skill-light payload was rejected by ingress validation.";
        }
        return "Heartbeat skill-light payload rejected: " + clean;
    }

    /**
     * Produce one bounded human-facing boundary without laundering it into raw
     * exception identity. All ISO controls and whitespace classes collapse to one
     * ordinary space, malformed lone UTF-16 surrogates become U+FFFD, and truncation
     * happens by Unicode code point so a valid surrogate pair is never bisected.
     */
    static String cleanBoundary(String value) {
        if (value == null || value.isEmpty()) return "";

        StringBuilder normalized = new StringBuilder();
        boolean pendingSpace = false;
        for (int offset = 0; offset < value.length();) {
            int codePoint = value.codePointAt(offset);
            offset += Character.charCount(codePoint);

            if (codePoint >= Character.MIN_SURROGATE
                    && codePoint <= Character.MAX_SURROGATE) {
                codePoint = 0xfffd;
            }

            if (Character.isISOControl(codePoint)
                    || Character.isWhitespace(codePoint)
                    || Character.isSpaceChar(codePoint)) {
                if (normalized.length() > 0) pendingSpace = true;
                continue;
            }

            if (pendingSpace) {
                normalized.append(' ');
                pendingSpace = false;
            }
            normalized.appendCodePoint(codePoint);
        }

        int codePoints = normalized.codePointCount(0, normalized.length());
        if (codePoints <= MAX_BOUNDARY_CODE_POINTS) return normalized.toString();
        int end = normalized.offsetByCodePoints(0, MAX_BOUNDARY_CODE_POINTS);
        return normalized.substring(0, end);
    }
}
