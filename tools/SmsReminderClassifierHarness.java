package com.dclar.homecenter;

import java.time.Instant;
import java.util.Map;

public final class SmsReminderClassifierHarness {
    private static int failures = 0;
    private static final long RECEIVED = Instant.parse("2026-07-26T15:00:00Z").toEpochMilli();
    private static final String ZONE = "America/Chicago";

    public static void main(String[] args) {
        duplicateIngestionContract();
        changedContentConflict();
        nonCalendarDoesNotCreateProposal();
        clearAppointmentCreatesStructuredProposal();
        relativeTimeUsesMessageTimestampAndTimezone();
        ambiguousTimeBlocksApproval();
        missingDurationUsesDocumentedDefault();
        if (failures > 0) throw new AssertionError("SmsReminderClassifier failures=" + failures);
        System.out.println("SMS reminder classifier and ingestion contract: OK");
    }

    private static void duplicateIngestionContract() {
        String id = SmsCalendarIngestionContract.stableMessageId("android_google_messages_notification", "abc", RECEIVED);
        String hash = SmsCalendarIngestionContract.immutableHash(id, "Clinic", "+15015550100", "device",
                "Appointment tomorrow at 3 PM", RECEIVED, "android_google_messages_notification", "notification:abc");
        expect(SmsCalendarIngestionContract.replayDecision(hash, hash)
                == SmsCalendarIngestionContract.ReplayDecision.ATTACH, "exact duplicate must attach");
    }

    private static void changedContentConflict() {
        expect(SmsCalendarIngestionContract.replayDecision("first", "changed")
                == SmsCalendarIngestionContract.ReplayDecision.CONFLICT,
                "same stable message id with changed immutable content must conflict");
    }

    private static void nonCalendarDoesNotCreateProposal() {
        SmsReminderClassifier.Result result = classify("Friend", "Want to get lunch tomorrow?");
        expect(!result.candidate, "ordinary conversation must be non-calendar");
        expect(result.proposalMap("sms_test", "hash") == null, "non-calendar message must not create proposal");
    }

    private static void clearAppointmentCreatesStructuredProposal() {
        SmsReminderClassifier.Result result = classify("River Dental",
                "Dentist appointment Tuesday at 2:30 PM, 45 minutes, at River Dental.");
        expect(result.candidate, "clear dentist message must be a candidate");
        expect(result.approvalEligible(), "clear dentist proposal must be approval eligible");
        expect("Dentist appointment".equals(result.title), "dentist title must be normalized");
        expect("2026-07-28T14:30:00-05:00".equals(result.startTime), "Tuesday time must resolve in configured timezone");
        expect("2026-07-28T15:15:00-05:00".equals(result.endTime), "explicit 45 minute duration must set end");
        expect("River Dental".equals(result.location), "location must be explicit");
        Map<String, Object> proposal = result.proposalMap("sms_test", "source_hash");
        expect(Integer.valueOf(1).equals(proposal.get("revision")), "first proposal revision must be one");
        expect(!String.valueOf(proposal.get("proposalHash")).isEmpty(), "proposal must have a stable hash");
    }

    private static void relativeTimeUsesMessageTimestampAndTimezone() {
        SmsReminderClassifier.Result result = classify("Clinic", "Appointment tomorrow at 3 PM.");
        expect("2026-07-27T15:00:00-05:00".equals(result.startTime),
                "tomorrow must resolve from message timestamp in configured timezone");
        expect(result.inferredFields.contains("startDate"), "relative date must be marked inferred");
    }

    private static void ambiguousTimeBlocksApproval() {
        SmsReminderClassifier.Result result = classify("Clinic", "Appointment Tuesday at 2.");
        expect(result.candidate, "ambiguous appointment remains a review candidate");
        expect(!result.approvalEligible(), "ambiguous time must block approval");
        expect(result.ambiguityFlags.contains("ambiguous_time"), "ambiguity must be explicit");
    }

    private static void missingDurationUsesDocumentedDefault() {
        SmsReminderClassifier.Result result = classify("Clinic", "Appointment tomorrow at 3 PM.");
        expect(result.durationMinutes == 60, "missing duration must use explicit 60 minute default");
        expect(result.inferredFields.contains("endTime"), "default duration must mark end inferred");
        expect(result.fieldProvenance.get("endTime").contains("default_duration_60_minutes"),
                "default duration provenance must be recorded");
    }

    private static SmsReminderClassifier.Result classify(String sender, String body) {
        return SmsReminderClassifier.classify(sender, body, RECEIVED, ZONE,
                SmsReminderClassifier.DEFAULT_DURATION_MINUTES);
    }

    private static void expect(boolean condition, String message) {
        if (!condition) {
            failures += 1;
            System.err.println("FAIL: " + message);
        }
    }
}
