package com.dclar.homecenter;

import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.SystemClock;
import android.provider.MediaStore;
import android.util.Base64;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;

final class PocketTtsWorkerBridge {
    static final String CONTRACT_VERSION = "pocket-tts-render-v3";
    static final String VOICE_PROFILE_ID = "vera-venice-close-mic-v1";
    interface CancelCheck { boolean cancelled(); }

    static final class Result {
        final File wav;
        final int sampleRate;
        final long pcmBytes;
        final String artifactSha256;
        final double realTimeFactor;

        Result(File wav, int sampleRate, long pcmBytes, String artifactSha256, double realTimeFactor) {
            this.wav = wav;
            this.sampleRate = sampleRate;
            this.pcmBytes = pcmBytes;
            this.artifactSha256 = artifactSha256;
            this.realTimeFactor = realTimeFactor;
        }
    }

    private static final String REQUEST_RELATIVE_PATH = Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/pocket-tts-requests/";
    private static final String RESULT_RELATIVE_PATH = Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/pocket-tts-results/";
    private static final String START_COMMAND = "sh /storage/emulated/0/Documents/GodotProjects/home-center/tools/home_center_read_aloud.sh start";
    private static final long TIMEOUT_MS = 180_000L;
    private static final long POLL_MS = 500L;

    private PocketTtsWorkerBridge() { }

    private static File publicResultFile(String requestId) {
        return new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                "HomeCenter/pocket-tts-results/" + safe(requestId) + ".wav");
    }

    static boolean hasCompletedOutput(Context context, String requestId) {
        try { return materializeAcceptedResult(context, safe(requestId)) != null; }
        catch (Exception ignored) { return false; }
    }

    private static Uri findOwnedUri(ContentResolver resolver, String relativePath, String displayName) {
        String[] projection = new String[] { MediaStore.MediaColumns._ID };
        String selection = MediaStore.MediaColumns.RELATIVE_PATH + "=? AND " + MediaStore.MediaColumns.DISPLAY_NAME + "=?";
        try (Cursor cursor = resolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI, projection, selection,
                new String[] { relativePath, displayName }, MediaStore.MediaColumns.DATE_ADDED + " DESC")) {
            if (cursor != null && cursor.moveToFirst()) {
                return ContentUris.withAppendedId(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cursor.getLong(0));
            }
        } catch (Exception ignored) { }
        return null;
    }

    private static void deleteOwnedRows(ContentResolver resolver, String relativePath, String displayName) {
        String selection = MediaStore.MediaColumns.RELATIVE_PATH + "=? AND " + MediaStore.MediaColumns.DISPLAY_NAME + "=?";
        try { resolver.delete(MediaStore.Downloads.EXTERNAL_CONTENT_URI, selection, new String[] { relativePath, displayName }); }
        catch (Exception ignored) { }
    }

    private static Uri createOwnedRow(ContentResolver resolver, String relativePath, String displayName, String mimeType) throws IOException {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, displayName);
        values.put(MediaStore.Downloads.MIME_TYPE, mimeType);
        values.put(MediaStore.Downloads.RELATIVE_PATH, relativePath);
        values.put(MediaStore.Downloads.IS_PENDING, 0);
        Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IOException("could not create app-owned Pocket TTS result slot");
        return uri;
    }

    private static void createResultSlots(Context context, String requestId) throws IOException {
        ContentResolver resolver = context.getApplicationContext().getContentResolver();
        String wavName = requestId + ".wav";
        String receiptName = requestId + ".json";
        deleteOwnedRows(resolver, RESULT_RELATIVE_PATH, wavName);
        deleteOwnedRows(resolver, RESULT_RELATIVE_PATH, receiptName);
        createOwnedRow(resolver, RESULT_RELATIVE_PATH, wavName, "audio/wav");
        createOwnedRow(resolver, RESULT_RELATIVE_PATH, receiptName, "application/json");
    }

    static void enqueue(Context context, String requestId, String text) throws IOException {
        String safeId = safe(requestId);
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            throw new IOException("Pocket TTS request queue requires Android 10 or newer");
        }
        createResultSlots(context, safeId);
        try {
            JSONObject request = new JSONObject()
                    .put("requestId", safeId)
                    .put("contractVersion", CONTRACT_VERSION)
                    .put("voiceProfileId", VOICE_PROFILE_ID)
                    .put("textBase64", Base64.encodeToString((text == null ? "" : text).getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP))
                    .put("output", publicResultFile(safeId).getAbsolutePath());
            ContentResolver resolver = context.getApplicationContext().getContentResolver();
            deleteOwnedRows(resolver, REQUEST_RELATIVE_PATH, safeId + ".json");
            ContentValues values = new ContentValues();
            values.put(MediaStore.Downloads.DISPLAY_NAME, safeId + ".json");
            values.put(MediaStore.Downloads.MIME_TYPE, "application/json");
            values.put(MediaStore.Downloads.RELATIVE_PATH, REQUEST_RELATIVE_PATH);
            values.put(MediaStore.Downloads.IS_PENDING, 1);
            Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
            if (uri == null) throw new IOException("could not create Pocket TTS request");
            try (OutputStream output = resolver.openOutputStream(uri, "w")) {
                if (output == null) throw new IOException("could not open Pocket TTS request");
                output.write((request.toString() + "\n").getBytes(StandardCharsets.UTF_8));
            }
            ContentValues ready = new ContentValues();
            ready.put(MediaStore.Downloads.IS_PENDING, 0);
            resolver.update(uri, ready, null, null);
        } catch (IOException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new IOException("could not queue Pocket TTS section: " + ex.getMessage(), ex);
        }
    }

    static Result await(Context context, String requestId, CancelCheck cancel) throws IOException {
        long deadline = SystemClock.elapsedRealtime() + TIMEOUT_MS;
        while (SystemClock.elapsedRealtime() < deadline) {
            if (cancel != null && cancel.cancelled()) throw new IOException("Pocket TTS render cancelled");
            JSONObject receipt = readReceipt(context, requestId);
            if (receipt != null && "failed".equals(receipt.optString("status"))) {
                throw new IOException("Pocket TTS worker failed: " + receipt.optString("error", "unknown worker error"));
            }
            Result accepted = materializeAcceptedResult(context, requestId);
            if (accepted != null) return accepted;
            SystemClock.sleep(POLL_MS);
        }
        throw new IOException("Pocket TTS worker timed out. Run: " + START_COMMAND);
    }

    static Result render(Context context, String requestId, String text, CancelCheck cancel) throws IOException {
        String safeId = safe(requestId);
        Result accepted = materializeAcceptedResult(context, safeId);
        if (accepted != null) return accepted;
        enqueue(context, safeId, text);
        return await(context, safeId, cancel);
    }

    private static JSONObject readReceipt(Context context, String requestId) {
        ContentResolver resolver = context.getApplicationContext().getContentResolver();
        Uri uri = findOwnedUri(resolver, RESULT_RELATIVE_PATH, safe(requestId) + ".json");
        if (uri == null) return null;
        try (InputStream input = resolver.openInputStream(uri)) {
            if (input == null) return null;
            byte[] bytes = readAll(input, 2_000_000);
            if (bytes.length == 0) return null;
            return new JSONObject(new String(bytes, StandardCharsets.UTF_8));
        } catch (Exception ignored) { return null; }
    }

    private static Result materializeAcceptedResult(Context context, String requestId) {
        String safeId = safe(requestId);
        ContentResolver resolver = context.getApplicationContext().getContentResolver();
        Uri wavUri = findOwnedUri(resolver, RESULT_RELATIVE_PATH, safeId + ".wav");
        Uri receiptUri = findOwnedUri(resolver, RESULT_RELATIVE_PATH, safeId + ".json");
        if (wavUri == null || receiptUri == null) return null;
        File dir = new File(context.getCacheDir(), "pocket-tts-results");
        if (!dir.exists() && !dir.mkdirs()) return null;
        File wav = new File(dir, safeId + ".wav");
        File receipt = new File(dir, safeId + ".json");
        try {
            copyOwnedUri(resolver, wavUri, wav);
            copyOwnedUri(resolver, receiptUri, receipt);
            return inspect(wav);
        } catch (Exception ignored) { return null; }
    }

    private static void copyOwnedUri(ContentResolver resolver, Uri uri, File target) throws IOException {
        File part = new File(target.getParentFile(), target.getName() + ".part");
        try (InputStream input = resolver.openInputStream(uri); FileOutputStream output = new FileOutputStream(part, false)) {
            if (input == null) throw new IOException("Pocket TTS result slot is unavailable");
            byte[] buffer = new byte[65536];
            int count;
            while ((count = input.read(buffer)) >= 0) if (count > 0) output.write(buffer, 0, count);
            output.getFD().sync();
        }
        Files.move(part.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
    }

    private static byte[] readAll(InputStream input, int maxBytes) throws IOException {
        java.io.ByteArrayOutputStream output = new java.io.ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int count;
        while ((count = input.read(buffer)) >= 0) {
            if (count == 0) continue;
            if (output.size() + count > maxBytes) throw new IOException("Pocket TTS receipt is too large");
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }

    private static Result inspect(File wav) throws IOException {
        try (RandomAccessFile in = new RandomAccessFile(wav, "r")) {
            if (in.length() <= 44L) throw new IOException("Pocket TTS WAV is empty");
            byte[] header = new byte[44];
            in.readFully(header);
            if (header[0] != 'R' || header[1] != 'I' || header[2] != 'F' || header[3] != 'F'
                    || header[8] != 'W' || header[9] != 'A' || header[10] != 'V' || header[11] != 'E') {
                throw new IOException("Pocket TTS WAV header is invalid");
            }
            int sampleRate = (header[24] & 255) | ((header[25] & 255) << 8)
                    | ((header[26] & 255) << 16) | ((header[27] & 255) << 24);
            File receiptFile = new File(wav.getParentFile(), wav.getName().replaceFirst("\\.wav$", ".json"));
            JSONObject receipt = new JSONObject(new String(Files.readAllBytes(receiptFile.toPath()), StandardCharsets.UTF_8));
            if (!"complete".equals(receipt.optString("status")) || !receipt.optBoolean("accepted", false)
                    || !CONTRACT_VERSION.equals(receipt.optString("contractVersion"))) {
                throw new IOException("Pocket TTS receipt is not accepted v3");
            }
            if (!VOICE_PROFILE_ID.equals(receipt.optString("voiceProfileId"))) {
                throw new IOException("Pocket TTS receipt has the wrong voice profile");
            }
            if (!"local".equals(receipt.optString("backend"))) {
                throw new IOException("Pocket TTS receipt is not local-only");
            }
            String artifactSha256 = sha256(wav);
            if (!artifactSha256.equalsIgnoreCase(receipt.optString("artifactSha256"))) {
                throw new IOException("Pocket TTS receipt hash does not match WAV");
            }
            return new Result(wav, sampleRate, in.length() - 44L, artifactSha256, receipt.optDouble("realTimeFactor", 0.0));
        } catch (IOException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new IOException("Pocket TTS receipt is invalid: " + ex.getMessage(), ex);
        }
    }

    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (FileInputStream input = new FileInputStream(file)) {
            byte[] buffer = new byte[65536];
            int count;
            while ((count = input.read(buffer)) >= 0) if (count > 0) digest.update(buffer, 0, count);
        }
        StringBuilder hex = new StringBuilder();
        for (byte value : digest.digest()) hex.append(String.format("%02x", value & 255));
        return hex.toString();
    }

    private static String safe(String value) {
        String clean = value == null ? "" : value.replaceAll("[^A-Za-z0-9_.-]+", "-").replaceAll("^-|-$", "");
        return clean.isEmpty() ? "section" : (clean.length() > 120 ? clean.substring(0, 120) : clean);
    }
}
