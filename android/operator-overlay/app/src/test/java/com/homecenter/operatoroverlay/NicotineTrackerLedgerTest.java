package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

import org.junit.Test;

public class NicotineTrackerLedgerTest {
    @Test
    public void appPrivateEventIsImmutableAndIdempotent() throws Exception {
        File files = Files.createTempDirectory("tracker-ledger").toFile();
        NicotineTrackerContract.Draft draft =
                NicotineTrackerContract.parse("/track hunger strong").draft;
        FakeClock clock = new FakeClock(1000L, 50L, "America/Chicago");
        NicotineTrackerLedger.SaveResult first = NicotineTrackerLedger.save(
                files,
                draft,
                "local note",
                "idem_00000000000000000000000000000001",
                clock,
                () -> "evt_00000000000000000000000000000001",
                NicotineTrackerLedgerTest::atomicMove);
        NicotineTrackerLedger.SaveResult replay = NicotineTrackerLedger.save(
                files,
                draft,
                "local note",
                "idem_00000000000000000000000000000001",
                clock,
                () -> "evt_ffffffffffffffffffffffffffffffff",
                NicotineTrackerLedgerTest::atomicMove);

        assertTrue(first.created);
        assertFalse(replay.created);
        assertEquals(first.eventId, replay.eventId);
        assertEquals(first.eventDigest, replay.eventDigest);
        File[] events = eventFiles(files);
        assertEquals(1, events.length);
        String record = new String(
                Files.readAllBytes(events[0].toPath()), StandardCharsets.UTF_8);
        assertTrue(record.contains("\"source\":\"local\""));
        assertTrue(record.contains("\"kind\":\"hunger\""));
        assertTrue(record.contains("\"wallTimeZone\":\"America/Chicago\""));
        assertTrue(record.contains("\"monotonicOrder\":1"));
        assertTrue(record.contains("\"requestDigest\":"));
        assertTrue(record.contains("\"eventDigest\":"));
    }

    @Test
    public void idempotencyCollisionWithChangedDraftFailsClosed() throws Exception {
        File files = Files.createTempDirectory("tracker-idempotency").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        String key = "idem_00000000000000000000000000000002";
        NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse("/track tank low").draft,
                "",
                key,
                clock,
                () -> "evt_00000000000000000000000000000002",
                NicotineTrackerLedgerTest::atomicMove);
        try {
            NicotineTrackerLedger.save(
                    files,
                    NicotineTrackerContract.parse("/track tank low").draft,
                    "changed",
                    key,
                    clock,
                    () -> "evt_00000000000000000000000000000003",
                    NicotineTrackerLedgerTest::atomicMove);
            fail("changed local draft reused an idempotency key");
        } catch (IllegalStateException expected) {
            assertTrue(expected.getMessage().contains("idempotency"));
        }
        assertEquals(1, eventFiles(files).length);
    }

    @Test
    public void monotonicOrderSurvivesWallClockMovingBackward() throws Exception {
        File files = Files.createTempDirectory("tracker-order").toFile();
        FakeClock clock = new FakeClock(5000L, 100L, "UTC");
        NicotineTrackerLedger.SaveResult first = NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse("/track puffs 4").draft,
                "",
                "idem_00000000000000000000000000000003",
                clock,
                () -> "evt_00000000000000000000000000000004",
                NicotineTrackerLedgerTest::atomicMove);
        clock.wall = 1000L;
        clock.monotonic = 200L;
        NicotineTrackerLedger.SaveResult second = NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse("/track exposure skin").draft,
                "",
                "idem_00000000000000000000000000000004",
                clock,
                () -> "evt_00000000000000000000000000000005",
                NicotineTrackerLedgerTest::atomicMove);
        assertEquals(1L, first.monotonicOrder);
        assertEquals(2L, second.monotonicOrder);
    }

    @Test
    public void failedAtomicCommitLeavesNoEventAndNoPendingDraft() throws Exception {
        File files = Files.createTempDirectory("tracker-atomic").toFile();
        try {
            NicotineTrackerLedger.save(
                    files,
                    NicotineTrackerContract.parse("/track exposure eye").draft,
                    "",
                    "idem_00000000000000000000000000000005",
                    new FakeClock(1000L, 50L, "UTC"),
                    () -> "evt_00000000000000000000000000000006",
                    (pending, destination) -> {
                        throw new IOException("injected atomic failure");
                    });
            fail("injected commit failure was accepted");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("injected"));
        }
        assertEquals(0, eventFiles(files).length);
        File events = new File(new File(files, NicotineTrackerLedger.DIRECTORY_NAME), "events");
        File[] pending = events.listFiles((dir, name) -> name.startsWith(".pending-"));
        assertTrue(pending != null && pending.length == 0);
    }

    @Test
    public void oversizedLocalNoteIsRejectedBeforeAnyWrite() throws Exception {
        File files = Files.createTempDirectory("tracker-note").toFile();
        StringBuilder note = new StringBuilder();
        for (int i = 0; i <= NicotineTrackerContract.MAX_NOTE_CHARS; i++) note.append('x');
        try {
            NicotineTrackerLedger.save(
                    files,
                    NicotineTrackerContract.parse("/track hunger mild").draft,
                    note.toString(),
                    "idem_00000000000000000000000000000006",
                    new FakeClock(1000L, 50L, "UTC"),
                    () -> "evt_00000000000000000000000000000007",
                    NicotineTrackerLedgerTest::atomicMove);
            fail("oversized note was accepted");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("note"));
        }
        assertEquals(0, eventFiles(files).length);
    }

    private static File[] eventFiles(File files) {
        File events = new File(new File(files, NicotineTrackerLedger.DIRECTORY_NAME), "events");
        File[] result = events.listFiles((dir, name) -> name.endsWith(".json"));
        return result == null ? new File[0] : result;
    }

    private static void atomicMove(File source, File destination) throws IOException {
        Files.move(
                source.toPath(),
                destination.toPath(),
                java.nio.file.StandardCopyOption.ATOMIC_MOVE);
    }

    private static final class FakeClock implements NicotineTrackerLedger.Clock {
        long wall;
        long monotonic;
        final String zone;

        FakeClock(long wall, long monotonic, String zone) {
            this.wall = wall;
            this.monotonic = monotonic;
            this.zone = zone;
        }

        @Override
        public long wallTimeMillis() {
            return wall;
        }

        @Override
        public long monotonicNanos() {
            return monotonic;
        }

        @Override
        public String zoneId() {
            return zone;
        }
    }
}
