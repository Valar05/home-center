package com.dclar.homecenter;

import java.text.BreakIterator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Sentence-boundary primitive owned by MainActivity.MarkdownNarrationDocument. */
final class MarkdownSentenceChunker {
    private static final Pattern SPEAKER_PREFIX = Pattern.compile("^\\s*(\\[speaker:[^\\]]+\\])\\s+(.+)$", Pattern.CASE_INSENSITIVE);
    private static final char PROTECTED_PERIOD = '\uE000';
    private static final Pattern COMMON_ABBREVIATION = Pattern.compile(
            "(?i)\\b(?:mr|mrs|ms|dr|prof|sr|jr|st|vs|etc)\\.");
    private static final Pattern DECIMAL_PERIOD = Pattern.compile("(?<=\\d)\\.(?=\\d)");
    private static final Pattern QUOTED_SENTENCE = Pattern.compile("^[\"“].*[.!?][\"”]$");
    private static final Pattern DIALOGUE_ATTRIBUTION = Pattern.compile(
            "(?i)^(?:[\\p{L}][\\p{L}'’.-]*|he|she|they)(?:\\s+(?:[\\p{L}][\\p{L}'’.-]*|and|the)){0,3}\\s+"
                    + "(?:said|asked|replied|answered|called|whispered|shouted|muttered|continued|added|cried|"
                    + "observed|remarked|exclaimed)\\b.*[.!?][\"”]?$" );

    private MarkdownSentenceChunker() { }

    static List<String> chunkSpeechBlocks(List<String> blocks, int targetChars, int startupSentenceSections) {
        List<String> chunks = new ArrayList<>();
        int startupRemaining = Math.max(0, startupSentenceSections);
        int target = Math.max(1, targetChars);
        if (blocks != null) {
            for (String value : blocks) {
                String clean = normalize(value);
                if (clean.isEmpty()) continue;
                String speakerPrefix = "";
                String body = clean;
                Matcher speaker = SPEAKER_PREFIX.matcher(clean);
                if (speaker.matches()) {
                    speakerPrefix = speaker.group(1);
                    body = normalize(speaker.group(2));
                }
                List<String> sentences = sentenceUnits(body);
                if (sentences.isEmpty()) continue;
                StringBuilder packed = new StringBuilder();
                for (String sentence : sentences) {
                    if (startupRemaining > 0) {
                        flushPacked(packed, speakerPrefix, chunks);
                        chunks.add(withSpeaker(speakerPrefix, sentence));
                        startupRemaining -= 1;
                        continue;
                    }
                    int prefixChars = speakerPrefix.isEmpty() ? 0 : speakerPrefix.length() + 1;
                    int candidateChars = prefixChars + packed.length() + (packed.length() == 0 ? 0 : 1) + sentence.length();
                    if (packed.length() > 0 && candidateChars > target) flushPacked(packed, speakerPrefix, chunks);
                    if (packed.length() > 0) packed.append(' ');
                    packed.append(sentence);
                }
                flushPacked(packed, speakerPrefix, chunks);
            }
        }
        return chunks.isEmpty() ? Collections.singletonList("") : chunks;
    }

    static List<String> sentenceUnits(String text) {
        String clean = normalize(text);
        if (clean.isEmpty()) return Collections.emptyList();
        String protectedText = protectNonTerminalPeriods(clean);
        BreakIterator iterator = BreakIterator.getSentenceInstance(Locale.US);
        iterator.setText(protectedText);
        List<String> rawSentences = new ArrayList<>();
        int start = iterator.first();
        for (int end = iterator.next(); end != BreakIterator.DONE; start = end, end = iterator.next()) {
            String sentence = normalize(restorePeriods(protectedText.substring(start, end)));
            if (!sentence.isEmpty()) rawSentences.add(sentence);
        }
        if (rawSentences.isEmpty()) rawSentences.add(clean);

        List<String> sentences = new ArrayList<>();
        for (String sentence : rawSentences) {
            if (!sentences.isEmpty()
                    && QUOTED_SENTENCE.matcher(sentences.get(sentences.size() - 1)).matches()
                    && DIALOGUE_ATTRIBUTION.matcher(sentence).matches()) {
                int previous = sentences.size() - 1;
                sentences.set(previous, sentences.get(previous) + " " + sentence);
            } else {
                sentences.add(sentence);
            }
        }
        return sentences;
    }

    private static String protectNonTerminalPeriods(String text) {
        Matcher abbreviations = COMMON_ABBREVIATION.matcher(text);
        StringBuffer protectedText = new StringBuffer();
        while (abbreviations.find()) {
            String value = abbreviations.group();
            abbreviations.appendReplacement(
                    protectedText,
                    Matcher.quoteReplacement(value.substring(0, value.length() - 1) + PROTECTED_PERIOD));
        }
        abbreviations.appendTail(protectedText);
        return DECIMAL_PERIOD.matcher(protectedText.toString()).replaceAll(String.valueOf(PROTECTED_PERIOD));
    }

    private static String restorePeriods(String text) {
        return text.replace(PROTECTED_PERIOD, '.');
    }

    private static void flushPacked(StringBuilder packed, String speakerPrefix, List<String> chunks) {
        String clean = normalize(packed == null ? "" : packed.toString());
        if (!clean.isEmpty()) chunks.add(withSpeaker(speakerPrefix, clean));
        if (packed != null) packed.setLength(0);
    }

    private static String withSpeaker(String speakerPrefix, String body) {
        return speakerPrefix == null || speakerPrefix.isEmpty() ? body : (speakerPrefix + " " + body).trim();
    }

    private static String normalize(String text) {
        return text == null ? "" : text.replaceAll("\\s+", " ").trim();
    }
}
