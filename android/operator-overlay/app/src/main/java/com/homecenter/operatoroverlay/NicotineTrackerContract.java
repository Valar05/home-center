package com.homecenter.operatoroverlay;

import java.util.Locale;
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
    private static final Pattern TRACKER_LIKE = Pattern.compile(
            "^(?:/track\\b|track(?:er|ing)?\\b|hunger\\b|tank\\b|puffs?\\b|exposure\\b).*",
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

        String trimmed = exact.trim();
        if (!trimmed.isEmpty()
                && TRACKER_LIKE.matcher(trimmed.toLowerCase(Locale.ROOT)).matches()) {
            return ParseResult.unsaved("tracker_grammar_not_exact");
        }
        return ParseResult.notTracker();
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
