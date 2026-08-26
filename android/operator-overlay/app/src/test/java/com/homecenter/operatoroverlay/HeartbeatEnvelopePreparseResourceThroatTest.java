package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/**
 * RED source regression for a finite public-parser source-work throat.
 *
 * <p>The persisted writer's byte budget does not protect direct callers of
 * HeartbeatEnvelopeParser.parse(...). The parser must reject an obviously oversized
 * Java String before trim or JSON traversal can consume the whole caller-owned value.</p>
 */
public class HeartbeatEnvelopePreparseResourceThroatTest {
    @Test
    public void oversizedAllWhitespaceFailsAtResourceThroatBeforeBlankNormalization() {
        String oversized = repeat(
                ' ',
                HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS + 1);

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(oversized);

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("source resource ceiling"));
    }

    @Test
    public void exactSourceCeilingStillReachesExistingParserSemantics() {
        String exact = repeat(
                ' ',
                HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS);

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(exact);

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("Heartbeat envelope is empty"));
    }

    private static String repeat(char value, int count) {
        StringBuilder out = new StringBuilder(count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
