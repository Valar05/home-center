package com.dclar.homecenter;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;

final class GoogleDocAudioLibrary {
    static final int DEFAULT_SAMPLE_RATE = 24000;
    private static final String PROVIDER = "ElevenLabs";
    private static final String VOICE = "Brian";

    private final File root;
    private final File indexFile;

    GoogleDocAudioLibrary(Context context) {
        File base = context == null ? null : context.getExternalFilesDir(null);
        if (base == null && context != null) {
            base = context.getFilesDir();
        }
        root = new File(base, "google-doc-audio");
        indexFile = new File(root, "index.json");
    }

    Entry ingest(String fileId, String title, String modifiedTime, String textHash, int charCount, List<String> sections) {
        File dir = new File(new File(root, safePart(fileId == null || fileId.trim().isEmpty() ? "unknown-doc" : fileId.trim())), safePart(textHash));
        Entry entry = new Entry(dir, fileId, title, modifiedTime, textHash, charCount, sections == null ? 0 : sections.size());
        entry.ensureManifest(sections);
        updateIndex(entry);
        return entry;
    }

    private void updateIndex(Entry entry) {
        try {
            if (!root.exists()) root.mkdirs();
            JSONArray docs = new JSONArray();
            if (indexFile.exists()) {
                try (FileInputStream input = new FileInputStream(indexFile)) {
                    JSONObject existing = new JSONObject(new String(readAll(input), StandardCharsets.UTF_8));
                    JSONArray prior = existing.optJSONArray("documents");
                    if (prior != null) {
                        for (int i = 0; i < prior.length(); i++) {
                            JSONObject item = prior.optJSONObject(i);
                            if (item != null && !(entry.fileId.equals(item.optString("fileId", "")) && entry.textHash.equals(item.optString("textHash", "")))) {
                                docs.put(item);
                            }
                        }
                    }
                } catch (Exception ignored) {
                }
            }
            docs.put(entry.toIndexJson());
            writeTextAtomic(indexFile, new JSONObject()
                    .put("type", "google_doc_audio_index")
                    .put("updatedAt", now())
                    .put("documents", docs)
                    .toString(2));
        } catch (Exception ex) {
            LocalLog.warn("doc_audio", "index_update_failed " + safe(ex.getMessage()));
        }
    }

    static void writeWavHeader(RandomAccessFile output, int sampleRate, long pcmBytes) throws IOException {
        output.seek(0L);
        long dataSize = Math.max(0L, pcmBytes);
        output.write(new byte[]{'R','I','F','F'});
        writeLeInt(output, 36L + dataSize);
        output.write(new byte[]{'W','A','V','E'});
        output.write(new byte[]{'f','m','t',' '});
        writeLeInt(output, 16L);
        writeLeShort(output, 1);
        writeLeShort(output, 1);
        writeLeInt(output, sampleRate);
        writeLeInt(output, sampleRate * 2L);
        writeLeShort(output, 2);
        writeLeShort(output, 16);
        output.write(new byte[]{'d','a','t','a'});
        writeLeInt(output, dataSize);
    }

    private static void writeLeInt(RandomAccessFile output, long value) throws IOException {
        output.write((int) (value & 0xff));
        output.write((int) ((value >> 8) & 0xff));
        output.write((int) ((value >> 16) & 0xff));
        output.write((int) ((value >> 24) & 0xff));
    }

    private static void writeLeShort(RandomAccessFile output, int value) throws IOException {
        output.write(value & 0xff);
        output.write((value >> 8) & 0xff);
    }

    private static byte[] readAll(FileInputStream input) throws IOException {
        byte[] buffer = new byte[8192];
        java.io.ByteArrayOutputStream output = new java.io.ByteArrayOutputStream();
        int read;
        while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
        return output.toByteArray();
    }

    private static void writeTextAtomic(File file, String text) throws IOException {
        File parent = file.getParentFile();
        if (parent != null && !parent.exists()) parent.mkdirs();
        File tmp = new File(parent, file.getName() + ".tmp");
        try (FileOutputStream output = new FileOutputStream(tmp, false)) {
            output.write((text == null ? "" : text).getBytes(StandardCharsets.UTF_8));
        }
        if (!tmp.renameTo(file)) throw new IOException("rename failed for " + file.getName());
    }

    private static String now() {
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(new Date());
    }

    private static String safePart(String value) {
        String clean = value == null ? "" : value.trim().replaceAll("[^A-Za-z0-9_.-]", "_");
        if (clean.isEmpty()) return "unknown";
        return clean.length() > 140 ? clean.substring(0, 140) : clean;
    }

    private static String safe(String value) {
        return value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').replaceAll("\\s+", " ").trim();
    }

    final class Entry {
        final File dir;
        final File manifestFile;
        final String fileId;
        final String title;
        final String modifiedTime;
        final String textHash;
        final int charCount;
        final int sectionCount;

        Entry(File dir, String fileId, String title, String modifiedTime, String textHash, int charCount, int sectionCount) {
            this.dir = dir;
            this.manifestFile = new File(dir, "manifest.json");
            this.fileId = fileId == null ? "" : fileId;
            this.title = title == null || title.trim().isEmpty() ? "Google Doc" : title.trim();
            this.modifiedTime = modifiedTime == null ? "" : modifiedTime;
            this.textHash = textHash == null ? "" : textHash;
            this.charCount = charCount;
            this.sectionCount = Math.max(1, sectionCount);
        }

        synchronized void ensureManifest(List<String> sectionsText) {
            try {
                if (!dir.exists()) dir.mkdirs();
                JSONObject old = readManifest();
                JSONArray sections = new JSONArray();
                int cursor = 0;
                for (int i = 0; i < sectionCount; i++) {
                    String text = sectionsText == null || i >= sectionsText.size() ? "" : sectionsText.get(i);
                    JSONObject prior = sectionAt(old.optJSONArray("sections"), i);
                    File audio = sectionFile(i);
                    String status = audio.exists() && audio.length() > 44L ? "downloaded" : prior.optString("audioStatus", "not_downloaded");
                    long pcmBytes = audio.exists() ? Math.max(0L, audio.length() - 44L) : prior.optLong("pcmBytes", 0L);
                    int start = cursor;
                    int end = cursor + text.length();
                    cursor = end + 1;
                    sections.put(new JSONObject()
                            .put("index", i)
                            .put("label", "section " + (i + 1))
                            .put("textStart", start)
                            .put("textEnd", end)
                            .put("preview", preview(text))
                            .put("audioStatus", status)
                            .put("audioPath", audio.getAbsolutePath())
                            .put("sampleRate", prior.optInt("sampleRate", DEFAULT_SAMPLE_RATE))
                            .put("pcmBytes", pcmBytes));
                }
                writeManifest(new JSONObject()
                        .put("type", "google_doc_audio_manifest")
                        .put("fileId", fileId)
                        .put("title", title)
                        .put("modifiedTime", modifiedTime)
                        .put("textHash", textHash)
                        .put("charCount", charCount)
                        .put("sectionCount", sectionCount)
                        .put("voiceProvider", PROVIDER)
                        .put("voiceName", VOICE)
                        .put("ingestedAt", old.optString("ingestedAt", now()))
                        .put("updatedAt", now())
                        .put("sample", old.optJSONObject("sample") == null ? new JSONObject()
                                .put("audioStatus", sampleFile().exists() && sampleFile().length() > 44L ? "downloaded" : "not_downloaded")
                                .put("audioPath", sampleFile().getAbsolutePath())
                                .put("sampleRate", DEFAULT_SAMPLE_RATE)
                                .put("pcmBytes", sampleFile().exists() ? Math.max(0L, sampleFile().length() - 44L) : 0L)
                                : old.optJSONObject("sample"))
                        .put("rendering", old.optBoolean("rendering", false))
                        .put("downloadedSections", downloadedCount(sections))
                        .put("sections", sections));
                LocalLog.info("doc_audio", "doc_audio_ingested fileId=" + fileId + " textHash=" + textHash + " sections=" + sectionCount);
            } catch (Exception ex) {
                LocalLog.warn("doc_audio", "manifest_write_failed " + safe(ex.getMessage()));
            }
        }

        synchronized JSONObject readManifest() {
            try {
                if (!manifestFile.exists()) return new JSONObject();
                try (FileInputStream input = new FileInputStream(manifestFile)) {
                    return new JSONObject(new String(readAll(input), StandardCharsets.UTF_8));
                }
            } catch (Exception ex) {
                return new JSONObject();
            }
        }

        boolean isDownloaded(int index) {
            File file = sectionFile(index);
            return file.exists() && file.length() > 44L;
        }

        File sectionFile(int index) {
            return new File(dir, String.format(Locale.US, "section-%04d.wav", index + 1));
        }

        File partFile(int index) {
            return new File(dir, String.format(Locale.US, "section-%04d.wav.part", index + 1));
        }

        File sampleFile() {
            return new File(dir, "sample.wav");
        }

        File samplePartFile() {
            return new File(dir, "sample.wav.part");
        }

        boolean isSampleDownloaded() {
            File file = sampleFile();
            return file.exists() && file.length() > 44L;
        }

        synchronized void markSampleDownloading() {
            markSample("downloading", 0L, DEFAULT_SAMPLE_RATE, "");
        }

        synchronized void markSampleDownloaded(long pcmBytes, int sampleRate) {
            markSample("downloaded", pcmBytes, sampleRate, "");
            LocalLog.info("doc_audio", "doc_audio_sample_downloaded fileId=" + fileId + " textHash=" + textHash + " pcmBytes=" + pcmBytes);
        }

        synchronized void markSampleFailed(String detail) {
            markSample("failed", 0L, DEFAULT_SAMPLE_RATE, detail);
        }

        private void markSample(String status, long pcmBytes, int sampleRate, String error) {
            try {
                JSONObject manifest = readManifest();
                JSONObject sample = manifest.optJSONObject("sample");
                if (sample == null) sample = new JSONObject();
                sample.put("audioStatus", status)
                        .put("audioPath", sampleFile().getAbsolutePath())
                        .put("sampleRate", sampleRate)
                        .put("pcmBytes", pcmBytes)
                        .put("updatedAt", now());
                if (error != null && !error.trim().isEmpty()) sample.put("error", safe(error));
                manifest.put("sample", sample).put("updatedAt", now());
                writeManifest(manifest);
            } catch (Exception ex) {
                LocalLog.warn("doc_audio", "sample_mark_failed " + safe(ex.getMessage()));
            }
        }

        synchronized void markRendering(boolean rendering) {
            try {
                JSONObject manifest = readManifest();
                manifest.put("rendering", rendering).put("updatedAt", now());
                writeManifest(manifest);
            } catch (Exception ex) {
                LocalLog.warn("doc_audio", "render_mark_failed " + safe(ex.getMessage()));
            }
        }

        synchronized void markRenderComplete() {
            try {
                JSONObject manifest = readManifest();
                manifest.put("rendering", false)
                        .put("renderedAt", now())
                        .put("updatedAt", now());
                writeManifest(manifest);
            } catch (Exception ex) {
                LocalLog.warn("doc_audio", "render_complete_mark_failed " + safe(ex.getMessage()));
            }
        }

        synchronized void markDownloading(int index) {
            mark(index, "downloading", 0L, DEFAULT_SAMPLE_RATE, "");
        }

        synchronized void markDownloaded(int index, long pcmBytes, int sampleRate) {
            mark(index, "downloaded", pcmBytes, sampleRate, "");
            LocalLog.info("doc_audio", "doc_audio_section_downloaded fileId=" + fileId + " textHash=" + textHash + " section=" + index + " pcmBytes=" + pcmBytes);
        }

        synchronized void markFailed(int index, String detail) {
            mark(index, "failed", 0L, DEFAULT_SAMPLE_RATE, detail);
        }

        private void mark(int index, String status, long pcmBytes, int sampleRate, String error) {
            try {
                JSONObject manifest = readManifest();
                JSONArray sections = manifest.optJSONArray("sections");
                if (sections == null) sections = new JSONArray();
                JSONObject section = sectionAt(sections, index);
                section.put("index", index)
                        .put("label", "section " + (index + 1))
                        .put("audioStatus", status)
                        .put("audioPath", sectionFile(index).getAbsolutePath())
                        .put("sampleRate", sampleRate)
                        .put("pcmBytes", pcmBytes)
                        .put("updatedAt", now());
                if (error != null && !error.trim().isEmpty()) section.put("error", safe(error));
                sections.put(index, section);
                manifest.put("sections", sections)
                        .put("downloadedSections", downloadedCount(sections))
                        .put("updatedAt", now());
                writeManifest(manifest);
            } catch (Exception ex) {
                LocalLog.warn("doc_audio", "section_mark_failed " + safe(ex.getMessage()));
            }
        }

        private void writeManifest(JSONObject manifest) throws Exception {
            writeTextAtomic(manifestFile, manifest.toString(2));
        }

        JSONObject toIndexJson() throws Exception {
            return new JSONObject()
                    .put("fileId", fileId)
                    .put("title", title)
                    .put("modifiedTime", modifiedTime)
                    .put("textHash", textHash)
                    .put("charCount", charCount)
                    .put("sectionCount", sectionCount)
                    .put("manifestPath", manifestFile.getAbsolutePath())
                    .put("updatedAt", now());
        }

        private JSONObject sectionAt(JSONArray sections, int index) {
            JSONObject section = sections == null ? null : sections.optJSONObject(index);
            return section == null ? new JSONObject() : section;
        }

        private int downloadedCount(JSONArray sections) {
            int count = 0;
            if (sections == null) return 0;
            for (int i = 0; i < sections.length(); i++) {
                JSONObject section = sections.optJSONObject(i);
                if (section != null && "downloaded".equals(section.optString("audioStatus", ""))) count += 1;
            }
            return count;
        }

        private String preview(String text) {
            String clean = text == null ? "" : text.replaceAll("\\s+", " ").trim();
            return clean.length() > 180 ? clean.substring(0, 180) + "..." : clean;
        }
    }
}
