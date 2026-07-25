package com.dclar.homecenter;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

final class SmsReminderClassifier {
    private static final Pattern SERVICE = Pattern.compile(
            "\\b(vts|ivx|infusion|appointment|appt|clinic|hospital|doctor|dentist|therapy|therapist|provider|pharmacy|lab|imaging|radiology)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern SCHEDULE = Pattern.compile(
            "\\b(reminder|scheduled|confirmed|rescheduled|cancel(?:led|ation)?|arrive|check[ -]?in|visit|follow[ -]?up)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern DATE_OR_TIME = Pattern.compile(
            "(\\b(?:mon|tues|wednes|thurs|fri|satur|sun)day\\b"
                    + "|\\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\\b"
                    + "|\\b(?:today|tomorrow|tonight|next week)\\b"
                    + "|\\b\\d{1,2}[:.]\\d{2}\\s*(?:a\\.?m\\.?|p\\.?m\\.?)\\b"
                    + "|\\b\\d{1,2}\\s*(?:a\\.?m\\.?|p\\.?m\\.?)\\b"
                    + "|\\b\\d{1,2}[/-]\\d{1,2}(?:[/-]\\d{2,4})?\\b)",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern SENSITIVE_NON_REMINDER = Pattern.compile(
            "\\b(verification code|security code|one[- ]time (?:code|passcode)|otp|login code|password reset|fraud alert)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern MARKETING = Pattern.compile(
            "\\b(sale|coupon|promo code|percent off|% off|buy one|get one|limited time offer)\\b",
            Pattern.CASE_INSENSITIVE);

    private SmsReminderClassifier() {
    }

    static Result classify(String sender, String body) {
        String exact = body == null ? "" : body.trim();
        String exactSender = sender == null ? "" : sender.trim();
        if (exact.isEmpty()) return Result.rejected("empty");
        if (SENSITIVE_NON_REMINDER.matcher(exact).find()) return Result.rejected("security_message");
        if (MARKETING.matcher(exact).find()) return Result.rejected("marketing");

        boolean service = SERVICE.matcher(exact).find();
        boolean schedule = SCHEDULE.matcher(exact).find();
        boolean dateOrTime = DATE_OR_TIME.matcher(exact).find();
        boolean institutionalSender = SERVICE.matcher(exactSender).find()
                || exactSender.matches("^[+()0-9 .-]{3,}$");
        int score = (service ? 2 : 0) + (schedule ? 2 : 0) + (dateOrTime ? 2 : 0)
                + (institutionalSender ? 1 : 0);
        boolean candidate = (schedule && (service || dateOrTime))
                || (institutionalSender && service && dateOrTime);
        if (!candidate) return Result.rejected("not_a_high_confidence_reminder");

        List<String> reasons = new ArrayList<>();
        if (service) reasons.add("service_or_provider");
        if (schedule) reasons.add("schedule_language");
        if (dateOrTime) reasons.add("date_or_time");
        if (institutionalSender) reasons.add("institutional_sender");

        Set<String> aliases = new LinkedHashSet<>();
        String lower = exact.toLowerCase(Locale.US);
        if (Pattern.compile("\\bvts\\b").matcher(lower).find()) aliases.add("vts");
        if (Pattern.compile("\\bivx\\b").matcher(lower).find()) aliases.add("ivx");
        if (Pattern.compile("\\binfusion\\b").matcher(lower).find()) aliases.add("infusion");
        if (Pattern.compile("\\b(?:appointment|appt)\\b").matcher(lower).find()) aliases.add("appointment");

        return new Result(true, "candidate", Math.min(1.0, score / 7.0),
                Collections.unmodifiableList(reasons),
                Collections.unmodifiableList(new ArrayList<>(aliases)));
    }

    static final class Result {
        final boolean candidate;
        final String reason;
        final double confidence;
        final List<String> matchReasons;
        final List<String> normalizedAliases;

        Result(boolean candidate, String reason, double confidence, List<String> matchReasons, List<String> normalizedAliases) {
            this.candidate = candidate;
            this.reason = reason;
            this.confidence = confidence;
            this.matchReasons = matchReasons;
            this.normalizedAliases = normalizedAliases;
        }

        static Result rejected(String reason) {
            return new Result(false, reason, 0.0, Collections.emptyList(), Collections.emptyList());
        }
    }
}
