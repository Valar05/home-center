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
    public void absentOptionalPayloadStillInvokesHeartbeatSink() {
        RecordingSink sink = new RecordingSink();

        HeartbeatIngressPolicy.Result result = HeartbeatIngressPolicy.apply("   ", sink);

        assertFalse(result.payloadPresent);
        assertFalse(result.payloadAccepted);
        assertTrue(result.heartbeatInvoked);
        assertEquals("", result.boundary);
        assertEquals(Arrays.asList("heartbeat"), sink.events);
    }

    @Test
    public void validOptionalPayloadIsAcceptedBeforeHeartbeatSinkInvocation() {
        RecordingSink sink = new RecordingSink();

        HeartbeatIngressPolicy.Result result = HeartbeatIngressPolicy.apply("{\"schema\":\"ok\"}", sink);

        assertTrue(result.payloadPresent);
        assertTrue(result.payloadAccepted);
        assertTrue(result.heartbeatInvoked);
        assertEquals("", result.boundary);
        assertEquals(
                Arrays.asList("persist:{\"schema\":\"ok\"}", "heartbeat"),
                sink.events);
    }

    @Test
    public void callerInvalidOptionalPayloadStillInvokesIndependentHeartbeatSink() {
        RecordingSink sink = new RecordingSink();
        sink.invalidPayload = new HeartbeatIngressPolicy.CallerInvalidPayloadException(
                "invalid Unicode\nfrom optional lights");

        HeartbeatIngressPolicy.Result result = HeartbeatIngressPolicy.apply("{bad}", sink);

        assertTrue(result.payloadPresent);
        assertFalse(result.payloadAccepted);
        assertTrue(result.heartbeatInvoked);
        assertEquals(
                "Heartbeat skill-light payload rejected: invalid Unicode from optional lights",
                result.boundary);
        assertEquals(Arrays.asList("persist:{bad}", "heartbeat"), sink.events);
    }

    @Test
    public void unrelatedIllegalArgumentExceptionPropagatesWithoutHeartbeat() {
        RecordingSink sink = new RecordingSink();
        sink.argumentFailure = new IllegalArgumentException("internal persistence contract failed");

        try {
            HeartbeatIngressPolicy.apply("{\"schema\":\"ok\"}", sink);
            fail("Expected unrelated argument failure to propagate");
        } catch (IllegalArgumentException expected) {
            assertEquals("internal persistence contract failed", expected.getMessage());
        }

        assertEquals(Arrays.asList("persist:{\"schema\":\"ok\"}"), sink.events);
    }

    @Test
    public void storageFailureIsNotSwallowedOrRelabeledAsHeartbeatSuccess() {
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
    public void heartbeatSinkFailureAfterAcceptedPayloadAlsoPropagates() {
        RecordingSink sink = new RecordingSink();
        sink.heartbeatFailure = new IllegalStateException("heartbeat sink failed");

        try {
            HeartbeatIngressPolicy.apply("{\"schema\":\"ok\"}", sink);
            fail("Expected heartbeat sink failure to propagate");
        } catch (IllegalStateException expected) {
            assertEquals("heartbeat sink failed", expected.getMessage());
        }

        assertEquals(
                Arrays.asList("persist:{\"schema\":\"ok\"}", "heartbeat"),
                sink.events);
    }

    private static final class RecordingSink implements HeartbeatIngressPolicy.Sink {
        final List<String> events = new ArrayList<>();
        HeartbeatIngressPolicy.CallerInvalidPayloadException invalidPayload;
        IllegalArgumentException argumentFailure;
        IllegalStateException storageFailure;
        IllegalStateException heartbeatFailure;

        @Override
        public void persistHeartbeatLights(String payloadJson) {
            events.add("persist:" + payloadJson);
            if (invalidPayload != null) throw invalidPayload;
            if (argumentFailure != null) throw argumentFailure;
            if (storageFailure != null) throw storageFailure;
        }

        @Override
        public void heartbeat() {
            events.add("heartbeat");
            if (heartbeatFailure != null) throw heartbeatFailure;
        }
    }
}
