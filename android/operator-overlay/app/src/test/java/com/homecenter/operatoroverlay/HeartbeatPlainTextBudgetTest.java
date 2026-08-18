package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatPlainTextBudgetTest {
    @Test
    public void returnedProjectionNeverExceedsCallerBudgetIncludingEllipsis() {
        String swan = "🦢";
        String value = repeat(swan, 12);

        String projected = HeartbeatPlainTextBudget.boundedWithEllipsis(value, 8);

        assertEquals(8, projected.codePointCount(0, projected.length()));
        assertEquals(repeat(swan, 7) + "…", projected);
        assertFalse(projected.contains("\uFFFD"));
        assertEquals(value, repeat(swan, 12));
    }

    @Test
    public void combiningSequenceIsNeverCutBeforeItsMark() {
        String value = "e\u0301xy";

        assertEquals("e\u0301…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 3));
        assertEquals("…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 2));
    }

    @Test
    public void zwjEmojiIsKeptAsOneCluster() {
        String technologist = "👩‍💻";
        String value = technologist + "x";

        assertEquals(technologist + "…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 4));
        assertEquals("…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 3));
    }

    @Test
    public void emojiModifierSequenceIsKeptAsOneCluster() {
        String thumbsUp = "👍🏽";
        String value = thumbsUp + "x";

        assertEquals(thumbsUp + "…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 3));
        assertEquals("…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 2));
    }

    @Test
    public void regionalIndicatorFlagIsKeptAsOneCluster() {
        String flag = "🇺🇸";
        String value = flag + "x";

        assertEquals(flag + "…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 3));
        assertEquals("…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 2));
    }

    @Test
    public void familyEmojiIsNeverCutInsideItsZwjChain() {
        String family = "👨‍👩‍👧‍👦";
        String value = family + "x";

        assertEquals(family + "…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 8));
        assertEquals("…", HeartbeatPlainTextBudget.boundedWithEllipsis(value, 7));
    }

    @Test
    public void tinyPositiveBudgetReturnsOneBoundedSignal() {
        assertEquals("…", HeartbeatPlainTextBudget.boundedWithEllipsis("abcdef", 1));
        assertEquals("", HeartbeatPlainTextBudget.boundedWithEllipsis("abcdef", 0));
    }

    @Test
    public void exactAndUnderBudgetTextPassThroughWithoutInventingEllipsis() {
        String family = "👨‍👩‍👧‍👦";

        assertEquals("abc", HeartbeatPlainTextBudget.boundedWithEllipsis("abc", 3));
        assertEquals("abc", HeartbeatPlainTextBudget.boundedWithEllipsis("abc", 4));
        assertEquals(family, HeartbeatPlainTextBudget.boundedWithEllipsis(family, 7));
        assertTrue(HeartbeatPlainTextBudget.boundedWithEllipsis("", 4).isEmpty());
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
