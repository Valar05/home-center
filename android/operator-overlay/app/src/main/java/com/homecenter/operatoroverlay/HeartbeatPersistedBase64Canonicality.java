package com.homecenter.operatoroverlay;

/**
 * Exact canonicality policy for the persisted heartbeat Base64 declaration.
 *
 * <p>{@link OperatorState#updateHeartbeatLights} owns the writer encoding and emits
 * standard padded Base64 with {@code android.util.Base64.NO_WRAP}. The existing
 * overlay owner decodes the stored declaration before byte-count/SHA verification.
 * A tolerant decoder may accept multiple textual declarations for the same decoded
 * bytes (for example ignored whitespace, omitted padding, or non-canonical pad
 * bits). Byte-count and SHA therefore prove the decoded payload bytes, but do not
 * prove that the persisted Base64 declaration is the exact writer encoding.</p>
 *
 * <p>The owner can close that evidence gap without inventing a second decoder: decode
 * through its existing platform codec, re-encode the decoded bytes with the exact
 * writer flags, then compare the raw stored declaration to that canonical result.
 * This policy owns only the exact comparison. It never trims, repairs padding,
 * removes whitespace, case-folds, decodes, renders, touches a phone, or coordinates
 * P0 recovery.</p>
 */
final class HeartbeatPersistedBase64Canonicality {
    static final String NON_CANONICAL_BOUNDARY =
            "Stored heartbeat Base64 declaration is not the exact canonical writer encoding.";

    private HeartbeatPersistedBase64Canonicality() {
    }

    /**
     * True only when a non-empty raw persisted declaration is byte-for-character
     * identical to the canonical writer-equivalent re-encoding of its decoded bytes.
     *
     * <p>Empty/null values are not canonical payload declarations here. The poll
     * policy owns the separate WAITING/contact-loss meaning of an absent store.</p>
     *
     * <p>This direct comparison boundary also reuses the canonical persisted Base64
     * source ceiling before {@link String#equals(Object)}. Safe composition through
     * the snapshot reader already supplies bounded declarations, but direct/package
     * callers do not inherit that guarantee. Oversized exact text is rejected rather
     * than normalized, truncated, or compared with attacker-sized repeated work.</p>
     */
    static boolean matchesCanonicalRoundTrip(
            String persistedDeclaration,
            String canonicalReencodedDeclaration) {
        if (persistedDeclaration == null || canonicalReencodedDeclaration == null) {
            return false;
        }
        if (persistedDeclaration.isEmpty() || canonicalReencodedDeclaration.isEmpty()) {
            return false;
        }
        int maxChars = HeartbeatPersistedPollPolicy.MAX_PAYLOAD_B64_CHARS;
        if (persistedDeclaration.length() > maxChars
                || canonicalReencodedDeclaration.length() > maxChars) {
            return false;
        }
        return persistedDeclaration.equals(canonicalReencodedDeclaration);
    }
}
