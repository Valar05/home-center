package com.homecenter.operatoroverlay;

/**
 * Pure classification policy for the existing Operator Overlay's persisted
 * heartbeat polling loop.
 *
 * <p>The service polls much faster than heartbeat semantics change. Re-decoding,
 * hashing, parsing, and projecting the exact same persisted semantic inputs on
 * every poll is not useful UI work. More importantly, an all-empty persisted store
 * means two different things depending on history: before any heartbeat exists it
 * is ordinary waiting; after visible last-good contact exists it is a storage-contact
 * wound and must not silently masquerade as a still-current heartbeat.</p>
 *
 * <p>This class owns no SharedPreferences access, renderer, service lifecycle,
 * transport, phone surface, queue, recovery coordinator, deployment, or P0 action.
 * The existing owner may use the decision and retain the last processed snapshot.</p>
 */
public final class HeartbeatPersistedPollPolicy {
    public static final String MISSING_AFTER_CONTACT_BOUNDARY =
            "Stored heartbeat payload contact disappeared after a visible heartbeat.";

    public enum Decision {
        /** No persisted heartbeat has ever produced visible contact yet. */
        WAITING,
        /** Persisted semantic inputs changed and must traverse verification/parser/scene. */
        PROJECT,
        /** Storage became fully absent after visible contact; preserve last-good as a wound. */
        PRESERVE_MISSING_CONTACT,
        /** The last processed projection inputs are semantically identical; do no projection work. */
        SKIP_UNCHANGED
    }

    /**
     * Exact persisted observation supplied by the existing owner.
     *
     * <p>The Base64 payload is retained exactly because a changed stored byte string
     * must be re-decoded/re-verified. SHA metadata is compared after trim because the
     * persisted projection already treats surrounding SHA whitespace as metadata
     * normalization. The wall-clock timestamp contributes only its validity class
     * ({@code > 0} versus missing): its magnitude is observation metadata, not
     * semantic identity.</p>
     */
    public static final class Snapshot {
        public final String payloadB64;
        public final long declaredBytes;
        public final String declaredSha256;
        public final long updatedMs;

        public Snapshot(
                String payloadB64,
                long declaredBytes,
                String declaredSha256,
                long updatedMs) {
            this.payloadB64 = raw(payloadB64);
            this.declaredBytes = declaredBytes;
            this.declaredSha256 = clean(declaredSha256);
            this.updatedMs = updatedMs;
        }

        /** True only for the canonical never-populated/fully-cleared store shape. */
        public boolean fullyAbsent() {
            return payloadB64.isEmpty()
                    && declaredBytes == 0L
                    && declaredSha256.isEmpty()
                    && updatedMs <= 0L;
        }

        /**
         * Equality of inputs that can change storage verification or semantic
         * projection. Positive timestamp magnitude is intentionally excluded.
         */
        public boolean sameProjectionInputs(Snapshot other) {
            if (other == null) return false;
            return payloadB64.equals(other.payloadB64)
                    && declaredBytes == other.declaredBytes
                    && declaredSha256.equals(other.declaredSha256)
                    && (updatedMs > 0L) == (other.updatedMs > 0L);
        }
    }

    private HeartbeatPersistedPollPolicy() {
    }

    /**
     * Visible contact is keyed by an accepted/preserved visible pulse identity, not
     * by material-node count. A valid pulse may legitimately contain zero material
     * lights and still be the last complete heartbeat contact.
     */
    public static boolean hasVisibleLastGoodContact(HeartbeatSceneGraph.Frame frame) {
        return frame != null && !clean(frame.visiblePulseId).isEmpty();
    }

    /** Scene-bound convenience overload so the existing owner does not invent its own contact predicate. */
    public static Decision decide(
            Snapshot previousProcessed,
            Snapshot current,
            HeartbeatSceneGraph.Frame lastGoodFrame) {
        return decide(
                previousProcessed,
                current,
                hasVisibleLastGoodContact(lastGoodFrame));
    }

    /**
     * Classify one poll without performing any Android or parsing work.
     *
     * <p>The caller should retain {@code current} only after it has applied the
     * returned decision. If an unexpected internal exception aborts projection,
     * retaining the older processed snapshot lets the next poll retry instead of
     * falsely declaring the failed work deduplicated.</p>
     */
    public static Decision decide(
            Snapshot previousProcessed,
            Snapshot current,
            boolean hasVisibleLastGoodContact) {
        if (current == null) {
            return hasVisibleLastGoodContact
                    ? Decision.PRESERVE_MISSING_CONTACT
                    : Decision.WAITING;
        }

        if (current.fullyAbsent()) {
            if (!hasVisibleLastGoodContact) return Decision.WAITING;
            if (current.sameProjectionInputs(previousProcessed)) {
                return Decision.SKIP_UNCHANGED;
            }
            return Decision.PRESERVE_MISSING_CONTACT;
        }

        if (current.sameProjectionInputs(previousProcessed)) {
            return Decision.SKIP_UNCHANGED;
        }
        return Decision.PROJECT;
    }

    private static String raw(String value) {
        return value == null ? "" : value;
    }

    private static String clean(String value) {
        return raw(value).trim();
    }
}
