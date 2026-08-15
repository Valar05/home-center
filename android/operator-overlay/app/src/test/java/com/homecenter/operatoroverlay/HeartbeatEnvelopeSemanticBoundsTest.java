package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class HeartbeatEnvelopeSemanticBoundsTest {
    @Test
    public void fieldSpecificLabelLimitFailsClosed() {
        String oversized = repeat('L', HeartbeatEnvelopeParser.MAX_LABEL_CHARS + 1);

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-bounds", lightWithLabel(escape(oversized))));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains(
                "Heartbeat field label exceeds "
                        + HeartbeatEnvelopeParser.MAX_LABEL_CHARS
                        + " characters"));
    }

    @Test
    public void decodedControlCharacterCannotEnterTalkBackSemanticText() {
        String nulEscape = "\\" + "u0000";

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-control", lightWithLabel("Warm" + nulEscape + "Wall")));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("label contains a decoded control character"));
    }

    @Test
    public void edgeControlCharacterIsRejectedBeforeTrimming() {
        String tabEscape = "\\" + "u0009";

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-edge-control", lightWithLabel(tabEscape + "Warm Wall")));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("label contains a decoded control character"));
    }

    @Test
    public void unpairedUnicodeSurrogateFailsClosed() {
        String highSurrogateEscape = "\\" + "uD83E";

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-surrogate", lightWithLabel("Swan " + highSurrogateEscape)));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains("label contains an unpaired surrogate"));
    }

    @Test
    public void pairedUnicodeSurrogateRemainsValidSemanticText() {
        String high = "\\" + "uD83E";
        String low = "\\" + "uDDA2";

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope("pulse-swan", lightWithLabel("Swan " + high + low)));

        assertTrue(result.accepted());
        assertTrue(result.pulse.candidates.get(0).label.startsWith("Swan "));
    }

    @Test
    public void pulseIdentityHasItsOwnBound() {
        String oversizedPulse = repeat('p', HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS + 1);

        HeartbeatEnvelopeParser.Result result = HeartbeatEnvelopeParser.parse(
                envelope(oversizedPulse, lightWithLabel("Warm Wall")));

        assertFalse(result.accepted());
        assertTrue(result.boundary.contains(
                "Heartbeat field pulseId exceeds "
                        + HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS
                        + " characters"));
    }

    private static String envelope(String pulseId, String light) {
        return "{\"schema\":\"heartbeat-skill-lights.v1\","
                + "\"pulseId\":\"" + escape(pulseId) + "\","
                + "\"complete\":true,\"lights\":[" + light + "]}";
    }

    /** labelJsonContents is already JSON-string content, not a decoded Java label. */
    private static String lightWithLabel(String labelJsonContents) {
        return "{"
                + "\"id\":\"warm-wall\","
                + "\"label\":\"" + labelJsonContents + "\","
                + "\"provenanceKind\":\"doctrine\","
                + "\"provenanceLocator\":\"Warm Walls\","
                + "\"activationReason\":\"Accessibility semantics are material.\","
                + "\"state\":\"active\","
                + "\"changedThisPulse\":true,"
                + "\"consequence\":\"Semantic text remains bounded and speakable.\","
                + "\"evidenceBoundary\":\"Pure parser source fixture.\""
                + "}";
    }

    private static String repeat(char value, int count) {
        StringBuilder out = new StringBuilder(count);
        for (int i = 0; i < count; i++) out.append(value);
        return out.toString();
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
