package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

import java.nio.charset.StandardCharsets;
import org.junit.Test;

public class OperatorStateHeartbeatLightsEncodingTest {
    @Test
    public void wellFormedUnicodeMatchesCanonicalUtf8Bytes() {
        String payload = "{\"label\":\"warm wall 🦢\",\"state\":\"active\"}";

        byte[] strict = OperatorState.strictHeartbeatLightsUtf8(payload);

        assertArrayEquals(payload.getBytes(StandardCharsets.UTF_8), strict);
        assertEquals(payload, new String(strict, StandardCharsets.UTF_8));
    }

    @Test
    public void unpairedHighSurrogateIsRejectedAsCallerInvalidTelemetryBeforePersistenceEncoding() {
        String payload = "heartbeat-" + (char) 0xD800 + "-invalid";

        try {
            OperatorState.strictHeartbeatLightsUtf8(payload);
            fail("Expected malformed UTF-16 to be rejected.");
        } catch (HeartbeatIngressPolicy.CallerInvalidPayloadException expected) {
            assertEquals(
                    "heartbeat lights payload contains invalid Unicode",
                    expected.getMessage());
        }
    }

    @Test
    public void unpairedLowSurrogateIsRejectedAsCallerInvalidTelemetryBeforePersistenceEncoding() {
        String payload = "heartbeat-" + (char) 0xDC00 + "-invalid";

        try {
            OperatorState.strictHeartbeatLightsUtf8(payload);
            fail("Expected malformed UTF-16 to be rejected.");
        } catch (HeartbeatIngressPolicy.CallerInvalidPayloadException expected) {
            assertEquals(
                    "heartbeat lights payload contains invalid Unicode",
                    expected.getMessage());
        }
    }
}
