package com.dclar.homecenter;

import java.util.Arrays;
import java.util.List;

public final class MarkdownSentenceChunkerTest {
    public static void main(String[] args) {
        startupUsesWholeSentences();
        steadyStatePacksWithoutCutting();
        speakerOwnershipRepeats();
        longSentenceRemainsWhole();
        abbreviationsAndQuotesStayNatural();
        System.out.println("MarkdownSentenceChunkerTest: OK");
    }

    private static void startupUsesWholeSentences() {
        List<String> chunks = MarkdownSentenceChunker.chunkSpeechBlocks(Arrays.asList(
                "One sentence. Two sentence! Three sentence? Four sentence. Five sentence. Six sentence."), 80, 4);
        expect(chunks.size() == 5, "four startup sentences plus one packed tail");
        expect("One sentence.".equals(chunks.get(0)), "first sentence boundary");
        expect("Two sentence!".equals(chunks.get(1)), "second sentence boundary");
        expect("Three sentence?".equals(chunks.get(2)), "third sentence boundary");
        expect("Four sentence.".equals(chunks.get(3)), "fourth sentence boundary");
        expect("Five sentence. Six sentence.".equals(chunks.get(4)), "tail packs whole sentences");
    }

    private static void steadyStatePacksWithoutCutting() {
        String text = "Alpha ends here. Beta also ends here. Gamma completes the passage.";
        List<String> chunks = MarkdownSentenceChunker.chunkSpeechBlocks(Arrays.asList(text), 34, 0);
        expect(String.join(" ", chunks).equals(text), "reconstruction preserves all text");
        for (String chunk : chunks) expect(chunk.matches(".*[.!?]$"), "every ordinary chunk ends at sentence punctuation: " + chunk);
    }

    private static void speakerOwnershipRepeats() {
        List<String> chunks = MarkdownSentenceChunker.chunkSpeechBlocks(Arrays.asList(
                "[speaker:Ada] First line. Second line. Third line. Fourth line. Fifth line."), 24, 4);
        expect(chunks.size() == 5, "speaker turn sentence count");
        for (String chunk : chunks) expect(chunk.startsWith("[speaker:Ada] "), "speaker tag repeated: " + chunk);
    }

    private static void longSentenceRemainsWhole() {
        String longSentence = "This deliberately long sentence has no internal terminal punctuation and must remain whole even when the packing target is tiny";
        List<String> chunks = MarkdownSentenceChunker.chunkSpeechBlocks(Arrays.asList(longSentence), 20, 0);
        expect(chunks.size() == 1 && longSentence.equals(chunks.get(0)), "long sentence cannot fall back to character cutting");
    }

    private static void abbreviationsAndQuotesStayNatural() {
        List<String> units = MarkdownSentenceChunker.sentenceUnits("Dr. Aronnax waited. \"Ready?\" Conseil asked. \"Yes.\"");
        expect(units.size() == 3, "abbreviation and quoted sentence boundaries: " + units);
        expect("Dr. Aronnax waited.".equals(units.get(0)), "Dr abbreviation stays attached");
        expect("\"Ready?\" Conseil asked.".equals(units.get(1)), "quoted question stays with attribution");
    }

    private static void expect(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
