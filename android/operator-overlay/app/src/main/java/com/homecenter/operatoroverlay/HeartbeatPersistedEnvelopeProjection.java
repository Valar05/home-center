package com.homecenter.operatoroverlay;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

/**
 * Pure source bridge from persisted heartbeat payload identity into the existing
 * semantic parser/scene pipeline.
 *
 * <p>This class deliberately does not read SharedPreferences, decode Android
 * Base64, own transport, render UI, touch a phone, or mutate P0 recovery. A later
 * existing overlay owner may supply the exact decoded UTF-8 bytes together with
 * the byte-count/SHA/update metadata already persisted by {@link OperatorState}.
 * Integrity and strict UTF-8 decoding must pass before semantic parsing is
 * attempted.</p>
 */
public final class HeartbeatPersistedEnvelopeProjection {
    /** Alias the canonical ingress ceiling rather than repeating its numeric literal. */
    public static final int MAX_PAYLOAD_BYTES = OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES;

    public static final class Result {
        public final boolean storageAccepted;
        public final boolean semanticAttempted;
        public final boolean parserAccepted;
        public final boolean presentationAccepted;
        public final HeartbeatSceneGraph.Frame frame;
        public final String boundary;
        public final int observedBytes;
        public final String observedSha256;
        public final long updatedMs;

        private Result(
                boolean storageAccepted,
                boolean semanticAttempted,
                boolean parserAccepted,
                boolean presentationAccepted,
                HeartbeatSceneGraph.Frame frame,
                String boundary,
                int observedBytes,
                String observedSha256,
                long updatedMs) {
            this.storageAccepted = storageAccepted;
            this.semanticAttempted = semanticAttempted;
            this.parserAccepted = parserAccepted;
            this.presentationAccepted = presentationAccepted;
            this.frame = frame;
            this.boundary = clean(boundary);
            this.observedBytes = observedBytes;
            this.observedSha256 = clean(observedSha256);
            this.updatedMs = updatedMs;
        }
    }

    private HeartbeatPersistedEnvelopeProjection() {
    }

    /**
     * Source-compatibility adapter for callers that already possess a Java String.
     *
     * <p>This path preserves the original decoded String for semantic validation, so
     * malformed UTF-16 such as an unpaired surrogate remains visible to
     * {@link HeartbeatEnvelopeParser}. It cannot prove anything about a prior
     * Base64-to-bytes decode because those bytes have already been discarded. New
     * persisted-storage consumers should prefer {@link #projectBytes(byte[], long,
     * String, long, HeartbeatSceneGraph.Frame)}.</p>
     */
    public static Result project(
            String payloadJson,
            long declaredBytes,
            String declaredSha256,
            long updatedMs,
            HeartbeatSceneGraph.Frame lastGood) {
        if (payloadJson == null || payloadJson.isEmpty()) {
            return storageReject(
                    "Stored heartbeat payload is empty.",
                    lastGood,
                    0,
                    "",
                    updatedMs);
        }
        byte[] utf8 = payloadJson.getBytes(StandardCharsets.UTF_8);
        return projectVerifiedBytes(
                utf8,
                payloadJson,
                declaredBytes,
                declaredSha256,
                updatedMs,
                lastGood);
    }

    /**
     * Byte-first persisted-identity projection.
     *
     * <p>The caller supplies the exact bytes produced by the existing persisted
     * Base64 identity. This method snapshots the mutable array, verifies byte count
     * and SHA-256 on that exact snapshot, then performs strict UTF-8 decoding with
     * malformed/unmappable input set to REPORT. Lossy replacement decoding is never
     * allowed to manufacture semantic JSON. Only after storage identity and encoding
     * both pass does the canonical parser receive text.</p>
     *
     * <p>This is still pure source composition. It does not decode Android Base64,
     * read OperatorState, wire the existing overlay owner, render UI, or consume any
     * phone/P0 execution surface.</p>
     */
    public static Result projectBytes(
            byte[] payloadUtf8,
            long declaredBytes,
            String declaredSha256,
            long updatedMs,
            HeartbeatSceneGraph.Frame lastGood) {
        if (payloadUtf8 == null || payloadUtf8.length == 0) {
            return storageReject(
                    "Stored heartbeat payload is empty.",
                    lastGood,
                    0,
                    "",
                    updatedMs);
        }
        byte[] exact = payloadUtf8.clone();
        return projectVerifiedBytes(
                exact,
                null,
                declaredBytes,
                declaredSha256,
                updatedMs,
                lastGood);
    }

    /**
     * Verify exact persisted content identity before delegating accepted bytes to
     * the canonical parser and scene graph.
     *
     * <p>The persisted update timestamp is currently produced from
     * {@code System.currentTimeMillis()}. It proves only that a positive observation
     * timestamp was stored; it is not a monotonic sequence and must not be used to
     * reject a self-consistent payload merely because wall time moved backward or
     * two broadcasts shared the same millisecond.</p>
     *
     * <p>Storage-integrity or strict-decoding rejection delegates to the existing
     * scene-preservation organ so visible contact/checkpoint identity survives while
     * every one-shot motion bit is clamped off and the exact boundary remains
     * visible. Parser/scene rejection after storage acceptance uses the same
     * preservation semantics through {@link HeartbeatSceneGraph}.</p>
     */
    private static Result projectVerifiedBytes(
            byte[] utf8,
            String alreadyDecodedText,
            long declaredBytes,
            String declaredSha256,
            long updatedMs,
            HeartbeatSceneGraph.Frame lastGood) {
        int observedBytes = utf8.length;
        String observedSha256 = sha256(utf8);

        if (updatedMs <= 0L) {
            return storageReject(
                    "Stored heartbeat update identity is missing.",
                    lastGood,
                    observedBytes,
                    observedSha256,
                    updatedMs);
        }
        if (observedBytes > MAX_PAYLOAD_BYTES) {
            return storageReject(
                    "Stored heartbeat payload exceeds " + MAX_PAYLOAD_BYTES + " UTF-8 bytes.",
                    lastGood,
                    observedBytes,
                    observedSha256,
                    updatedMs);
        }
        if (declaredBytes != observedBytes) {
            return storageReject(
                    "Stored heartbeat byte-count mismatch: declared "
                            + declaredBytes + " observed " + observedBytes + ".",
                    lastGood,
                    observedBytes,
                    observedSha256,
                    updatedMs);
        }

        String declaredHash = clean(declaredSha256);
        if (!isCanonicalSha256(declaredHash)) {
            return storageReject(
                    "Stored heartbeat SHA-256 metadata is not canonical lowercase hex.",
                    lastGood,
                    observedBytes,
                    observedSha256,
                    updatedMs);
        }
        if (!observedSha256.equals(declaredHash)) {
            return storageReject(
                    "Stored heartbeat SHA-256 mismatch: declared identity does not match decoded UTF-8 payload.",
                    lastGood,
                    observedBytes,
                    observedSha256,
                    updatedMs);
        }

        String payloadJson = alreadyDecodedText;
        if (payloadJson == null) {
            payloadJson = decodeUtf8Strict(utf8);
            if (payloadJson == null) {
                return storageReject(
                        "Stored heartbeat payload is not valid UTF-8.",
                        lastGood,
                        observedBytes,
                        observedSha256,
                        updatedMs);
            }
        }

        HeartbeatEnvelopeParser.Result parsed = HeartbeatEnvelopeParser.parse(payloadJson);
        HeartbeatSceneGraph.Frame frame = HeartbeatSceneGraph.build(parsed, lastGood);
        boolean parserAccepted = parsed.accepted();
        boolean presentationAccepted = frame != null && !frame.refreshInterrupted;
        String boundary = presentationAccepted
                ? ""
                : frame == null
                        ? "Heartbeat semantic projection produced no frame."
                        : frame.refreshBoundary;
        return new Result(
                true,
                true,
                parserAccepted,
                presentationAccepted,
                frame,
                boundary,
                observedBytes,
                observedSha256,
                updatedMs);
    }

    private static String decodeUtf8Strict(byte[] bytes) {
        try {
            return StandardCharsets.UTF_8
                    .newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(bytes))
                    .toString();
        } catch (CharacterCodingException invalidEncoding) {
            return null;
        }
    }

    private static Result storageReject(
            String boundary,
            HeartbeatSceneGraph.Frame lastGood,
            int observedBytes,
            String observedSha256,
            long updatedMs) {
        HeartbeatSceneGraph.Frame preserved = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                lastGood,
                boundary);
        return new Result(
                false,
                false,
                false,
                false,
                preserved,
                boundary,
                observedBytes,
                observedSha256,
                updatedMs);
    }

    private static boolean isCanonicalSha256(String value) {
        if (value.length() != 64) return false;
        for (int index = 0; index < value.length(); index++) {
            char c = value.charAt(index);
            boolean digit = c >= '0' && c <= '9';
            boolean lowerHex = c >= 'a' && c <= 'f';
            if (!(digit || lowerHex)) return false;
        }
        return true;
    }

    private static String sha256(byte[] bytes) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(bytes);
            StringBuilder out = new StringBuilder(hash.length * 2);
            for (byte value : hash) {
                out.append(String.format(Locale.ROOT, "%02x", value & 0xff));
            }
            return out.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable.", impossible);
        }
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
