package com.dclar.homecenter;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class VoiceScriptPlanner {
    static final String DEFAULT_DIALOGUE_SPEAKER = "dialogue-default";

    private static final String SPEECH_VERBS =
            "said|says|asked|asks|replied|replies|answered|answers|called|calls|"
            + "whispered|whispers|shouted|shouts|muttered|mutters|continued|continues|"
            + "snapped|snaps|sighed|sighs";
    private static final String NAME =
            "[A-Z][A-Za-z0-9.'-]*(?:\\s+[A-Z][A-Za-z0-9.'-]*){0,3}";
    private static final Pattern LEADING_ATTRIBUTION = Pattern.compile(
            "(" + NAME + ")\\s+(?i:" + SPEECH_VERBS + ")\\b[^.!?\\\"“”]*$");
    private static final Pattern TRAILING_ATTRIBUTION = Pattern.compile(
            "^[\\s,;:.!?-]*(" + NAME + ")\\s+(?i:" + SPEECH_VERBS + ")\\b");
    private static final Pattern STRUCTURAL_SPEAKER = Pattern.compile(
            "^\\s*\\[(?:speaker|voice):([^\\]]+)\\]",
            Pattern.CASE_INSENSITIVE);

    private VoiceScriptPlanner() {
    }

    static List<Segment> splitQuotedLine(String line) {
        String source = line == null ? "" : line.trim();
        List<QuoteSpan> quotes = quoteSpans(source);
        if (quotes.isEmpty()) return Collections.emptyList();

        List<Segment> segments = new ArrayList<>();
        int cursor = 0;
        for (QuoteSpan quote : quotes) {
            appendNarration(segments, source.substring(cursor, quote.open));
            String speaker = attributedSpeaker(
                    source.substring(0, quote.open),
                    source.substring(quote.close + 1));
            appendDialogue(segments, speaker, source.substring(quote.open + 1, quote.close));
            cursor = quote.close + 1;
        }
        appendNarration(segments, source.substring(cursor));
        return segments;
    }

    static String structuralSpeakerId(String chunk) {
        Matcher matcher = STRUCTURAL_SPEAKER.matcher(chunk == null ? "" : chunk);
        if (!matcher.find()) return "";
        return normalizeId(matcher.group(1));
    }

    private static List<QuoteSpan> quoteSpans(String source) {
        List<QuoteSpan> spans = new ArrayList<>();
        int open = -1;
        char opening = 0;
        for (int i = 0; i < source.length(); i++) {
            char value = source.charAt(i);
            if (open < 0) {
                if (value == '"' || value == '“') {
                    open = i;
                    opening = value;
                }
                continue;
            }
            boolean closes = (opening == '"' && value == '"')
                    || (opening == '“' && (value == '”' || value == '"'));
            if (!closes) continue;
            if (i > open + 1) spans.add(new QuoteSpan(open, i));
            open = -1;
            opening = 0;
        }
        return open < 0 ? spans : Collections.emptyList();
    }

    private static String attributedSpeaker(String before, String after) {
        String leading = lastMatch(LEADING_ATTRIBUTION, before);
        if (!leading.isEmpty()) return normalizeId(leading);
        Matcher trailing = TRAILING_ATTRIBUTION.matcher(after == null ? "" : after);
        if (trailing.find()) return normalizeId(trailing.group(1));
        return DEFAULT_DIALOGUE_SPEAKER;
    }

    private static String lastMatch(Pattern pattern, String text) {
        Matcher matcher = pattern.matcher(text == null ? "" : text);
        String match = "";
        while (matcher.find()) match = matcher.group(1);
        return match;
    }

    private static void appendNarration(List<Segment> target, String text) {
        String clean = clean(text);
        if (!clean.isEmpty()) target.add(new Segment(false, "", clean));
    }

    private static void appendDialogue(List<Segment> target, String speakerId, String text) {
        String clean = clean(text);
        if (!clean.isEmpty()) {
            target.add(new Segment(true,
                    speakerId == null || speakerId.isEmpty() ? DEFAULT_DIALOGUE_SPEAKER : speakerId,
                    clean));
        }
    }

    private static String clean(String value) {
        return value == null ? "" : value.replaceAll("\\s+", " ").trim();
    }

    private static String normalizeId(String value) {
        String clean = value == null ? "" : value.toLowerCase(Locale.US)
                .replaceAll("[^a-z0-9]+", "-")
                .replaceAll("^-|-$", "");
        return clean.isEmpty() ? DEFAULT_DIALOGUE_SPEAKER : clean;
    }

    static final class Segment {
        final boolean dialogue;
        final String speakerId;
        final String text;

        Segment(boolean dialogue, String speakerId, String text) {
            this.dialogue = dialogue;
            this.speakerId = speakerId == null ? "" : speakerId;
            this.text = text == null ? "" : text;
        }
    }

    private static final class QuoteSpan {
        final int open;
        final int close;

        QuoteSpan(int open, int close) {
            this.open = open;
            this.close = close;
        }
    }
}
