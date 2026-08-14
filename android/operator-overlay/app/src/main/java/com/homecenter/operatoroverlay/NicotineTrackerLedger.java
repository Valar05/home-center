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
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * App-private, append-only event ledger.
 *
 * Each event is a separate immutable file committed by an atomic same-directory
 * move. There is no network, provider, exported component, or worker entrypoint.
 */
final class NicotineTrackerLedger {
    static final String DIRECTORY_NAME = "nicotine-tracker-v1";
    private static final String EVENT_SCHEMA = "adam-nicotine-tracker-event-v1";
    private static final String SOURCE_LOCAL = "local";
    private static final Pattern IDEMPOTENCY =
            Pattern.compile("^idem_[a-f0-9]{32}$");
    private static final Pattern EVENT_ID =
            Pattern.compile("^evt_[a-f0-9]{32}$");
    private static final Pattern EVENT_FILE =
            Pattern.compile("^(\\d{20})-(evt_[a-f0-9]{32})\\.json$");
    private static final Pattern JSON_IDEMPOTENCY =
            Pattern.compile("\\\"idempotencyKey\\\":\\\"(idem_[a-f0-9]{32})\\\"");
    private static final Pattern JSON_REQUEST_DIGEST =
            Pattern.compile("\\\"requestDigest\\\":\\\"([a-f0-9]{64})\\\"");
    private static final Pattern JSON_EVENT_DIGEST =
            Pattern.compile("\\\"eventDigest\\\":\\\"([a-f0-9]{64})\\\"");
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();
    private static final int MAX_EVENT_BYTES = 8192;

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
        if (appFilesDirectory == null || draft == null || draft.kind == null || clock == null
                || ids == null || atomicCommit == null) {
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
        String requestDigest = digest(
                "request-v1",
                draft.kind.wireName,
                draft.value,
                cleanNote,
                idempotencyKey,
                SOURCE_LOCAL);

        try (RandomAccessFile lockAccess = new RandomAccessFile(lockFile, "rw");
                FileChannel lockChannel = lockAccess.getChannel();
                FileLock ignored = lockChannel.lock()) {
            cleanupPending(events);
            Existing[] existing = scan(events);
            long maxOrder = 0L;
            for (Existing event : existing) {
                maxOrder = Math.max(maxOrder, event.monotonicOrder);
                if (!idempotencyKey.equals(event.idempotencyKey)) continue;
                if (!requestDigest.equals(event.requestDigest)) {
                    throw new IllegalStateException(
                            "idempotency key already belongs to a different local draft");
                }
                return new SaveResult(
                        false, event.monotonicOrder, event.eventId, event.eventDigest);
            }

            long order = Math.addExact(maxOrder, 1L);
            String eventId = ids.eventId();
            if (!EVENT_ID.matcher(String.valueOf(eventId)).matches()) {
                throw new IllegalArgumentException("invalid random event id");
            }
            long wallTimeMillis = clock.wallTimeMillis();
            long monotonicNanos = clock.monotonicNanos();
            String eventDigest = digest(
                    EVENT_SCHEMA,
                    eventId,
                    Long.toString(order),
                    Long.toString(wallTimeMillis),
                    zone,
                    Long.toString(monotonicNanos),
                    SOURCE_LOCAL,
                    draft.kind.wireName,
                    draft.value,
                    cleanNote,
                    idempotencyKey,
                    requestDigest);
            String record = eventJson(
                    eventId,
                    order,
                    wallTimeMillis,
                    zone,
                    monotonicNanos,
                    draft,
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
                throw new IllegalStateException("random event id collision");
            }
            File pending = new File(events, ".pending-" + randomHex(16));
            try {
                try (FileOutputStream output = new FileOutputStream(pending, false)) {
                    output.write(bytes);
                    output.getFD().sync();
                }
                atomicCommit.commit(pending, destination);
                if (!destination.isFile()) {
                    throw new IOException("atomic local event commit did not materialize");
                }
            } finally {
                if (pending.exists() && !pending.delete()) {
                    pending.deleteOnExit();
                }
            }
            return new SaveResult(true, order, eventId, eventDigest);
        }
    }

    private static Existing[] scan(File events) throws IOException {
        File[] files = events.listFiles((directory, name) -> EVENT_FILE.matcher(name).matches());
        if (files == null) throw new IOException("app-private event directory unreadable");
        Arrays.sort(files, Comparator.comparing(File::getName));
        Existing[] result = new Existing[files.length];
        long previousOrder = 0L;
        for (int index = 0; index < files.length; index++) {
            File file = files[index];
            if (file.length() <= 0L || file.length() > MAX_EVENT_BYTES) {
                throw new IOException("invalid immutable local event length");
            }
            String name = file.getName();
            Matcher filename = EVENT_FILE.matcher(name);
            if (!filename.matches()) throw new IOException("invalid immutable event filename");
            long order = Long.parseLong(filename.group(1));
            String eventId = filename.group(2);
            if (order <= previousOrder) {
                throw new IOException("local monotonic event order is not strictly increasing");
            }
            previousOrder = order;
            String json = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
            if (!json.endsWith("\n")
                    || !json.contains("\"schema\":\"" + EVENT_SCHEMA + "\"")
                    || !json.contains("\"source\":\"" + SOURCE_LOCAL + "\"")) {
                throw new IOException("invalid immutable local event");
            }
            String idempotencyKey = extract(JSON_IDEMPOTENCY, json);
            String requestDigest = extract(JSON_REQUEST_DIGEST, json);
            String eventDigest = extract(JSON_EVENT_DIGEST, json);
            if (!json.contains("\"eventId\":\"" + eventId + "\"")
                    || !json.contains("\"monotonicOrder\":" + order + ",")) {
                throw new IOException("local event identity mismatch");
            }
            result[index] = new Existing(
                    order, eventId, idempotencyKey, requestDigest, eventDigest);
        }
        return result;
    }

    private static void cleanupPending(File events) throws IOException {
        File[] pending = events.listFiles(
                (directory, name) -> name.startsWith(".pending-"));
        if (pending == null) throw new IOException("app-private event directory unreadable");
        for (File file : pending) {
            if (!file.delete()) throw new IOException("stale local pending event cannot be removed");
        }
    }

    private static String extract(Pattern pattern, String json) throws IOException {
        Matcher matcher = pattern.matcher(json);
        if (!matcher.find()) throw new IOException("immutable local event field missing");
        return matcher.group(1);
    }

    private static String eventJson(
            String eventId,
            long order,
            long wallTimeMillis,
            String zone,
            long monotonicNanos,
            NicotineTrackerContract.Draft draft,
            String note,
            String idempotencyKey,
            String requestDigest,
            String eventDigest) {
        return "{"
                + "\"schema\":\"" + EVENT_SCHEMA + "\","
                + "\"eventId\":\"" + eventId + "\","
                + "\"monotonicOrder\":" + order + ","
                + "\"wallTimeEpochMs\":" + wallTimeMillis + ","
                + "\"wallTimeZone\":\"" + jsonEscape(zone) + "\","
                + "\"monotonicNanos\":" + monotonicNanos + ","
                + "\"source\":\"" + SOURCE_LOCAL + "\","
                + "\"kind\":\"" + draft.kind.wireName + "\","
                + "\"value\":\"" + jsonEscape(draft.value) + "\","
                + "\"note\":\"" + jsonEscape(note) + "\","
                + "\"idempotencyKey\":\"" + idempotencyKey + "\","
                + "\"requestDigest\":\"" + requestDigest + "\","
                + "\"eventDigest\":\"" + eventDigest + "\""
                + "}";
    }

    private static String jsonEscape(String value) {
        StringBuilder out = new StringBuilder(value.length() + 16);
        for (int index = 0; index < value.length(); index++) {
            char ch = value.charAt(index);
            switch (ch) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\b': out.append("\\b"); break;
                case '\f': out.append("\\f"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (ch < 0x20) {
                        out.append(String.format(Locale.ROOT, "\\u%04x", (int) ch));
                    } else {
                        out.append(ch);
                    }
            }
        }
        return out.toString();
    }

    private static String digest(String... fields) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (String field : fields) {
                byte[] value = String.valueOf(field).getBytes(StandardCharsets.UTF_8);
                digest.update(ByteBuffer.allocate(4).putInt(value.length).array());
                digest.update(value);
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
