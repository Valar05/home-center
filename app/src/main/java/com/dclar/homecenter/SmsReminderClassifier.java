package com.dclar.homecenter;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class SmsReminderClassifier {
    static final String CLASSIFIER_VERSION = "2026-07-26.deterministic-v2";
    static final int DEFAULT_DURATION_MINUTES = 60;

    private static final Pattern SERVICE = Pattern.compile(
            "\\b(vts|ivx|infusion|appointment|appt|clinic|hospital|doctor|dentist|dental|therapy|therapist|provider|pharmacy|lab|imaging|radiology|meeting|reservation|visit)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern SCHEDULE = Pattern.compile(
            "\\b(reminder|scheduled|confirmed|rescheduled|cancel(?:led|ation)?|arrive|check[ -]?in|visit|follow[ -]?up|appointment|appt|meeting|reservation)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern SENSITIVE_NON_REMINDER = Pattern.compile(
            "\\b(verification code|security code|one[- ]time (?:code|passcode)|otp|login code|password reset|fraud alert)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern MARKETING = Pattern.compile(
            "\\b(sale|coupon|promo code|percent off|% off|buy one|get one|limited time offer)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern RELATIVE_DATE = Pattern.compile("\\b(today|tomorrow)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern WEEKDAY = Pattern.compile(
            "\\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern NUMERIC_DATE = Pattern.compile("\\b(\\d{1,2})/(\\d{1,2})(?:/(\\d{2,4}))?\\b");
    private static final Pattern AM_PM_TIME = Pattern.compile(
            "\\b(\\d{1,2})(?::(\\d{2}))?\\s*(a\\.?m\\.?|p\\.?m\\.?)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern TWENTY_FOUR_HOUR_TIME = Pattern.compile("\\b([01]?\\d|2[0-3]):([0-5]\\d)\\b");
    private static final Pattern AMBIGUOUS_TIME = Pattern.compile("\\bat\\s+(\\d{1,2})(?![:0-9])\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern DURATION = Pattern.compile(
            "\\b(\\d{1,3})\\s*(minutes?|mins?|hours?|hrs?)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern LOCATION = Pattern.compile("(?:,\\s*|\\blocation:\\s*)(?:at\\s+)?([^,]+?)\\s*$", Pattern.CASE_INSENSITIVE);

    private SmsReminderClassifier() {
    }

    static Result classify(String sender, String body) {
        return classify(sender, body, System.currentTimeMillis(), ZoneId.systemDefault().getId(), DEFAULT_DURATION_MINUTES);
    }

    static Result classify(String sender, String body, long receivedAtMs, String timezone, int defaultDurationMinutes) {
        String exact = clean(body, 12000);
        String exactSender = clean(sender, 320);
        String excerpt = cleanWhitespace(exact, 240);
        ZoneId zone = validZone(timezone);
        ZonedDateTime received = Instant.ofEpochMilli(Math.max(1L, receivedAtMs)).atZone(zone);
        List<String> missing = new ArrayList<>();
        List<String> ambiguities = new ArrayList<>();
        List<String> inferred = new ArrayList<>();
        Map<String, String> provenance = new LinkedHashMap<>();

        if (exact.isEmpty()) {
            return Result.nonCalendar("empty", zone.getId(), excerpt);
        }
        if (SENSITIVE_NON_REMINDER.matcher(exact).find()) {
            return Result.nonCalendar("security_message", zone.getId(), excerpt);
        }
        if (MARKETING.matcher(exact).find()) {
            return Result.nonCalendar("marketing", zone.getId(), excerpt);
        }

        boolean service = SERVICE.matcher(exact).find();
        boolean schedule = SCHEDULE.matcher(exact).find();
        DateResult date = parseDate(exact, received, inferred, provenance);
        TimeResult time = parseTime(exact, provenance);
        boolean plausible = service || schedule;
        if (!plausible) return Result.nonCalendar("not_calendar_event", zone.getId(), excerpt);

        if (date.value == null) {
            missing.add("date");
            ambiguities.add("date_missing");
        }
        if (time.value == null) {
            missing.add("time");
            ambiguities.add(time.ambiguous ? "ambiguous_time" : "time_missing");
        }

        String title = proposedTitle(exact);
        provenance.put("title", "normalized_from_explicit_service_text");
        provenance.put("timezone", "configured_device_timezone");
        String location = parseLocation(exact);
        if (!location.isEmpty()) provenance.put("location", "explicit");

        int durationMinutes = parseDuration(exact);
        boolean defaultedDuration = durationMinutes <= 0;
        if (defaultedDuration) {
            durationMinutes = Math.max(1, defaultDurationMinutes);
            inferred.add("endTime");
            provenance.put("endTime", "inferred_default_duration_" + durationMinutes + "_minutes");
        } else {
            provenance.put("endTime", "explicit_duration");
        }

        ZonedDateTime start = date.value == null || time.value == null ? null
                : ZonedDateTime.of(date.value, time.value, zone);
        ZonedDateTime end = start == null ? null : start.plusMinutes(durationMinutes);
        String startTime = start == null ? "" : start.toOffsetDateTime().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        String endTime = end == null ? "" : end.toOffsetDateTime().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
        if (start != null) provenance.put("startTime", "normalized_from_explicit_date_and_time");

        String classification = ambiguities.isEmpty() ? "calendar_event" : "calendar_event_ambiguous";
        double confidence = ambiguities.isEmpty() ? 0.95 : 0.65;
        List<String> reasons = new ArrayList<>();
        if (service) reasons.add("service_or_event_language");
        if (schedule) reasons.add("schedule_language");
        if (date.value != null) reasons.add("date");
        if (time.value != null) reasons.add("time");

        return new Result(true, classification, confidence, title, startTime, endTime, durationMinutes,
                zone.getId(), location, excerpt, excerpt, missing, ambiguities, inferred, provenance, reasons,
                defaultedDuration);
    }

    private static DateResult parseDate(String body, ZonedDateTime received, List<String> inferred,
                                        Map<String, String> provenance) {
        Matcher relative = RELATIVE_DATE.matcher(body);
        if (relative.find()) {
            LocalDate value = "tomorrow".equalsIgnoreCase(relative.group(1))
                    ? received.toLocalDate().plusDays(1) : received.toLocalDate();
            inferred.add("startDate");
            provenance.put("startDate", "normalized_relative_to_received_timestamp");
            return new DateResult(value);
        }
        Matcher weekday = WEEKDAY.matcher(body);
        if (weekday.find()) {
            DayOfWeek day = dayOfWeek(weekday.group(1));
            LocalDate value = received.toLocalDate().with(TemporalAdjusters.nextOrSame(day));
            inferred.add("startDate");
            provenance.put("startDate", "normalized_weekday_relative_to_received_timestamp");
            return new DateResult(value);
        }
        Matcher numeric = NUMERIC_DATE.matcher(body);
        if (numeric.find()) {
            try {
                int month = Integer.parseInt(numeric.group(1));
                int day = Integer.parseInt(numeric.group(2));
                String yearText = numeric.group(3);
                int year = received.getYear();
                if (yearText != null && !yearText.isEmpty()) {
                    year = Integer.parseInt(yearText);
                    if (year < 100) year += 2000;
                    provenance.put("startDate", "explicit_numeric_date");
                } else {
                    inferred.add("startDateYear");
                    provenance.put("startDate", "numeric_date_with_inferred_year");
                }
                LocalDate value = LocalDate.of(year, month, day);
                if ((yearText == null || yearText.isEmpty()) && value.isBefore(received.toLocalDate())) {
                    value = value.plusYears(1);
                }
                return new DateResult(value);
            } catch (RuntimeException ignored) {
                return new DateResult(null);
            }
        }
        return new DateResult(null);
    }

    private static TimeResult parseTime(String body, Map<String, String> provenance) {
        Matcher amPm = AM_PM_TIME.matcher(body);
        if (amPm.find()) {
            int hour = Integer.parseInt(amPm.group(1));
            int minute = amPm.group(2) == null ? 0 : Integer.parseInt(amPm.group(2));
            String suffix = amPm.group(3).toLowerCase(Locale.US).replace(".", "");
            if (hour < 1 || hour > 12 || minute > 59) return new TimeResult(null, true);
            if ("pm".equals(suffix) && hour != 12) hour += 12;
            if ("am".equals(suffix) && hour == 12) hour = 0;
            provenance.put("startClockTime", "explicit");
            return new TimeResult(LocalTime.of(hour, minute), false);
        }
        Matcher twentyFour = TWENTY_FOUR_HOUR_TIME.matcher(body);
        if (twentyFour.find()) {
            provenance.put("startClockTime", "explicit_24_hour");
            return new TimeResult(LocalTime.of(Integer.parseInt(twentyFour.group(1)),
                    Integer.parseInt(twentyFour.group(2))), false);
        }
        return new TimeResult(null, AMBIGUOUS_TIME.matcher(body).find());
    }

    private static int parseDuration(String body) {
        Matcher matcher = DURATION.matcher(body);
        if (!matcher.find()) return 0;
        int value = Integer.parseInt(matcher.group(1));
        return matcher.group(2).toLowerCase(Locale.US).startsWith("h") ? value * 60 : value;
    }

    private static String parseLocation(String body) {
        Matcher matcher = LOCATION.matcher(body);
        if (!matcher.find()) return "";
        String location = clean(matcher.group(1), 500).replaceAll("[.!?]+$", "").trim();
        if (location.matches("(?i)^\\d{1,2}(?::\\d{2})?\\s*(?:a\\.?m\\.?|p\\.?m\\.?)?.*$")) return "";
        if (DURATION.matcher(location).find()) return "";
        return location;
    }

    private static String proposedTitle(String body) {
        String lower = body.toLowerCase(Locale.US);
        if (lower.contains("dentist") || lower.contains("dental")) return "Dentist appointment";
        if (lower.contains("therapy") || lower.contains("therapist")) return "Therapy appointment";
        if (lower.contains("infusion") || lower.contains("ivx")) return "Infusion appointment";
        if (lower.contains("lab")) return "Lab appointment";
        if (lower.contains("imaging") || lower.contains("radiology")) return "Imaging appointment";
        if (lower.contains("doctor") || lower.contains("clinic") || lower.contains("hospital")) return "Medical appointment";
        if (lower.contains("meeting")) return "Meeting";
        if (lower.contains("reservation")) return "Reservation";
        return "Appointment";
    }

    private static DayOfWeek dayOfWeek(String value) {
        return DayOfWeek.valueOf(value.trim().toUpperCase(Locale.US));
    }

    private static ZoneId validZone(String value) {
        try {
            return ZoneId.of(value == null || value.trim().isEmpty() ? "UTC" : value.trim());
        } catch (RuntimeException ignored) {
            return ZoneId.of("UTC");
        }
    }

    private static String clean(String value, int max) {
        String clean = value == null ? "" : value.trim();
        return clean.length() > max ? clean.substring(0, max) : clean;
    }

    private static String cleanWhitespace(String value, int max) {
        return clean(value == null ? "" : value.replaceAll("\\s+", " "), max);
    }

    private static final class DateResult {
        final LocalDate value;
        DateResult(LocalDate value) { this.value = value; }
    }

    private static final class TimeResult {
        final LocalTime value;
        final boolean ambiguous;
        TimeResult(LocalTime value, boolean ambiguous) { this.value = value; this.ambiguous = ambiguous; }
    }

    static final class Result {
        final boolean candidate;
        final String classification;
        final double confidence;
        final String title;
        final String startTime;
        final String endTime;
        final int durationMinutes;
        final String timezone;
        final String location;
        final String notes;
        final String sourceExcerpt;
        final List<String> missingFields;
        final List<String> ambiguityFlags;
        final List<String> inferredFields;
        final Map<String, String> fieldProvenance;
        final List<String> matchReasons;
        final boolean defaultedDuration;
        final String classifierVersion;
        final String classificationHash;

        Result(boolean candidate, String classification, double confidence, String title, String startTime,
               String endTime, int durationMinutes, String timezone, String location, String notes,
               String sourceExcerpt, List<String> missingFields, List<String> ambiguityFlags,
               List<String> inferredFields, Map<String, String> fieldProvenance, List<String> matchReasons,
               boolean defaultedDuration) {
            this.candidate = candidate;
            this.classification = classification;
            this.confidence = confidence;
            this.title = title;
            this.startTime = startTime;
            this.endTime = endTime;
            this.durationMinutes = durationMinutes;
            this.timezone = timezone;
            this.location = location;
            this.notes = notes;
            this.sourceExcerpt = sourceExcerpt;
            this.missingFields = immutableList(missingFields);
            this.ambiguityFlags = immutableList(ambiguityFlags);
            this.inferredFields = immutableList(inferredFields);
            this.fieldProvenance = Collections.unmodifiableMap(new LinkedHashMap<>(fieldProvenance));
            this.matchReasons = immutableList(matchReasons);
            this.defaultedDuration = defaultedDuration;
            this.classifierVersion = CLASSIFIER_VERSION;
            this.classificationHash = hashClassification();
        }

        static Result nonCalendar(String reason, String timezone, String excerpt) {
            List<String> reasons = new ArrayList<>();
            reasons.add(reason);
            return new Result(false, "not_calendar", 0.0, "", "", "", 0, timezone, "", excerpt,
                    excerpt, Collections.emptyList(), Collections.emptyList(), Collections.emptyList(),
                    Collections.emptyMap(), reasons, false);
        }

        boolean approvalEligible() {
            return candidate && missingFields.isEmpty() && ambiguityFlags.isEmpty()
                    && !title.isEmpty() && !startTime.isEmpty() && !endTime.isEmpty();
        }

        Map<String, Object> classificationMap() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("classification", classification);
            out.put("candidate", candidate);
            out.put("confidence", confidence);
            out.put("proposedTitle", title);
            out.put("proposedStartTime", emptyToNull(startTime));
            out.put("proposedEndTime", emptyToNull(endTime));
            out.put("durationMinutes", durationMinutes <= 0 ? null : durationMinutes);
            out.put("timezone", timezone);
            out.put("location", location);
            out.put("notes", notes);
            out.put("sourceExcerpt", sourceExcerpt);
            out.put("missingFields", missingFields);
            out.put("ambiguityFlags", ambiguityFlags);
            out.put("inferredFields", inferredFields);
            out.put("fieldProvenance", fieldProvenance);
            out.put("matchReasons", matchReasons);
            out.put("classifierVersion", classifierVersion);
            out.put("classificationHash", classificationHash);
            out.put("approvalEligible", approvalEligible());
            return out;
        }

        Map<String, Object> proposalMap(String sourceMessageId, String sourceHash) {
            if (!candidate) return null;
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("revision", 1);
            out.put("sourceMessageId", sourceMessageId);
            out.put("sourceHash", sourceHash);
            out.put("classificationHash", classificationHash);
            out.put("classifierVersion", classifierVersion);
            out.put("title", title);
            out.put("startTime", emptyToNull(startTime));
            out.put("endTime", emptyToNull(endTime));
            out.put("durationMinutes", durationMinutes);
            out.put("timezone", timezone);
            out.put("location", location);
            out.put("notes", notes);
            out.put("sourceExcerpt", sourceExcerpt);
            out.put("missingFields", missingFields);
            out.put("ambiguityFlags", ambiguityFlags);
            out.put("inferredFields", inferredFields);
            out.put("fieldProvenance", fieldProvenance);
            out.put("approvalEligible", approvalEligible());
            out.put("proposalHash", proposalHash(out));
            return out;
        }

        private String hashClassification() {
            return SmsCalendarIngestionContract.sha256(classification + "\n" + confidence + "\n" + title + "\n"
                    + startTime + "\n" + endTime + "\n" + durationMinutes + "\n" + timezone + "\n"
                    + location + "\n" + sourceExcerpt + "\n" + missingFields + "\n" + ambiguityFlags
                    + "\n" + inferredFields + "\n" + fieldProvenance + "\n" + classifierVersion);
        }

        private String proposalHash(Map<String, Object> proposal) {
            return SmsCalendarIngestionContract.sha256(String.valueOf(proposal.get("sourceMessageId")) + "\n"
                    + String.valueOf(proposal.get("sourceHash")) + "\n" + classificationHash + "\n"
                    + title + "\n" + startTime + "\n" + endTime + "\n" + durationMinutes + "\n"
                    + timezone + "\n" + location + "\n" + notes + "\n" + missingFields + "\n"
                    + ambiguityFlags + "\n" + inferredFields + "\n" + fieldProvenance);
        }

        private static Object emptyToNull(String value) {
            return value == null || value.isEmpty() ? null : value;
        }

        private static List<String> immutableList(List<String> values) {
            return Collections.unmodifiableList(new ArrayList<>(values));
        }
    }
}
