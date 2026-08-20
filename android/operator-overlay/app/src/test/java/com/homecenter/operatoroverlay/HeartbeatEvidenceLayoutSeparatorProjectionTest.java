package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatEvidenceLayoutSeparatorProjectionTest {
    @Test
    public void explicitProjectionRevealsLineAndParagraphSeparators() {
        String exact = "Warm\u2028Wall\u2029Evidence";

        assertTrue(HeartbeatInvisibleSemanticControlPolicy.containsRevealableInvisibleControl(exact));
        assertEquals(
                "Warm\\u{2028 LS}Wall\\u{2029 PS}Evidence",
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(exact));
        assertTrue(exact.contains("\u2028"));
        assertTrue(exact.contains("\u2029"));
    }

    @Test
    public void literalSeparatorMarkerCannotAliasActualSeparator() {
        String actual = "Warm\u2028Wall";
        String literal = "Warm\\u{2028 LS}Wall";

        String actualProjection =
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(actual);
        String literalProjection =
                HeartbeatInvisibleSemanticControlPolicy.explicitEvidenceProjection(literal);

        assertEquals("Warm\\u{2028 LS}Wall", actualProjection);
        assertEquals("Warm\\\\u{2028 LS}Wall", literalProjection);
        assertNotEquals(actualProjection, literalProjection);
    }

    @Test
    public void typedExplicitDetailRevealsSeparatorWithoutRewritingCanonicalSource() {
        String exactLabel = "Warm\u2028Wall";
        HeartbeatSkillPolicy.Candidate candidate = new HeartbeatSkillPolicy.Candidate(
                "separator-evidence",
                exactLabel,
                "doctrine",
                "heartbeat-invisible-semantic-controls",
                "layout separator is meaningful source text but ambiguous when emitted raw",
                HeartbeatSkillPolicy.State.BLOCKED,
                false,
                "explicit detail must expose the source distinction",
                "source projection only; routine speech unchanged");

        assertTrue(HeartbeatSkillPolicy.hasTypedSourceContract(candidate));
        String detail = HeartbeatEvidenceDetailProjection.detailContentDescription(candidate);
        assertTrue(detail.contains("Warm\\u{2028 LS}Wall"));
        assertFalse(detail.contains(exactLabel));
        assertEquals(exactLabel, candidate.label);
    }

    @Test
    public void boundedProjectionNeverCutsSeparatorMarkerInHalf() {
        String exact = "A\u2028B\u2029C";
        String projected = HeartbeatInvisibleSemanticControlPolicy.boundedEvidenceProjection(exact, 16);

        assertTrue(projected.codePointCount(0, projected.length()) <= 16);
        assertFalse(projected.matches(".*\\\\u\\{[0-9A-F]*(?:\\s[A-Z]*)?$"));
    }
}
