package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Test;

public class HeartbeatIngressPolicyTest {
    @Test
    public void absentOptionalPayloadStillAdvancesHeartbeat() {
        RecordingSink sink = new RecordingSink();

        HeartbeatIngressPolicy.Result result = HeartbeatIngressPolicy.apply("   ", sink);

        assertFalse(result.payloadPresent);
        assertFalse(result.payloadAccepted);
        assertTrue(result.heartbeatAccepted);
        assertEquals("", result.boundary);
        assertEquals(Arrays.asList("heartbeat"), sink.events);
    }

    @Test
    public void validOptionalPayloadPersistsBeforeHeartbeat() {
        RecordingSink sink = new RecordingSink();

        HeartbeatIngressPolicy.Result result = HeartbeatIngressPolicy.apply("{\"schema\":\"ok\"}", sink);

        assertTrue(result.payloadPresent);
        assertTrue(result.payloadAccepted);
        assertTrue(result.heartbeatAccepted);
        assertEquals("", result.boundary);
        assertEquals(
                Arrays.asList("persist:{\"schema\":\"ok\"}", "heartbeat"),
                sink.events);
    }

    @Test
    public void callerInvalidOptionalPayloadPreservesIndependentHeartbeat() {
        RecordingSink sink = new RecordingSink();
        sink.invalidPayload = new IllegalArgumentException("invalid Unicode\nfrom optional lights");

        HeartbeatIngressPolicy.Result result = HeartbeatIngressPolicy.apply("{bad}", sink);

        assertTrue(result.payloadPresent);
        assertFalse(result.payloadAccepted);
        assertTrue(result.heartbeatAccepted);
        assertEquals(
                "Heartbeat skill-light payload rejected: invalid Unicode from optional lights",
                result.boundary);
        assertEquals(Arrays.asList("persist:{bad}", "heartbeat"), sink.events);
    }

    @Test
    public void storageFailureIsNotSwallowedOrRelabeledAsHealthyHeartbeat() {
        RecordingSink sink = new RecordingSink();
        sink.storageFailure = new IllegalStateException("commit failed");

        try {
            HeartbeatIngressPolicy.apply("{\"schema\":\"ok\"}", sink);
            fail("Expected storage failure to propagate");
        } catch (IllegalStateException expected) {
            assertEquals("commit failed", expected.getMessage());
        }

        assertEquals(Arrays.asList("persist:{\"schema\":\"ok\"}"), sink.events);
    }

    @Test
    public void heartbeatFailureAfterAcceptedPayloadAlsoPropagates() {
        RecordingSink sink = new RecordingSink();
        sink.heartbeatFailure = new IllegalStateException("heartbeat commit failed");

        try {
            HeartbeatIngressPolicy.apply("{\"schema\":\"ok\"}", sink);
            fail("Expected heartbeat failure to propagate");
        } catch (IllegalStateException expected) {
            assertEquals("heartbeat commit failed", expected.getMessage());
        }

        assertEquals(
                Arrays.asList("persist:{\"schema\":\"ok\"}", "heartbeat"),
                sink.events);
    }

    private static final class RecordingSink implements HeartbeatIngressPolicy.Sink {
        final List<String> events = new ArrayList<>();
        IllegalArgumentException invalidPayload;
        IllegalStateException storageFailure;
        IllegalStateException heartbeatFailure;

        @Override
        public void persistHeartbeatLights(String payloadJson) {
            events.add("persist:" + payloadJson);
            if (invalidPayload != null) throw invalidPayload;
            if (storageFailure != null) throw storageFailure;
        }

        @Override
        public void heartbeat() {
            events.add("heartbeat");
            if (heartbeatFailure != null) throw heartbeatFailure;
        }
    }
}
