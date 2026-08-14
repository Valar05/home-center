package com.homecenter.operatoroverlay;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * App-private, append-only event ledger.
 *
 * Every append first parses and cryptographically verifies the complete chain.
 * Each new event is committed by one same-directory atomic move.
 */
final class NicotineTrackerLedger {
    static final String DIRECTORY_NAME = "nicotine-tracker-v1";
    private static final String EVENT_SCHEMA = "adam-nicotine-tracker-event-v1";
    private static final String HEAD_SCHEMA = "adam-nicotine-tracker-head-v1";
    private static final String HEAD_FILE_NAME = "head.json";
    private static final String SOURCE_LOCAL = "local";
    private static final String GENESIS_DIGEST =
            "0000000000000000000000000000000000000000000000000000000000000000";
    private static final Pattern IDEMPOTENCY =
            Pattern.compile("^idem_[a-f0-9]{32}$");
    private static final Pattern EVENT_ID =
            Pattern.compile("^evt_[a-f0-9]{32}$");
    private static final Pattern DIGEST =
            Pattern.compile("^[a-f0-9]{64}$");
    private static final Pattern EVENT_FILE =
            Pattern.compile("^(\\d{20})-(evt_[a-f0-9]{32})\\.json$");
    private static final Pattern EVENT_PENDING_FILE =
            Pattern.compile("^\\.pending-[a-f0-9]{32}$");
    private static final Pattern HEAD_PENDING_FILE =
            Pattern.compile("^\\.head-pending-[a-f0-9]{32}$");
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();
    private static final int MAX_EVENT_BYTES = 8192;
    private static final int MAX_EVENT_ID_ATTEMPTS = 8;
    private static final int MAX_PENDING_FILES = 16;

    interface Clock {
        long wallTimeMillis();
        long monotonicNanos();
        String zoneId();
    }

    interface IdSource {
        String eventId();
    }

    interface AtomicCommit {
        void commit(File pending, File destination) throws IOException;
    }

    static final class SaveResult {
        final boolean created;
        final long monotonicOrder;
        final String eventId;
        final String eventDigest;

        SaveResult(boolean created, long monotonicOrder, String eventId, String eventDigest) {
            this.created = created;
            this.monotonicOrder = monotonicOrder;
            this.eventId = eventId;
            this.eventDigest = eventDigest;
        }
    }

    private static final class Existing {
        final long monotonicOrder;
        final String eventId;
        final String idempotencyKey;
        final String requestDigest;
        final String eventDigest;

        Existing(
                long monotonicOrder,
                String eventId,
                String idempotencyKey,
                String requestDigest,
                String eventDigest) {
            this.monotonicOrder = monotonicOrder;
            this.eventId = eventId;
            this.idempotencyKey = idempotencyKey;
            this.requestDigest = requestDigest;
            this.eventDigest = eventDigest;
        }
    }

    private static final class ParsedEvent {
        String schema;
        String eventId;
        long monotonicOrder;
        String previousEventDigest;
        long wallTimeEpochMs;
        String wallTimeZone;
        long monotonicNanos;
        String source;
        String kind;
        String value;
        String note;
        String idempotencyKey;
        String requestDigest;
        String eventDigest;
    }

    private static final class HeadCheckpoint {
        String schema;
        long eventCount;
        long lastMonotonicOrder;
        String lastEventId;
        String lastEventDigest;
        String chainHeadDigest;
    }

    private NicotineTrackerLedger() {}

    static String newIdempotencyKey() {
        return "idem_" + randomHex(16);
    }

    static SaveResult save(
            File appFilesDirectory,
            NicotineTrackerContract.Draft draft,
            String note,
            String idempotencyKey,
            Clock clock) throws IOException {
        return save(
                appFilesDirectory,
                draft,
                note,
                idempotencyKey,
                clock,
                () -> "evt_" + randomHex(16),
                (pending, destination) -> Files.move(
                        pending.toPath(),
                        destination.toPath(),
                        StandardCopyOption.ATOMIC_MOVE));
    }

    static SaveResult save(
            File appFilesDirectory,
            NicotineTrackerContract.Draft draft,
            String note,
            String idempotencyKey,
            Clock clock,
            IdSource ids,
            AtomicCommit atomicCommit) throws IOException {
        return save(
                appFilesDirectory,
                draft,
                note,
                idempotencyKey,
                clock,
                ids,
                atomicCommit,
                NicotineTrackerLedger::atomicReplace);
    }

    static SaveResult save(
            File appFilesDirectory,
            NicotineTrackerContract.Draft draft,
            String note,
            String idempotencyKey,
            Clock clock,
            IdSource ids,
            AtomicCommit eventCommit,
            AtomicCommit headCommit) throws IOException {
        if (appFilesDirectory == null || draft == null || draft.kind == null || clock == null
                || ids == null || eventCommit == null || headCommit == null) {
            throw new IllegalArgumentException("local save arguments are required");
        }
        String cleanNote = note == null ? "" : note;
        if (cleanNote.length() > NicotineTrackerContract.MAX_NOTE_CHARS) {
            throw new IllegalArgumentException("local note exceeds the bounded length");
        }
        if (!IDEMPOTENCY.matcher(String.valueOf(idempotencyKey)).matches()) {
            throw new IllegalArgumentException("invalid local idempotency key");
        }
        String zone = String.valueOf(clock.zoneId());
        if (zone.isEmpty() || zone.length() > 80) {
            throw new IllegalArgumentException("invalid local wall-time zone");
        }

        File root = new File(appFilesDirectory, DIRECTORY_NAME);
        File events = new File(root, "events");
        if ((!events.isDirectory() && !events.mkdirs()) || !events.isDirectory()) {
            throw new IOException("app-private tracker directory unavailable");
        }
        File lockFile = new File(root, "ledger.lock");
        String requestDigest = requestDigest(draft, cleanNote, idempotencyKey);

        try (RandomAccessFile lockAccess = new RandomAccessFile(lockFile, "rw");
                FileChannel lockChannel = lockAccess.getChannel();
                FileLock ignored = lockChannel.lock()) {
            cleanupPending(root, events);
            Existing[] existing = scan(root, events, true);
            for (Existing event : existing) {
                if (!idempotencyKey.equals(event.idempotencyKey)) continue;
                if (!requestDigest.equals(event.requestDigest)) {
                    throw new IllegalStateException(
                            "idempotency key already belongs to a different local draft");
                }
                return new SaveResult(
                        false, event.monotonicOrder, event.eventId, event.eventDigest);
            }

            long order = Math.addExact(existing.length, 1L);
            String previousEventDigest = existing.length == 0
                    ? GENESIS_DIGEST
                    : existing[existing.length - 1].eventDigest;
            String eventId = uniqueEventId(existing, ids);
            long wallTimeMillis = clock.wallTimeMillis();
            long monotonicNanos = clock.monotonicNanos();
            if (wallTimeMillis < 0L || monotonicNanos < 0L) {
                throw new IllegalArgumentException("local event clocks must be nonnegative");
            }
            String eventDigest = eventDigest(
                    eventId,
                    order,
                    previousEventDigest,
                    wallTimeMillis,
                    zone,
                    monotonicNanos,
                    draft,
                    cleanNote,
                    idempotencyKey,
                    requestDigest);
            String record = eventJson(
                    eventId,
                    order,
                    previousEventDigest,
                    wallTimeMillis,
                    zone,
                    monotonicNanos,
                    draft.kind.wireName,
                    draft.value,
                    cleanNote,
                    idempotencyKey,
                    requestDigest,
                    eventDigest);
            byte[] bytes = (record + "\n").getBytes(StandardCharsets.UTF_8);
            if (bytes.length > MAX_EVENT_BYTES) {
                throw new IllegalArgumentException("local event exceeds bounded storage size");
            }

            File destination = new File(
                    events, String.format(Locale.ROOT, "%020d-%s.json", order, eventId));
            if (destination.exists()) {
                throw new IllegalStateException("local event destination collision");
            }
            File pending = new File(events, ".pending-" + randomHex(16));
            try {
                try (FileOutputStream output = new FileOutputStream(pending, false)) {
                    output.write(bytes);
                    output.getFD().sync();
                }
                try {
                    eventCommit.commit(pending, destination);
                    if (!destination.isFile()) {
                        throw new IOException("atomic local event commit did not materialize");
                    }
                    fsyncDirectory(events);
                    writeHead(
                            root,
                            checkpoint(
                                    existing.length + 1L,
                                    order,
                                    eventId,
                                    eventDigest),
                            headCommit);
                    Existing[] verified = scan(root, events, false);
                    Existing last = verified.length == 0 ? null : verified[verified.length - 1];
                    if (verified.length != existing.length + 1
                            || last == null
                            || last.monotonicOrder != order
                            || !eventId.equals(last.eventId)
                            || !eventDigest.equals(last.eventDigest)) {
                        throw new IOException("atomic local event postcondition failed");
                    }
                } catch (IOException | RuntimeException failure) {
                    if (destination.exists() && !destination.delete()) {
                        failure.addSuppressed(
                                new IOException("failed to remove an unverified local event"));
                    }
                    try {
                        fsyncDirectory(events);
                        writeHead(root, checkpoint(existing), NicotineTrackerLedger::atomicReplace);
                    } catch (IOException rollbackFailure) {
                        failure.addSuppressed(rollbackFailure);
                    }
                    throw failure;
                }
            } finally {
                if (pending.exists() && !pending.delete()) {
                    throw new IOException("failed to remove local pending event");
                }
            }
            return new SaveResult(true, order, eventId, eventDigest);
        }
    }

    private static String uniqueEventId(Existing[] existing, IdSource ids) throws IOException {
        Set<String> used = new HashSet<>();
        for (Existing event : existing) used.add(event.eventId);
        for (int attempt = 0; attempt < MAX_EVENT_ID_ATTEMPTS; attempt++) {
            String candidate = ids.eventId();
            if (!EVENT_ID.matcher(String.valueOf(candidate)).matches()) {
                throw new IllegalArgumentException("invalid random event id");
            }
            if (!used.contains(candidate)) return candidate;
        }
        throw new IOException("random event id collision retry limit reached");
    }

    private static Existing[] scan(
            File root, File events, boolean allowSingleEventHeadRecovery) throws IOException {
        File[] files = events.listFiles();
        if (files == null) throw new IOException("app-private event directory unreadable");
        for (File file : files) {
            if (!file.isFile() || !EVENT_FILE.matcher(file.getName()).matches()) {
                throw new IOException(
                        "unexpected entry in immutable local events directory: "
                                + file.getName());
            }
        }
        Arrays.sort(files, Comparator.comparing(File::getName));
        Existing[] result = new Existing[files.length];
        Set<String> eventIds = new HashSet<>();
        long expectedOrder = 1L;
        String expectedPreviousDigest = GENESIS_DIGEST;
        for (int index = 0; index < files.length; index++) {
            File file = files[index];
            if (file.length() <= 0L || file.length() > MAX_EVENT_BYTES) {
                throw new IOException("invalid immutable local event length");
            }
            Matcher filename = EVENT_FILE.matcher(file.getName());
            if (!filename.matches()) throw new IOException("invalid immutable event filename");
            long filenameOrder;
            try {
                filenameOrder = Long.parseLong(filename.group(1));
            } catch (NumberFormatException invalidOrder) {
                throw new IOException("invalid immutable event order", invalidOrder);
            }
            String filenameEventId = filename.group(2);
            if (filenameOrder != expectedOrder) {
                throw new IOException("local monotonic event order has a deletion or gap");
            }

            String stored = new String(
                    Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
            if (!stored.endsWith("\n") || stored.length() < 2) {
                throw new IOException("truncated immutable local event");
            }
            String body = stored.substring(0, stored.length() - 1);
            if (body.indexOf('\n') >= 0 || body.indexOf('\r') >= 0) {
                throw new IOException("invalid immutable local event framing");
            }
            ParsedEvent event = parseEvent(body);
            validateEvent(
                    event,
                    body,
                    filenameOrder,
                    filenameEventId,
                    expectedPreviousDigest);
            if (!eventIds.add(event.eventId)) {
                throw new IOException("duplicate immutable local event id");
            }
            result[index] = new Existing(
                    event.monotonicOrder,
                    event.eventId,
                    event.idempotencyKey,
                    event.requestDigest,
                    event.eventDigest);
            expectedPreviousDigest = event.eventDigest;
            expectedOrder = Math.addExact(expectedOrder, 1L);
        }
        verifyHead(root, result, allowSingleEventHeadRecovery);
        return result;
    }

    private static void validateEvent(
            ParsedEvent event,
            String body,
            long filenameOrder,
            String filenameEventId,
            String expectedPreviousDigest) throws IOException {
        if (!EVENT_SCHEMA.equals(event.schema) || !SOURCE_LOCAL.equals(event.source)) {
            throw new IOException("invalid immutable local event identity");
        }
        if (!EVENT_ID.matcher(event.eventId).matches()
                || !event.eventId.equals(filenameEventId)
                || event.monotonicOrder != filenameOrder) {
            throw new IOException("immutable local event filename mismatch");
        }
        if (!IDEMPOTENCY.matcher(event.idempotencyKey).matches()
                || !DIGEST.matcher(event.requestDigest).matches()
                || !DIGEST.matcher(event.eventDigest).matches()
                || !DIGEST.matcher(event.previousEventDigest).matches()) {
            throw new IOException("invalid immutable local event cryptographic field");
        }
        if (!expectedPreviousDigest.equals(event.previousEventDigest)) {
            throw new IOException("immutable local event digest chain mismatch");
        }
        if (event.wallTimeEpochMs < 0L || event.monotonicNanos < 0L
                || event.wallTimeZone.isEmpty() || event.wallTimeZone.length() > 80
                || event.note.length() > NicotineTrackerContract.MAX_NOTE_CHARS) {
            throw new IOException("invalid immutable local event value");
        }
        NicotineTrackerContract.ParseResult allowed = NicotineTrackerContract.parse(
                "/track " + event.kind + " " + event.value);
        if (allowed.state != NicotineTrackerContract.State.VALID
                || allowed.draft == null
                || !event.kind.equals(allowed.draft.kind.wireName)
                || !event.value.equals(allowed.draft.value)) {
            throw new IOException("invalid immutable local event kind or value");
        }
        String expectedRequestDigest = digest(
                "request-v1",
                event.kind,
                event.value,
                event.note,
                event.idempotencyKey,
                SOURCE_LOCAL);
        if (!expectedRequestDigest.equals(event.requestDigest)) {
            throw new IOException("immutable local request digest mismatch");
        }
        String expectedEventDigest = digest(
                EVENT_SCHEMA,
                event.eventId,
                Long.toString(event.monotonicOrder),
                event.previousEventDigest,
                Long.toString(event.wallTimeEpochMs),
                event.wallTimeZone,
                Long.toString(event.monotonicNanos),
                SOURCE_LOCAL,
                event.kind,
                event.value,
                event.note,
                event.idempotencyKey,
                event.requestDigest);
        if (!expectedEventDigest.equals(event.eventDigest)) {
            throw new IOException("immutable local event digest mismatch");
        }
        String canonical = eventJson(
                event.eventId,
                event.monotonicOrder,
                event.previousEventDigest,
                event.wallTimeEpochMs,
                event.wallTimeZone,
                event.monotonicNanos,
                event.kind,
                event.value,
                event.note,
                event.idempotencyKey,
                event.requestDigest,
                event.eventDigest);
        if (!canonical.equals(body)) {
            throw new IOException("immutable local event is not canonical");
        }
    }

    private static ParsedEvent parseEvent(String body) throws IOException {
        JsonCursor cursor = new JsonCursor(body);
        ParsedEvent event = new ParsedEvent();
        cursor.expect('{');
        event.schema = cursor.stringField("schema");
        cursor.expect(',');
        event.eventId = cursor.stringField("eventId");
        cursor.expect(',');
        event.monotonicOrder = cursor.longField("monotonicOrder");
        cursor.expect(',');
        event.previousEventDigest = cursor.stringField("previousEventDigest");
        cursor.expect(',');
        event.wallTimeEpochMs = cursor.longField("wallTimeEpochMs");
        cursor.expect(',');
        event.wallTimeZone = cursor.stringField("wallTimeZone");
        cursor.expect(',');
        event.monotonicNanos = cursor.longField("monotonicNanos");
        cursor.expect(',');
        event.source = cursor.stringField("source");
        cursor.expect(',');
        event.kind = cursor.stringField("kind");
        cursor.expect(',');
        event.value = cursor.stringField("value");
        cursor.expect(',');
        event.note = cursor.stringField("note");
        cursor.expect(',');
        event.idempotencyKey = cursor.stringField("idempotencyKey");
        cursor.expect(',');
        event.requestDigest = cursor.stringField("requestDigest");
        cursor.expect(',');
        event.eventDigest = cursor.stringField("eventDigest");
        cursor.expect('}');
        cursor.requireEnd();
        return event;
    }

    private static void verifyHead(
            File root,
            Existing[] events,
            boolean allowSingleEventRecovery) throws IOException {
        File headFile = new File(root, HEAD_FILE_NAME);
        if (!headFile.exists()) {
            if (events.length != 0 || !allowSingleEventRecovery) {
                throw new IOException("durable local ledger head checkpoint missing");
            }
            writeHead(root, checkpoint(events), NicotineTrackerLedger::atomicReplace);
        }
        HeadCheckpoint head = readHead(headFile);
        if (headMatchesPrefix(head, events, events.length)) return;
        if (allowSingleEventRecovery
                && head.eventCount >= 0L
                && head.eventCount + 1L == events.length
                && headMatchesPrefix(head, events, (int) head.eventCount)) {
            HeadCheckpoint recovered = checkpoint(events);
            writeHead(root, recovered, NicotineTrackerLedger::atomicReplace);
            HeadCheckpoint verified = readHead(headFile);
            if (headMatchesPrefix(verified, events, events.length)) return;
            throw new IOException("durable local ledger head recovery postcondition failed");
        }
        throw new IOException("durable local ledger head does not match immutable events");
    }

    private static boolean headMatchesPrefix(
            HeadCheckpoint head, Existing[] events, int count) {
        if (count < 0 || count > events.length
                || head.eventCount != count
                || head.lastMonotonicOrder != count
                || !HEAD_SCHEMA.equals(head.schema)) {
            return false;
        }
        if (count == 0) {
            return head.lastEventId.isEmpty()
                    && GENESIS_DIGEST.equals(head.lastEventDigest)
                    && GENESIS_DIGEST.equals(head.chainHeadDigest);
        }
        Existing last = events[count - 1];
        return last.monotonicOrder == count
                && last.eventId.equals(head.lastEventId)
                && last.eventDigest.equals(head.lastEventDigest)
                && last.eventDigest.equals(head.chainHeadDigest);
    }

    private static HeadCheckpoint checkpoint(Existing[] events) {
        if (events.length == 0) {
            return checkpoint(0L, 0L, "", GENESIS_DIGEST);
        }
        Existing last = events[events.length - 1];
        return checkpoint(
                events.length,
                last.monotonicOrder,
                last.eventId,
                last.eventDigest);
    }

    private static HeadCheckpoint checkpoint(
            long count, long order, String eventId, String eventDigest) {
        HeadCheckpoint head = new HeadCheckpoint();
        head.schema = HEAD_SCHEMA;
        head.eventCount = count;
        head.lastMonotonicOrder = order;
        head.lastEventId = eventId;
        head.lastEventDigest = eventDigest;
        head.chainHeadDigest = eventDigest;
        return head;
    }

    private static HeadCheckpoint readHead(File headFile) throws IOException {
        if (!headFile.isFile() || headFile.length() <= 0L || headFile.length() > 2048L) {
            throw new IOException("invalid durable local ledger head length");
        }
        String stored = new String(
                Files.readAllBytes(headFile.toPath()), StandardCharsets.UTF_8);
        if (!stored.endsWith("\n") || stored.length() < 2) {
            throw new IOException("truncated durable local ledger head");
        }
        String body = stored.substring(0, stored.length() - 1);
        try {
            JsonCursor cursor = new JsonCursor(body);
            HeadCheckpoint head = new HeadCheckpoint();
            cursor.expect('{');
            head.schema = cursor.stringField("schema");
            cursor.expect(',');
            head.eventCount = cursor.longField("eventCount");
            cursor.expect(',');
            head.lastMonotonicOrder = cursor.longField("lastMonotonicOrder");
            cursor.expect(',');
            head.lastEventId = cursor.stringField("lastEventId");
            cursor.expect(',');
            head.lastEventDigest = cursor.stringField("lastEventDigest");
            cursor.expect(',');
            head.chainHeadDigest = cursor.stringField("chainHeadDigest");
            cursor.expect('}');
            cursor.requireEnd();
            if (!HEAD_SCHEMA.equals(head.schema)
                    || head.eventCount < 0L
                    || head.lastMonotonicOrder < 0L
                    || head.eventCount != head.lastMonotonicOrder
                    || !DIGEST.matcher(head.lastEventDigest).matches()
                    || !DIGEST.matcher(head.chainHeadDigest).matches()
                    || (head.eventCount == 0L
                            ? !head.lastEventId.isEmpty()
                            : !EVENT_ID.matcher(head.lastEventId).matches())) {
                throw new IOException("invalid durable local ledger head value");
            }
            if (!headJson(head).equals(body)) {
                throw new IOException("durable local ledger head is not canonical");
            }
            return head;
        } catch (IOException invalid) {
            throw new IOException("corrupt durable local ledger head", invalid);
        }
    }

    private static void writeHead(
            File root, HeadCheckpoint head, AtomicCommit headCommit) throws IOException {
        File destination = new File(root, HEAD_FILE_NAME);
        File pending = new File(root, ".head-pending-" + randomHex(16));
        byte[] bytes = (headJson(head) + "\n").getBytes(StandardCharsets.UTF_8);
        try {
            try (FileOutputStream output = new FileOutputStream(pending, false)) {
                output.write(bytes);
                output.getFD().sync();
            }
            headCommit.commit(pending, destination);
            if (!destination.isFile()) {
                throw new IOException("atomic durable local ledger head commit missing");
            }
            fsyncDirectory(root);
            HeadCheckpoint verified = readHead(destination);
            if (!headMatchesCheckpoint(head, verified)) {
                throw new IOException("atomic durable local ledger head postcondition failed");
            }
        } finally {
            if (pending.exists() && !pending.delete()) {
                throw new IOException("failed to remove local head pending file");
            }
        }
    }

    private static boolean headMatchesCheckpoint(
            HeadCheckpoint expected, HeadCheckpoint actual) {
        return expected.eventCount == actual.eventCount
                && expected.lastMonotonicOrder == actual.lastMonotonicOrder
                && expected.lastEventId.equals(actual.lastEventId)
                && expected.lastEventDigest.equals(actual.lastEventDigest)
                && expected.chainHeadDigest.equals(actual.chainHeadDigest);
    }

    private static String headJson(HeadCheckpoint head) {
        return "{"
                + "\"schema\":\"" + HEAD_SCHEMA + "\","
                + "\"eventCount\":" + head.eventCount + ","
                + "\"lastMonotonicOrder\":" + head.lastMonotonicOrder + ","
                + "\"lastEventId\":\"" + head.lastEventId + "\","
                + "\"lastEventDigest\":\"" + head.lastEventDigest + "\","
                + "\"chainHeadDigest\":\"" + head.chainHeadDigest + "\""
                + "}";
    }

    private static final class JsonCursor {
        private final String value;
        private int index;

        JsonCursor(String value) {
            this.value = value;
        }

        String stringField(String expectedName) throws IOException {
            String actualName = readString();
            if (!expectedName.equals(actualName)) {
                throw new IOException("unexpected immutable local event field");
            }
            expect(':');
            return readString();
        }

        long longField(String expectedName) throws IOException {
            String actualName = readString();
            if (!expectedName.equals(actualName)) {
                throw new IOException("unexpected immutable local event field");
            }
            expect(':');
            int start = index;
            if (index < value.length() && value.charAt(index) == '-') index++;
            int digits = index;
            while (index < value.length()
                    && value.charAt(index) >= '0'
                    && value.charAt(index) <= '9') {
                index++;
            }
            if (digits == index) throw new IOException("immutable local event number missing");
            try {
                return Long.parseLong(value.substring(start, index));
            } catch (NumberFormatException invalidNumber) {
                throw new IOException("immutable local event number invalid", invalidNumber);
            }
        }

        String readString() throws IOException {
            expect('"');
            StringBuilder decoded = new StringBuilder();
            while (index < value.length()) {
                char character = value.charAt(index++);
                if (character == '"') return decoded.toString();
                if (character < 0x20) {
                    throw new IOException("unescaped control in immutable local event");
                }
                if (character != '\\') {
                    decoded.append(character);
                    continue;
                }
                if (index >= value.length()) {
                    throw new IOException("truncated immutable local event escape");
                }
                char escape = value.charAt(index++);
                switch (escape) {
                    case '"': decoded.append('"'); break;
                    case '\\': decoded.append('\\'); break;
                    case '/': decoded.append('/'); break;
                    case 'b': decoded.append('\b'); break;
                    case 'f': decoded.append('\f'); break;
                    case 'n': decoded.append('\n'); break;
                    case 'r': decoded.append('\r'); break;
                    case 't': decoded.append('\t'); break;
                    case 'u':
                        if (index + 4 > value.length()) {
                            throw new IOException("truncated immutable local event unicode escape");
                        }
                        try {
                            decoded.append((char) Integer.parseInt(
                                    value.substring(index, index + 4), 16));
                        } catch (NumberFormatException invalidEscape) {
                            throw new IOException(
                                    "invalid immutable local event unicode escape",
                                    invalidEscape);
                        }
                        index += 4;
                        break;
                    default:
                        throw new IOException("invalid immutable local event escape");
                }
            }
            throw new IOException("truncated immutable local event string");
        }

        void expect(char expected) throws IOException {
            if (index >= value.length() || value.charAt(index) != expected) {
                throw new IOException("invalid immutable local event syntax");
            }
            index++;
        }

        void requireEnd() throws IOException {
            if (index != value.length()) {
                throw new IOException("unexpected immutable local event suffix");
            }
        }
    }

    private static void cleanupPending(File root, File events) throws IOException {
        cleanupPendingDirectory(events, ".pending-", EVENT_PENDING_FILE);
        cleanupPendingDirectory(root, ".head-pending-", HEAD_PENDING_FILE);
    }

    private static void cleanupPendingDirectory(
            File directory, String prefix, Pattern allowedName) throws IOException {
        File[] entries = directory.listFiles();
        if (entries == null) throw new IOException("app-private tracker directory unreadable");
        int count = 0;
        boolean changed = false;
        for (File entry : entries) {
            if (!entry.getName().startsWith(prefix)) continue;
            count++;
            if (count > MAX_PENDING_FILES) {
                throw new IOException("local pending cleanup bound exceeded");
            }
            if (!entry.isFile() || !allowedName.matcher(entry.getName()).matches()) {
                throw new IOException("invalid local pending entry");
            }
            if (!entry.delete()) throw new IOException("stale local pending file cannot be removed");
            changed = true;
        }
        if (changed) fsyncDirectory(directory);
    }

    private static void fsyncDirectory(File directory) throws IOException {
        try (FileChannel channel = FileChannel.open(
                directory.toPath(), StandardOpenOption.READ)) {
            channel.force(true);
        }
    }

    private static void atomicMove(File pending, File destination) throws IOException {
        Files.move(
                pending.toPath(),
                destination.toPath(),
                StandardCopyOption.ATOMIC_MOVE);
    }

    private static void atomicReplace(File pending, File destination) throws IOException {
        Files.move(
                pending.toPath(),
                destination.toPath(),
                StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING);
    }

    private static String requestDigest(
            NicotineTrackerContract.Draft draft,
            String note,
            String idempotencyKey) {
        return digest(
                "request-v1",
                draft.kind.wireName,
                draft.value,
                note,
                idempotencyKey,
                SOURCE_LOCAL);
    }

    private static String eventDigest(
            String eventId,
            long order,
            String previousEventDigest,
            long wallTimeMillis,
            String zone,
            long monotonicNanos,
            NicotineTrackerContract.Draft draft,
            String note,
            String idempotencyKey,
            String requestDigest) {
        return digest(
                EVENT_SCHEMA,
                eventId,
                Long.toString(order),
                previousEventDigest,
                Long.toString(wallTimeMillis),
                zone,
                Long.toString(monotonicNanos),
                SOURCE_LOCAL,
                draft.kind.wireName,
                draft.value,
                note,
                idempotencyKey,
                requestDigest);
    }

    private static String eventJson(
            String eventId,
            long order,
            String previousEventDigest,
            long wallTimeMillis,
            String zone,
            long monotonicNanos,
            String kind,
            String value,
            String note,
            String idempotencyKey,
            String requestDigest,
            String eventDigest) {
        return "{"
                + "\"schema\":\"" + EVENT_SCHEMA + "\","
                + "\"eventId\":\"" + eventId + "\","
                + "\"monotonicOrder\":" + order + ","
                + "\"previousEventDigest\":\"" + previousEventDigest + "\","
                + "\"wallTimeEpochMs\":" + wallTimeMillis + ","
                + "\"wallTimeZone\":\"" + jsonEscape(zone) + "\","
                + "\"monotonicNanos\":" + monotonicNanos + ","
                + "\"source\":\"" + SOURCE_LOCAL + "\","
                + "\"kind\":\"" + kind + "\","
                + "\"value\":\"" + jsonEscape(value) + "\","
                + "\"note\":\"" + jsonEscape(note) + "\","
                + "\"idempotencyKey\":\"" + idempotencyKey + "\","
                + "\"requestDigest\":\"" + requestDigest + "\","
                + "\"eventDigest\":\"" + eventDigest + "\""
                + "}";
    }

    private static String jsonEscape(String value) {
        StringBuilder out = new StringBuilder(value.length() + 16);
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\b': out.append("\\b"); break;
                case '\f': out.append("\\f"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (character < 0x20) {
                        out.append(String.format(Locale.ROOT, "\\u%04x", (int) character));
                    } else {
                        out.append(character);
                    }
            }
        }
        return out.toString();
    }

    private static String digest(String... fields) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (String field : fields) {
                byte[] encoded = String.valueOf(field).getBytes(StandardCharsets.UTF_8);
                digest.update(ByteBuffer.allocate(4).putInt(encoded.length).array());
                digest.update(encoded);
            }
            return hex(digest.digest());
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 unavailable", impossible);
        }
    }

    private static String randomHex(int bytes) {
        byte[] value = new byte[bytes];
        SECURE_RANDOM.nextBytes(value);
        return hex(value);
    }

    private static String hex(byte[] value) {
        StringBuilder out = new StringBuilder(value.length * 2);
        for (byte item : value) {
            out.append(String.format(Locale.ROOT, "%02x", item & 0xff));
        }
        return out.toString();
    }
}
