package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/** Regression source for exact persisted Base64 declaration identity. */
public final class HeartbeatPersistedBase64CanonicalityTest {
    @Test
    public void canonicalWriterEncodingIsAccepted() {
        assertTrue(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                "Zg==",
                "Zg=="));
    }

    @Test
    public void ignoredWhitespaceAliasIsRejectedInsteadOfNormalized() {
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                "Zg==\n",
                "Zg=="));
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                " Zg==",
                "Zg=="));
    }

    @Test
    public void omittedPaddingAliasIsRejectedInsteadOfRepaired() {
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                "Zg",
                "Zg=="));
    }

    @Test
    public void nonCanonicalPadBitsAreRejectedEvenWhenDecodedPayloadCanAlias() {
        // "Zg==" is the writer-equivalent encoding for one byte 0x66 ('f').
        // A permissive decoder can map alternative unused pad bits such as "Zh=="
        // to the same payload byte. Exact round-trip identity must still reject it.
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                "Zh==",
                "Zg=="));
    }

    @Test
    public void missingDeclarationsAreNotPromotedIntoCanonicalPayloadIdentity() {
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip("", ""));
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(null, "Zg=="));
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip("Zg==", null));
    }

    @Test
    public void directComparisonWorkStopsAtCanonicalPersistedTextCeiling() {
        int max = HeartbeatPersistedPollPolicy.MAX_PAYLOAD_B64_CHARS;
        String exactMax = ascii(max);
        String over = ascii(max + 1);

        assertTrue(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                exactMax,
                exactMax));
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                over,
                over));
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                exactMax,
                over));
        assertFalse(HeartbeatPersistedBase64Canonicality.matchesCanonicalRoundTrip(
                over,
                exactMax));
    }

    private static String ascii(int length) {
        char[] chars = new char[length];
        for (int index = 0; index < chars.length; index++) chars[index] = 'A';
        return new String(chars);
    }
}
