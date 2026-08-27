package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

/** Source-only regression for finite direct work in explicit invisible-control projection. */
public class HeartbeatInvisibleSemanticControlSourceWorkTest {
    @Test
    public void exactSourceCeilingStillProjectsWithoutRewritingCanonicalText() {
        String exact = repeat("A", HeartbeatInvisibleSemanticControlPolicy.MAX_SOURCE_CODE_UNITS - 1)
                + "\u200B";

        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(exact));
        String projected = HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection(exact, 32);

        assertTrue(projected.codePointCount(0, projected.length()) <= 32);
        assertTrue(exact.endsWith("\u200B"));
    }

    @Test
    public void maxPlusOneFailsBeforeProjectionTraversalInsteadOfPretendingToBeBounded() {
        String over = repeat("A", HeartbeatInvisibleSemanticControlPolicy.MAX_SOURCE_CODE_UNITS + 1);

        expectSourceRejection(() ->
                HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(over));
        expectSourceRejection(() ->
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(over));
        expectSourceRejection(() ->
                HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection(over, 32));
    }

    @Test
    public void zeroReturnedBudgetStillNeedsNoSourceTraversal() {
        String over = repeat("A", HeartbeatInvisibleSemanticControlPolicy.MAX_SOURCE_CODE_UNITS + 1);

        assertEquals("", HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection(over, 0));
    }

    private static void expectSourceRejection(Runnable work) {
        try {
            work.run();
            fail("expected finite-source rejection");
        } catch (IllegalArgumentException expected) {
            assertEquals(
                    "explicit evidence source exceeds finite work budget",
                    expected.getMessage());
        }
    }

    private static String repeat(String value, int count) {
        StringBuilder out = new StringBuilder(value.length() * count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
