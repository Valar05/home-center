package com.dclar.homecenter

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PocketTtsTextSplitTest {
    private fun tokenizer(): SpTokenizer {
        val root = File(System.getProperty("user.dir") ?: ".")
        val candidates = listOf(
            File(root, "src/main/assets/pockettts/pt_tokenizer.tsv"),
            File(root, "app/src/main/assets/pockettts/pt_tokenizer.tsv"),
        )
        return SpTokenizer(candidates.first { it.isFile })
    }

    @Test fun exact20kContentsSectionUsesBoundedWordSplitsWithoutChangingText() {
        val text = "PART I CHAPTER I A SHIFTING REEF CHAPTER II PRO AND CON CHAPTER III I FORM MY RESOLUTION CHAPTER IV NED LAND CHAPTER V AT A VENTURE CHAPTER VI AT FULL STEAM CHAPTER VII AN UNKNOWN SPECIES OF WHALE CHAPTER VIII MOBILIS IN MOBILI CHAPTER IX NED LAND’S TEMPERS CHAPTER X THE MAN OF THE SEAS CHAPTER XI ALL BY ELECTRICITY CHAPTER XII SOME FIGURES CHAPTER XIII THE BLACK RIVER CHAPTER XIV A NOTE OF INVITATION CHAPTER XV A WALK ON THE BOTTOM OF THE SEA CHAPTER XVI A SUBMARINE FOREST CHAPTER XVII FOUR THOUSAND LEAGUES UNDER THE PACIFIC CHAPTER XVIII VANIKORO CHAPTER XIX TORRES STRAITS CHAPTER XX A FEW DAYS ON LAND CHAPTER XXI CAPTAIN NEMO’S THUNDERBOLT CHAPTER XXII"
        val tokenizer = tokenizer()
        val chunks = PocketTtsSynthesizer.splitIntoBestSentences(text, tokenizer)
        val expected = PocketTtsSynthesizer.prepareTextPrompt(text).first
        assertTrue("production overflow input must require multiple units", chunks.size > 1)
        assertEquals(expected, chunks.joinToString(" "))
        for (chunk in chunks) {
            val prompt = PocketTtsSynthesizer.prepareTextPrompt(chunk).first
            assertTrue("unit exceeded 50 tokens: ${tokenizer.encode(prompt).size}", tokenizer.encode(prompt).size <= 50)
        }
    }

    @Test fun ordinarySentenceSizedTextIsNotHardSplit() {
        val tokenizer = tokenizer()
        val text = "Captain Nemo watched the sea. The Nautilus continued quietly."
        val chunks = PocketTtsSynthesizer.splitIntoBestSentences(text, tokenizer)
        assertEquals(1, chunks.size)
        assertEquals(PocketTtsSynthesizer.prepareTextPrompt(text).first, chunks.single())
    }
}
