package com.dclar.homecenter;

import java.util.List;

public final class VoiceScriptPlannerTest {
    public static void main(String[] args) {
        narratorDialogueNarrator();
        trailingAttribution();
        curlyQuotes();
        multipleCharacters();
        unattributedDialogue();
        narrationNameMentionIsNotStructural();
        unmatchedQuoteFailsClosed();
        largeQuotedParagraphUsesBoundedAttributionScan();
        System.out.println("VoiceScriptPlannerTest: OK");
    }

    private static void narratorDialogueNarrator() {
        List<VoiceScriptPlanner.Segment> values = VoiceScriptPlanner.splitQuotedLine(
                "The room went quiet. Lexen said, \"Get down.\" Glass shattered.");
        equal(3, values.size(), "leading attribution segment count");
        segment(values.get(0), false, "", "The room went quiet. Lexen said,");
        segment(values.get(1), true, "lexen", "Get down.");
        segment(values.get(2), false, "", "Glass shattered.");
    }

    private static void trailingAttribution() {
        List<VoiceScriptPlanner.Segment> values = VoiceScriptPlanner.splitQuotedLine(
                "\"Move,\" Lexen said. The door buckled.");
        equal(2, values.size(), "trailing attribution segment count");
        segment(values.get(0), true, "lexen", "Move,");
        segment(values.get(1), false, "", "Lexen said. The door buckled.");
    }

    private static void curlyQuotes() {
        List<VoiceScriptPlanner.Segment> values = VoiceScriptPlanner.splitQuotedLine(
                "She-Raw whispered, “Bring receipts.” Then she smiled.");
        segment(values.get(0), false, "", "She-Raw whispered,");
        segment(values.get(1), true, "she-raw", "Bring receipts.");
        segment(values.get(2), false, "", "Then she smiled.");
    }

    private static void multipleCharacters() {
        List<VoiceScriptPlanner.Segment> values = VoiceScriptPlanner.splitQuotedLine(
                "Lexen said, \"Advance.\" Bea replied, \"Not blindly.\"");
        equal(4, values.size(), "multiple character segment count");
        segment(values.get(1), true, "lexen", "Advance.");
        segment(values.get(3), true, "bea", "Not blindly.");
    }

    private static void unattributedDialogue() {
        List<VoiceScriptPlanner.Segment> values = VoiceScriptPlanner.splitQuotedLine(
                "A voice came through the smoke. \"Run.\" Nobody moved.");
        segment(values.get(1), true, VoiceScriptPlanner.DEFAULT_DIALOGUE_SPEAKER, "Run.");
    }

    private static void narrationNameMentionIsNotStructural() {
        equal("", VoiceScriptPlanner.structuralSpeakerId(
                "Lexen crossed the room while Bea watched."), "name mention must stay narration");
        equal("lexen", VoiceScriptPlanner.structuralSpeakerId(
                "[speaker:Lexen] Hold the line."), "speaker tag must be structural");
    }

    private static void unmatchedQuoteFailsClosed() {
        equal(0, VoiceScriptPlanner.splitQuotedLine(
                "Lexen said, \"This never closes.").size(), "unmatched quote must not invent ownership");
    }

    private static void largeQuotedParagraphUsesBoundedAttributionScan() {
        StringBuilder text = new StringBuilder();
        for (int i = 0; i < 1200; i++) {
            text.append("Narration before ").append(i).append(". Lexen said, \"Advance ")
                    .append(i).append(".\" After. ");
        }
        long start = System.nanoTime();
        List<VoiceScriptPlanner.Segment> values = VoiceScriptPlanner.splitQuotedLine(text.toString());
        long elapsedMs = (System.nanoTime() - start) / 1000000L;
        equal(2401, values.size(), "large quoted paragraph segment count");
        if (elapsedMs > 750) {
            throw new AssertionError("large quoted paragraph scan took " + elapsedMs + "ms");
        }
    }

    private static void segment(VoiceScriptPlanner.Segment actual, boolean dialogue,
                                String speakerId, String text) {
        equal(dialogue, actual.dialogue, "dialogue flag");
        equal(speakerId, actual.speakerId, "speaker id");
        equal(text, actual.text, "segment text");
    }

    private static void equal(Object expected, Object actual, String label) {
        if (expected == null ? actual != null : !expected.equals(actual)) {
            throw new AssertionError(label + ": expected <" + expected + "> but was <" + actual + ">");
        }
    }
}
