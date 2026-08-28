package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;
import org.junit.Test;

public final class HeartbeatPersistedSnapshotReadFailureTest {
    @Test
    public void boundedReadFailurePreservesLastGoodContactAndClampsMotion() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-before-read-wound",
                Collections.emptyList(),
                true,
                null);

        HeartbeatSceneGraph.Frame preserved = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                accepted,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);

        assertTrue(preserved.refreshInterrupted);
        assertEquals("pulse-before-read-wound", preserved.visiblePulseId);
        assertEquals(
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY,
                preserved.refreshBoundary);
        assertFalse(preserved.transitionMotionAllowed);
        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(accepted, preserved));
    }

    @Test
    public void readFailureBeforeFirstContactDoesNotInventVisiblePulseIdentity() {
        HeartbeatSceneGraph.Frame preserved = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                null,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);

        assertTrue(preserved.refreshInterrupted);
        assertTrue(preserved.visiblePulseId.isEmpty());
        assertTrue(preserved.nodes.isEmpty());
        assertTrue(preserved.interruptedRefreshDescription().contains(
                "No complete heartbeat is available"));
    }

    @Test
    public void repeatedReadFailureKeepsEquivalentVisibleContactAndNoMotion() {
        HeartbeatSceneGraph.Frame accepted = HeartbeatSceneGraph.build(
                "pulse-stable",
                Collections.emptyList(),
                true,
                null);
        HeartbeatSceneGraph.Frame first = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                accepted,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);
        HeartbeatSceneGraph.Frame second = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                first,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);

        assertTrue(HeartbeatFrameCheckpoint.sameVisibleContact(first, second));
        assertEquals(first.refreshBoundary, second.refreshBoundary);
        assertFalse(first.transitionMotionAllowed);
        assertFalse(second.transitionMotionAllowed);
    }

    @Test
    public void failedReadRetryMustRetainPreviousProcessedSnapshot() {
        HeartbeatPersistedPollPolicy.Snapshot previous = new HeartbeatPersistedPollPolicy.Snapshot(
                "payload-a",
                9L,
                repeat('a', 64),
                10L);
        HeartbeatPersistedPollPolicy.Snapshot recovered = new HeartbeatPersistedPollPolicy.Snapshot(
                "payload-b",
                9L,
                repeat('b', 64),
                11L);

        // A storage-read failure produces no current Snapshot. The existing owner must not
        // overwrite previous with null; when a coherent read succeeds next poll, changed
        // storage still classifies as PROJECT rather than being falsely deduplicated.
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(previous, recovered, true));
    }

    private static String repeat(char value, int count) {
        StringBuilder out = new StringBuilder(count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
