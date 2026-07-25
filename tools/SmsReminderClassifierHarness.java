package com.dclar.homecenter;

public final class SmsReminderClassifierHarness {
    private static int failures = 0;

    public static void main(String[] args) {
        accept("IVX", "Reminder: June's infusion is Tuesday at 9:30 AM. Arrive 20 minutes early.",
                "ivx infusion reminder");
        accept("VTS", "VTS appointment confirmed for 7/29 at 2 PM.", "vts fuzzy alias");
        accept("Clinic", "Your appointment was rescheduled to tomorrow at 11:00 AM.", "reschedule");
        reject("Friend", "Want to get lunch tomorrow?", "ordinary conversation");
        reject("Google", "Your verification code is 123456", "security code");
        reject("Store", "Limited time offer: 30% off through Friday", "marketing");
        reject("Friend", "The infusion scene in that movie was weird.", "medical word without schedule");
        reject("Friend", "June's appointment is Tuesday at 9 AM.", "private conversation about an appointment");
        if (failures > 0) throw new AssertionError("SmsReminderClassifier failures=" + failures);
        System.out.println("SMS reminder classifier: OK");
    }

    private static void accept(String sender, String body, String label) {
        SmsReminderClassifier.Result result = SmsReminderClassifier.classify(sender, body);
        if (!result.candidate) fail(label + " should be accepted: " + result.reason);
    }

    private static void reject(String sender, String body, String label) {
        SmsReminderClassifier.Result result = SmsReminderClassifier.classify(sender, body);
        if (result.candidate) fail(label + " should be rejected");
    }

    private static void fail(String message) {
        failures += 1;
        System.err.println("FAIL: " + message);
    }
}
