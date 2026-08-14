package com.homecenter.operatoroverlay;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.Test;

public class NicotineTrackerLedgerTest {
    @Test
    public void appPrivateEventIsImmutableChainedAndIdempotent() throws Exception {
        File files = Files.createTempDirectory("tracker-ledger").toFile();
        NicotineTrackerContract.Draft draft =
                NicotineTrackerContract.parse("/track hunger strong").draft;
        FakeClock clock = new FakeClock(1000L, 50L, "America/Chicago");
        NicotineTrackerLedger.SaveResult first = NicotineTrackerLedger.save(
                files,
                draft,
                "local note",
                key(1),
                clock,
                () -> eventId(1),
                NicotineTrackerLedgerTest::atomicMove);
        NicotineTrackerLedger.SaveResult replay = NicotineTrackerLedger.save(
                files,
                draft,
                "local note",
                key(1),
                clock,
                () -> eventId(99),
                NicotineTrackerLedgerTest::atomicMove);

        assertTrue(first.created);
        assertFalse(replay.created);
        assertEquals(first.eventId, replay.eventId);
        assertEquals(first.eventDigest, replay.eventDigest);
        File[] events = eventFiles(files);
        assertEquals(1, events.length);
        String record = read(events[0]);
        assertTrue(record.contains("\"source\":\"local\""));
        assertTrue(record.contains("\"kind\":\"hunger\""));
        assertTrue(record.contains("\"wallTimeZone\":\"America/Chicago\""));
        assertTrue(record.contains("\"monotonicOrder\":1"));
        assertTrue(record.contains(
                "\"previousEventDigest\":\"0000000000000000000000000000000000000000000000000000000000000000\""));
        assertTrue(record.contains("\"requestDigest\":"));
        assertTrue(record.contains("\"eventDigest\":"));
    }

    @Test
    public void idempotencyCollisionWithChangedDraftFailsClosed() throws Exception {
        File files = Files.createTempDirectory("tracker-idempotency").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse("/track tank low").draft,
                "",
                key(2),
                clock,
                () -> eventId(2),
                NicotineTrackerLedgerTest::atomicMove);
        try {
            NicotineTrackerLedger.save(
                    files,
                    NicotineTrackerContract.parse("/track tank low").draft,
                    "changed",
                    key(2),
                    clock,
                    () -> eventId(3),
                    NicotineTrackerLedgerTest::atomicMove);
            fail("changed local draft reused an idempotency key");
        } catch (IllegalStateException expected) {
            assertTrue(expected.getMessage().contains("idempotency"));
        }
        assertEquals(1, eventFiles(files).length);
    }

    @Test
    public void duplicateRandomEventIdRetriesThenUsesUniqueIdentity() throws Exception {
        File files = Files.createTempDirectory("tracker-event-id-retry").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse("/track tank low").draft,
                "",
                key(3),
                clock,
                () -> eventId(3),
                NicotineTrackerLedgerTest::atomicMove);
        String[] candidates = new String[]{eventId(3), eventId(4)};
        AtomicInteger index = new AtomicInteger();
        NicotineTrackerLedger.SaveResult second = NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse("/track hunger mild").draft,
                "",
                key(4),
                clock,
                () -> candidates[index.getAndIncrement()],
                NicotineTrackerLedgerTest::atomicMove);
        assertEquals(eventId(4), second.eventId);
        assertEquals(2, eventFiles(files).length);
    }

    @Test
    public void duplicateRandomEventIdRetryExhaustionAppendsNothing() throws Exception {
        File files = Files.createTempDirectory("tracker-event-id-exhaust").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse("/track tank low").draft,
                "",
                key(5),
                clock,
                () -> eventId(5),
                NicotineTrackerLedgerTest::atomicMove);
        try {
            NicotineTrackerLedger.save(
                    files,
                    NicotineTrackerContract.parse("/track hunger moderate").draft,
                    "",
                    key(6),
                    clock,
                    () -> eventId(5),
                    NicotineTrackerLedgerTest::atomicMove);
            fail("duplicate event id was accepted");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("collision retry"));
        }
        assertEquals(1, eventFiles(files).length);
    }

    @Test
    public void duplicateImmutableEventIdBlocksAppend() throws Exception {
        File files = Files.createTempDirectory("tracker-duplicate-record").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        NicotineTrackerLedger.SaveResult first = save(
                files, "/track hunger mild", key(18), eventId(18), clock);
        save(files, "/track tank high", key(19), eventId(19), clock);
        File originalSecond = eventFiles(files)[1];
        String requestDigest = digest(
                "request-v1", "tank", "high", "", key(19), "local");
        String eventDigest = digest(
                "adam-nicotine-tracker-event-v1",
                eventId(18),
                "2",
                first.eventDigest,
                "1000",
                "UTC",
                "50",
                "local",
                "tank",
                "high",
                "",
                key(19),
                requestDigest);
        String duplicate = "{"
                + "\"schema\":\"adam-nicotine-tracker-event-v1\","
                + "\"eventId\":\"" + eventId(18) + "\","
                + "\"monotonicOrder\":2,"
                + "\"previousEventDigest\":\"" + first.eventDigest + "\","
                + "\"wallTimeEpochMs\":1000,"
                + "\"wallTimeZone\":\"UTC\","
                + "\"monotonicNanos\":50,"
                + "\"source\":\"local\","
                + "\"kind\":\"tank\","
                + "\"value\":\"high\","
                + "\"note\":\"\","
                + "\"idempotencyKey\":\"" + key(19) + "\","
                + "\"requestDigest\":\"" + requestDigest + "\","
                + "\"eventDigest\":\"" + eventDigest + "\"}\n";
        File duplicateFile = new File(
                originalSecond.getParentFile(),
                String.format(Locale.ROOT, "%020d-%s.json", 2, eventId(18)));
        Files.write(duplicateFile.toPath(), duplicate.getBytes(StandardCharsets.UTF_8));
        assertTrue(originalSecond.delete());
        assertAppendBlocked(files, clock, "duplicate immutable local event id");
        assertEquals(2, eventFiles(files).length);
    }

    @Test
    public void monotonicOrderSurvivesWallClockMovingBackward() throws Exception {
        File files = Files.createTempDirectory("tracker-order").toFile();
        FakeClock clock = new FakeClock(5000L, 100L, "UTC");
        NicotineTrackerLedger.SaveResult first = save(
                files, "/track puffs 4", key(7), eventId(7), clock);
        clock.wall = 1000L;
        clock.monotonic = 200L;
        NicotineTrackerLedger.SaveResult second = save(
                files, "/track exposure skin", key(8), eventId(8), clock);
        assertEquals(1L, first.monotonicOrder);
        assertEquals(2L, second.monotonicOrder);
        assertTrue(read(eventFiles(files)[1]).contains(
                "\"previousEventDigest\":\"" + first.eventDigest + "\""));
    }

    @Test
    public void corruptedRequestDigestBlocksReplayAndAppend() throws Exception {
        File files = Files.createTempDirectory("tracker-request-digest").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        save(files, "/track hunger mild", key(9), eventId(9), clock);
        corruptDigest(eventFiles(files)[0], "requestDigest");
        assertAppendBlocked(files, clock, "request digest");
        assertEquals(1, eventFiles(files).length);
    }

    @Test
    public void corruptedEventDigestBlocksReplayAndAppend() throws Exception {
        File files = Files.createTempDirectory("tracker-event-digest").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        save(files, "/track hunger mild", key(10), eventId(10), clock);
        corruptDigest(eventFiles(files)[0], "eventDigest");
        assertAppendBlocked(files, clock, "event digest");
        assertEquals(1, eventFiles(files).length);
    }

    @Test
    public void deletedEventCreatesGapAndBlocksAppend() throws Exception {
        File files = Files.createTempDirectory("tracker-gap").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        save(files, "/track hunger mild", key(11), eventId(11), clock);
        save(files, "/track tank high", key(12), eventId(12), clock);
        save(files, "/track puffs 3", key(13), eventId(13), clock);
        File[] before = eventFiles(files);
        assertTrue(before[1].delete());
        assertAppendBlocked(files, clock, "deletion or gap");
        assertEquals(2, eventFiles(files).length);
    }

    @Test
    public void truncatedEventBlocksAppend() throws Exception {
        File files = Files.createTempDirectory("tracker-truncated").toFile();
        FakeClock clock = new FakeClock(1000L, 50L, "UTC");
        save(files, "/track exposure eye", key(14), eventId(14), clock);
        Files.write(
                eventFiles(files)[0].toPath(),
                "{".getBytes(StandardCharsets.UTF_8),
                StandardOpenOption.TRUNCATE_EXISTING);
        assertAppendBlocked(files, clock, "truncated");
        assertEquals(1, eventFiles(files).length);
    }

    @Test
    public void failedAtomicCommitLeavesNoEventAndNoPendingDraft() throws Exception {
        File files = Files.createTempDirectory("tracker-atomic").toFile();
        try {
            NicotineTrackerLedger.save(
                    files,
                    NicotineTrackerContract.parse("/track exposure eye").draft,
                    "",
                    key(15),
                    new FakeClock(1000L, 50L, "UTC"),
                    () -> eventId(15),
                    (pending, destination) -> {
                        throw new IOException("injected atomic failure");
                    });
            fail("injected commit failure was accepted");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("injected"));
        }
        assertEquals(0, eventFiles(files).length);
        File events = new File(
                new File(files, NicotineTrackerLedger.DIRECTORY_NAME), "events");
        File[] pending = events.listFiles((dir, name) -> name.startsWith(".pending-"));
        assertTrue(pending != null && pending.length == 0);
    }

    @Test
    public void partialDestinationFromBrokenCommitIsRemoved() throws Exception {
        File files = Files.createTempDirectory("tracker-partial").toFile();
        try {
            NicotineTrackerLedger.save(
                    files,
                    NicotineTrackerContract.parse("/track tank empty").draft,
                    "",
                    key(16),
                    new FakeClock(1000L, 50L, "UTC"),
                    () -> eventId(16),
                    (pending, destination) -> {
                        Files.write(destination.toPath(), "{".getBytes(StandardCharsets.UTF_8));
                        throw new IOException("injected partial commit");
                    });
            fail("partial commit was accepted");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("injected partial"));
        }
        assertEquals(0, eventFiles(files).length);
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
                    key(17),
                    new FakeClock(1000L, 50L, "UTC"),
                    () -> eventId(17),
                    NicotineTrackerLedgerTest::atomicMove);
            fail("oversized note was accepted");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("note"));
        }
        assertEquals(0, eventFiles(files).length);
    }

    private static NicotineTrackerLedger.SaveResult save(
            File files,
            String command,
            String key,
            String eventId,
            FakeClock clock) throws Exception {
        return NicotineTrackerLedger.save(
                files,
                NicotineTrackerContract.parse(command).draft,
                "",
                key,
                clock,
                () -> eventId,
                NicotineTrackerLedgerTest::atomicMove);
    }

    private static void assertAppendBlocked(
            File files, FakeClock clock, String expectedMessage) throws Exception {
        try {
            save(files, "/track tank unknown", key(99), eventId(99), clock);
            fail("corrupt immutable ledger accepted a new event");
        } catch (IOException expected) {
            assertTrue(
                    expected.getMessage(),
                    expected.getMessage().contains(expectedMessage));
        }
    }

    private static void corruptDigest(File event, String field) throws Exception {
        String value = read(event);
        String marker = "\"" + field + "\":\"";
        int offset = value.indexOf(marker);
        assertTrue(offset >= 0);
        int digest = offset + marker.length();
        char replacement = value.charAt(digest) == '0' ? '1' : '0';
        String corrupted = value.substring(0, digest)
                + replacement
                + value.substring(digest + 1);
        Files.write(
                event.toPath(),
                corrupted.getBytes(StandardCharsets.UTF_8),
                StandardOpenOption.TRUNCATE_EXISTING);
    }

    private static String key(int value) {
        return String.format("idem_%032x", value);
    }

    private static String eventId(int value) {
        return String.format("evt_%032x", value);
    }

    private static String read(File file) throws IOException {
        return new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
    }

    private static String digest(String... fields) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        for (String field : fields) {
            byte[] encoded = field.getBytes(StandardCharsets.UTF_8);
            digest.update(ByteBuffer.allocate(4).putInt(encoded.length).array());
            digest.update(encoded);
        }
        StringBuilder result = new StringBuilder();
        for (byte value : digest.digest()) {
            result.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        }
        return result.toString();
    }

    private static File[] eventFiles(File files) {
        File events = new File(
                new File(files, NicotineTrackerLedger.DIRECTORY_NAME), "events");
        File[] result = events.listFiles((dir, name) -> name.endsWith(".json"));
        if (result == null) return new File[0];
        Arrays.sort(result, (left, right) -> left.getName().compareTo(right.getName()));
        return result;
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
