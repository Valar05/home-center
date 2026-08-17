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
    public void tinyPositiveBudgetReturnsOneBoundedSignal() {
        assertEquals("…", HeartbeatPlainTextBudget.boundedWithEllipsis("abcdef", 1));
        assertEquals("", HeartbeatPlainTextBudget.boundedWithEllipsis("abcdef", 0));
    }

    @Test
    public void exactAndUnderBudgetTextPassThroughWithoutInventingEllipsis() {
        assertEquals("abc", HeartbeatPlainTextBudget.boundedWithEllipsis("abc", 3));
        assertEquals("abc", HeartbeatPlainTextBudget.boundedWithEllipsis("abc", 4));
        assertTrue(HeartbeatPlainTextBudget.boundedWithEllipsis("", 4).isEmpty());
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder();
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
