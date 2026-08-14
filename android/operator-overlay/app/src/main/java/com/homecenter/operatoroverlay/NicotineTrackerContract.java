package com.homecenter.operatoroverlay;

import java.text.Normalizer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Pure deterministic grammar for local tracker drafts.
 *
 * Parsing never persists and never grants authority to a worker. Only the
 * app-local Review/Save surface may turn a VALID result into an event.
 */
final class NicotineTrackerContract {
    static final String UNSAVED_LOCAL_DRAFT = "UNSAVED_LOCAL_DRAFT";
    static final int MAX_NOTE_CHARS = 240;

    enum State {
        NOT_TRACKER,
        VALID,
        UNSAVED_LOCAL_DRAFT
    }

    enum Kind {
        HUNGER("hunger"),
        TANK("tank"),
        PUFFS("puffs"),
        EXPOSURE("exposure");

        final String wireName;

        Kind(String wireName) {
            this.wireName = wireName;
        }
    }

    static final class Draft {
        final Kind kind;
        final String value;

        Draft(Kind kind, String value) {
            this.kind = kind;
            this.value = value;
        }
    }

    static final class ParseResult {
        final State state;
        final Draft draft;
        final String errorCode;

        private ParseResult(State state, Draft draft, String errorCode) {
            this.state = state;
            this.draft = draft;
            this.errorCode = errorCode;
        }

        static ParseResult valid(Kind kind, String value) {
            return new ParseResult(State.VALID, new Draft(kind, value), "");
        }

        static ParseResult unsaved(String errorCode) {
            return new ParseResult(State.UNSAVED_LOCAL_DRAFT, null, errorCode);
        }

        static ParseResult notTracker() {
            return new ParseResult(State.NOT_TRACKER, null, "");
        }
    }

    private static final Pattern EXACT = Pattern.compile(
            "^/track (hunger|tank|puffs|exposure) ([a-z0-9-]+)$");
    private static final Pattern TRACKING_WORD = Pattern.compile(
            "\\btrack(?:er|ing)?\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern EVENT_KIND = Pattern.compile(
            "\\b(?:hunger|tank|puffs?|exposure)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern LEADING_EVENT_KIND = Pattern.compile(
            "^(?:nicotine\\s+)?(?:hunger|tank|puffs?|exposure)\\b",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern PUFF_COUNT = Pattern.compile("^(?:0|[1-9][0-9]?|100)$");

    private NicotineTrackerContract() {}

    static ParseResult parse(String raw) {
        String exact = raw == null ? "" : raw;
        Matcher matcher = EXACT.matcher(exact);
        if (matcher.matches()) {
            String kind = matcher.group(1);
            String value = matcher.group(2);
            if ("hunger".equals(kind)) {
                return oneOf(value, Kind.HUNGER,
                        "none", "mild", "moderate", "strong", "overwhelming");
            }
            if ("tank".equals(kind)) {
                return oneOf(value, Kind.TANK,
                        "unknown", "empty", "low", "about-half", "high");
            }
            if ("puffs".equals(kind)) {
                return PUFF_COUNT.matcher(value).matches()
                        ? ParseResult.valid(Kind.PUFFS, value)
                        : ParseResult.unsaved("puff_count_out_of_range");
            }
            if ("exposure".equals(kind)) {
                return oneOf(value, Kind.EXPOSURE,
                        "mouth", "swallowed", "skin", "eye", "unknown");
            }
        }

        if (isTrackerLike(exact)) {
            return ParseResult.unsaved("tracker_grammar_not_exact");
        }
        return ParseResult.notTracker();
    }

    static boolean isTrackerLike(String raw) {
        String normalized = classificationText(raw).trim();
        if (normalized.toLowerCase(java.util.Locale.ROOT).contains("/track")) {
            return true;
        }
        if (TRACKING_WORD.matcher(normalized).find()
                && EVENT_KIND.matcher(normalized).find()) {
            return true;
        }
        return LEADING_EVENT_KIND.matcher(normalized).find();
    }

    private static String classificationText(String raw) {
        String value = raw == null ? "" : raw;
        String compatibility = Normalizer.normalize(value, Normalizer.Form.NFKD);
        StringBuilder normalized = new StringBuilder(compatibility.length());
        for (int offset = 0; offset < compatibility.length();) {
            int codePoint = compatibility.codePointAt(offset);
            int type = Character.getType(codePoint);
            if (type != Character.FORMAT
                    && type != Character.NON_SPACING_MARK
                    && type != Character.ENCLOSING_MARK
                    && !isDefaultIgnorable(codePoint)) {
                normalized.appendCodePoint(codePoint);
            }
            offset += Character.charCount(codePoint);
        }
        return normalized.toString();
    }

    private static boolean isDefaultIgnorable(int codePoint) {
        return codePoint == 0x034F
                || codePoint == 0x061C
                || between(codePoint, 0x115F, 0x1160)
                || between(codePoint, 0x17B4, 0x17B5)
                || between(codePoint, 0x180B, 0x180F)
                || between(codePoint, 0x200B, 0x200F)
                || between(codePoint, 0x202A, 0x202E)
                || between(codePoint, 0x2060, 0x206F)
                || codePoint == 0x3164
                || between(codePoint, 0xFE00, 0xFE0F)
                || codePoint == 0xFEFF
                || codePoint == 0xFFA0
                || between(codePoint, 0x1BCA0, 0x1BCA3)
                || between(codePoint, 0x1D173, 0x1D17A)
                || between(codePoint, 0xE0000, 0xE0FFF);
    }

    private static boolean between(int value, int first, int last) {
        return value >= first && value <= last;
    }

    private static ParseResult oneOf(
            String value, Kind kind, String first, String... remaining) {
        if (first.equals(value)) return ParseResult.valid(kind, value);
        for (String candidate : remaining) {
            if (candidate.equals(value)) return ParseResult.valid(kind, value);
        }
        return ParseResult.unsaved(kind.wireName + "_value_not_allowed");
    }
}
