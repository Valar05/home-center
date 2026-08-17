package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Collections;
import org.junit.Test;

public final class HeartbeatPersistedPollPolicyTest {
    @Test
    public void coldFullyAbsentStoreIsWaiting() {
        HeartbeatPersistedPollPolicy.Snapshot empty = snapshot("", 0L, "", 0L);

        assertTrue(empty.fullyAbsent());
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.WAITING,
                HeartbeatPersistedPollPolicy.decide(null, empty, false));
    }

    @Test
    public void negativeTimestampIsNotCanonicalAbsenceAndMustProject() {
        HeartbeatPersistedPollPolicy.Snapshot corrupted = snapshot("", 0L, "", -1L);

        assertFalse(corrupted.fullyAbsent());
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(null, corrupted, false));
    }

    @Test
    public void acceptedZeroLightPulseStillCountsAsVisibleLastGoodContact() {
        HeartbeatSceneGraph.Frame emptyButAccepted = HeartbeatSceneGraph.build(
                "pulse-zero-material",
                Collections.emptyList(),
                true,
                null);

        assertTrue(HeartbeatPersistedPollPolicy.hasVisibleLastGoodContact(emptyButAccepted));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PRESERVE_MISSING_CONTACT,
                HeartbeatPersistedPollPolicy.decide(
                        null,
                        snapshot("", 0L, "", 0L),
                        emptyButAccepted));
    }

    @Test
    public void fullyAbsentStoreAfterVisibleContactBecomesOnePreservedWound() {
        HeartbeatPersistedPollPolicy.Snapshot prior = snapshot(
                "eyJzY2hlbWEiOiJoZWFydGJlYXQtc2tpbGwtaWdodHMudjEifQ==",
                34L,
                repeat('a', 64),
                100L);
        HeartbeatPersistedPollPolicy.Snapshot empty = snapshot("", 0L, "", 0L);

        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PRESERVE_MISSING_CONTACT,
                HeartbeatPersistedPollPolicy.decide(prior, empty, true));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.SKIP_UNCHANGED,
                HeartbeatPersistedPollPolicy.decide(empty, empty, true));
    }

    @Test
    public void preContactReadWoundClearsOnlyWhenHealthyWaitingReturns() {
        HeartbeatSceneGraph.Frame preContactWound = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                null,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);
        HeartbeatPersistedPollPolicy.Snapshot empty = snapshot("", 0L, "", 0L);
        HeartbeatPersistedPollPolicy.Decision waiting = HeartbeatPersistedPollPolicy.decide(
                null,
                empty,
                preContactWound);

        assertEquals(HeartbeatPersistedPollPolicy.Decision.WAITING, waiting);
        assertTrue(HeartbeatPersistedPollPolicy.shouldClearPreContactWoundOnWaiting(
                waiting,
                preContactWound));
        assertFalse(HeartbeatPersistedPollPolicy.shouldClearPreContactWoundOnWaiting(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                preContactWound));
        assertFalse(HeartbeatPersistedPollPolicy.shouldClearPreContactWoundOnWaiting(
                waiting,
                null));
    }

    @Test
    public void waitingRecoveryNeverClearsAcceptedOrPreservedContact() {
        HeartbeatSceneGraph.Frame acceptedZeroMaterial = HeartbeatSceneGraph.build(
                "pulse-zero-material",
                Collections.emptyList(),
                true,
                null);
        HeartbeatSceneGraph.Frame preservedContact = HeartbeatSceneGraph.preserveRejectedRefresh(
                "",
                acceptedZeroMaterial,
                HeartbeatPersistedSnapshotReader.STORAGE_READ_FAILURE_BOUNDARY);

        assertFalse(HeartbeatPersistedPollPolicy.shouldClearPreContactWoundOnWaiting(
                HeartbeatPersistedPollPolicy.Decision.WAITING,
                acceptedZeroMaterial));
        assertFalse(HeartbeatPersistedPollPolicy.shouldClearPreContactWoundOnWaiting(
                HeartbeatPersistedPollPolicy.Decision.WAITING,
                preservedContact));
    }

    @Test
    public void lifecycleProjectThenSkipThenWoundThenSkipThenRecover() {
        HeartbeatPersistedPollPolicy.Snapshot first = snapshot(
                "payload-a",
                9L,
                repeat('1', 64),
                100L);
        HeartbeatPersistedPollPolicy.Snapshot samePresentationObservation = snapshot(
                "payload-a",
                9L,
                repeat('1', 64),
                900L);
        HeartbeatPersistedPollPolicy.Snapshot missing = snapshot("", 0L, "", 0L);
        HeartbeatPersistedPollPolicy.Snapshot recovered = snapshot(
                "payload-b",
                9L,
                repeat('2', 64),
                901L);

        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(null, first, false));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.SKIP_UNCHANGED,
                HeartbeatPersistedPollPolicy.decide(first, samePresentationObservation, true));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PRESERVE_MISSING_CONTACT,
                HeartbeatPersistedPollPolicy.decide(samePresentationObservation, missing, true));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.SKIP_UNCHANGED,
                HeartbeatPersistedPollPolicy.decide(missing, missing, true));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(missing, recovered, true));
    }

    @Test
    public void failedProjectRemainsRetryableWhenOwnerKeepsPriorProcessedSnapshot() {
        HeartbeatPersistedPollPolicy.Snapshot priorProcessed = snapshot(
                "payload-a",
                9L,
                repeat('3', 64),
                100L);
        HeartbeatPersistedPollPolicy.Snapshot changed = snapshot(
                "payload-b",
                9L,
                repeat('4', 64),
                101L);

        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(priorProcessed, changed, true));
        // Simulate projection abort: the owner deliberately does not retain changed.
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(priorProcessed, changed, true));
    }

    @Test
    public void identicalSemanticInputsSkipWhenOnlyPositiveWallClockObservationChanges() {
        HeartbeatPersistedPollPolicy.Snapshot earlier = snapshot(
                "abc",
                3L,
                repeat('b', 64),
                100L);
        HeartbeatPersistedPollPolicy.Snapshot later = snapshot(
                "abc",
                3L,
                repeat('b', 64),
                999999L);

        assertTrue(earlier.sameProjectionInputs(later));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.SKIP_UNCHANGED,
                HeartbeatPersistedPollPolicy.decide(earlier, later, true));
    }

    @Test
    public void shaWhitespacePoisonMustReprojectEvenWhenOtherInputsMatch() {
        HeartbeatPersistedPollPolicy.Snapshot canonical = snapshot(
                "abc",
                3L,
                repeat('b', 64),
                100L);
        HeartbeatPersistedPollPolicy.Snapshot poisoned = snapshot(
                "abc",
                3L,
                "  " + repeat('b', 64) + "  ",
                999999L);

        assertFalse(canonical.sameProjectionInputs(poisoned));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(canonical, poisoned, true));
    }

    @Test
    public void timestampValidityClassChangeMustReproject() {
        HeartbeatPersistedPollPolicy.Snapshot missingTimestamp = snapshot(
                "abc",
                3L,
                repeat('c', 64),
                0L);
        HeartbeatPersistedPollPolicy.Snapshot validTimestamp = snapshot(
                "abc",
                3L,
                repeat('c', 64),
                1L);

        assertFalse(missingTimestamp.sameProjectionInputs(validTimestamp));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(
                        missingTimestamp,
                        validTimestamp,
                        true));
    }

    @Test
    public void payloadByteCountOrShaChangeMustReproject() {
        HeartbeatPersistedPollPolicy.Snapshot prior = snapshot(
                "abc",
                3L,
                repeat('d', 64),
                10L);

        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(
                        prior,
                        snapshot("abd", 3L, repeat('d', 64), 11L),
                        true));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(
                        prior,
                        snapshot("abc", 4L, repeat('d', 64), 11L),
                        true));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(
                        prior,
                        snapshot("abc", 3L, repeat('e', 64), 11L),
                        true));
    }

    @Test
    public void inconsistentEmptyPayloadMetadataIsNotMisclassifiedAsWaiting() {
        HeartbeatPersistedPollPolicy.Snapshot inconsistent = snapshot(
                "",
                17L,
                repeat('f', 64),
                25L);

        assertFalse(inconsistent.fullyAbsent());
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PROJECT,
                HeartbeatPersistedPollPolicy.decide(null, inconsistent, false));
    }

    @Test
    public void nullSnapshotFailsClosedToMissingContactOnlyWhenContactExists() {
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.WAITING,
                HeartbeatPersistedPollPolicy.decide(null, null, false));
        assertEquals(
                HeartbeatPersistedPollPolicy.Decision.PRESERVE_MISSING_CONTACT,
                HeartbeatPersistedPollPolicy.decide(null, null, true));
    }

    private static HeartbeatPersistedPollPolicy.Snapshot snapshot(
            String payloadB64,
            long declaredBytes,
            String sha256,
            long updatedMs) {
        return new HeartbeatPersistedPollPolicy.Snapshot(
                payloadB64,
                declaredBytes,
                sha256,
                updatedMs);
    }

    private static String repeat(char value, int count) {
        StringBuilder out = new StringBuilder(count);
        for (int index = 0; index < count; index++) out.append(value);
        return out.toString();
    }
}
