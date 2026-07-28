package com.dclar.homecenter;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

final class SmsCalendarIngestionContract {
    enum ReplayDecision {
        CREATE,
        ATTACH,
        CONFLICT
    }

    private SmsCalendarIngestionContract() {
    }

    static String stableMessageId(String sourceTransport, String notificationKeyHash, long messageTimestampMs) {
        String identity = clean(sourceTransport) + "\n" + clean(notificationKeyHash) + "\n"
                + Math.max(1L, messageTimestampMs);
        return "sms_" + sha256(identity).substring(0, 40);
    }

    static String immutableHash(String messageId, String sender, String senderAddress, String recipientDeviceId,
                                String body, long receivedAtMs, String sourceTransport, String rawSourceReference) {
        return sha256(clean(messageId) + "\n" + clean(sender) + "\n" + normalizePhone(senderAddress)
                + "\n" + clean(recipientDeviceId) + "\n" + clean(body) + "\n"
                + Math.max(1L, receivedAtMs) + "\n" + clean(sourceTransport) + "\n"
                + clean(rawSourceReference));
    }

    static String ingestionIdempotencyKey(String messageId, String immutableHash) {
        return "sms_ingest_" + sha256(clean(messageId) + "\n" + clean(immutableHash)).substring(0, 48);
    }

    static ReplayDecision replayDecision(String existingImmutableHash, String incomingImmutableHash) {
        String existing = clean(existingImmutableHash);
        String incoming = clean(incomingImmutableHash);
        if (existing.isEmpty()) return ReplayDecision.CREATE;
        return existing.equals(incoming) ? ReplayDecision.ATTACH : ReplayDecision.CONFLICT;
    }

    static String normalizePhone(String value) {
        String clean = clean(value);
        if (clean.isEmpty()) return "";
        boolean plus = clean.startsWith("+");
        String digits = clean.replaceAll("[^0-9]", "");
        if (digits.isEmpty()) return "";
        return plus ? "+" + digits : digits;
    }

    static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(clean(value).getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (byte item : bytes) out.append(String.format(Locale.US, "%02x", item));
            return out.toString();
        } catch (Exception error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
