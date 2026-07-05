package com.dclar.homecenter;

import android.content.Context;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

final class LocalKnowledgeClient {
    private static final int MAX_APPEND_CHARS = 20000;
    private static final int MAX_READ_CHARS = 60000;
    private final File root;

    LocalKnowledgeClient(Context context) {
        root = new File(context.getFilesDir(), "home_center_knowledge");
        ensureSeedFiles();
    }

    JSONObject runTool(String toolName, JSONObject arguments) {
        if ("knowledge.read".equals(toolName)) return readTool(arguments);
        if ("knowledge.append".equals(toolName)) return appendTool(arguments);
        return toolError(toolName, "unknown_knowledge_tool", "No local knowledge tool is registered with that name.");
    }

    private JSONObject readTool(JSONObject arguments) {
        String fileName = canonicalFileName(arguments == null ? "" : arguments.optString("file", ""));
        if (fileName.isEmpty()) return toolError("knowledge.read", "invalid_file", "Use SKILLS.md, AGENTS.md, or MEMORY.md.");
        try {
            File file = knowledgeFile(fileName);
            String content = readFile(file);
            boolean truncated = content.length() > MAX_READ_CHARS;
            if (truncated) {
                content = content.substring(content.length() - MAX_READ_CHARS);
            }
            return baseResult("knowledge.read", true, "knowledge_read", "")
                    .put("file", fileName)
                    .put("path", file.getAbsolutePath())
                    .put("content", content)
                    .put("truncated", truncated);
        } catch (Exception ex) {
            return toolError("knowledge.read", "read_failed", safe(ex.getMessage()));
        }
    }

    private JSONObject appendTool(JSONObject arguments) {
        String fileName = canonicalFileName(arguments == null ? "" : arguments.optString("file", ""));
        if (fileName.isEmpty()) return toolError("knowledge.append", "invalid_file", "Use SKILLS.md, AGENTS.md, or MEMORY.md.");
        String title = clean(arguments == null ? "" : arguments.optString("title", ""), 160);
        String body = clean(arguments == null ? "" : arguments.optString("body", ""), MAX_APPEND_CHARS);
        if (body.trim().isEmpty()) return toolError("knowledge.append", "empty_body", "No knowledge body was provided.");
        if (looksSensitive(body)) return toolError("knowledge.append", "sensitive_content_rejected", "The note looks like it contains a token, key, password, or Authorization header.");
        try {
            File file = knowledgeFile(fileName);
            String entry = buildEntry(title, body);
            try (FileOutputStream out = new FileOutputStream(file, true)) {
                out.write(entry.getBytes(StandardCharsets.UTF_8));
            }
            return baseResult("knowledge.append", true, "knowledge_appended", "")
                    .put("file", fileName)
                    .put("path", file.getAbsolutePath())
                    .put("title", title)
                    .put("bodyPreview", body.length() > 2000 ? body.substring(0, 2000) : body)
                    .put("bytesWritten", entry.getBytes(StandardCharsets.UTF_8).length);
        } catch (Exception ex) {
            return toolError("knowledge.append", "append_failed", safe(ex.getMessage()));
        }
    }

    private void ensureSeedFiles() {
        if (!root.exists() && !root.mkdirs()) {
            LocalLog.warn("agent", "local_knowledge_root_unavailable " + root.getAbsolutePath());
            return;
        }
        seed("SKILLS.md", "# Home Center Skills\n\nDurable workflows and repeated procedures promoted by Home Center.\n");
        seed("AGENTS.md", "# Home Center Agent Instructions\n\nLocal steering notes for Home Center agent behavior.\n");
        seed("MEMORY.md", "# Home Center Memory\n\nDurable local memory notes, workarounds, and operational facts.\n");
    }

    private void seed(String name, String content) {
        try {
            File file = knowledgeFile(name);
            if (!file.exists()) {
                try (FileOutputStream out = new FileOutputStream(file)) {
                    out.write(content.getBytes(StandardCharsets.UTF_8));
                }
            }
        } catch (Exception ex) {
            LocalLog.warn("agent", "local_knowledge_seed_failed " + name + " " + safe(ex.getMessage()));
        }
    }

    private File knowledgeFile(String fileName) throws Exception {
        if (!root.exists() && !root.mkdirs()) throw new Exception("Could not create local knowledge directory.");
        File file = new File(root, canonicalFileName(fileName));
        String rootPath = root.getCanonicalPath();
        String filePath = file.getCanonicalPath();
        if (!filePath.startsWith(rootPath + File.separator)) throw new Exception("Invalid local knowledge path.");
        return file;
    }

    private String canonicalFileName(String input) {
        String clean = input == null ? "" : input.trim().toUpperCase(Locale.US);
        if ("SKILL.MD".equals(clean)) clean = "SKILLS.MD";
        if ("SKILLS.MD".equals(clean)) return "SKILLS.md";
        if ("AGENTS.MD".equals(clean) || "AGENT.MD".equals(clean)) return "AGENTS.md";
        if ("MEMORY.MD".equals(clean) || "MEMORIES.MD".equals(clean)) return "MEMORY.md";
        return "";
    }

    private String buildEntry(String title, String body) {
        String heading = title == null || title.trim().isEmpty() ? "Untitled note" : title.trim();
        return "\n\n## " + heading + "\n\n"
                + "- capturedAt: " + isoNow() + "\n"
                + "- source: Home Center chat\n\n"
                + body.trim() + "\n";
    }

    private String readFile(File file) throws Exception {
        if (!file.exists()) return "";
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        try (FileInputStream in = new FileInputStream(file)) {
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
        }
        return out.toString("UTF-8");
    }

    private String isoNow() {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US);
        format.setTimeZone(TimeZone.getDefault());
        return format.format(new Date());
    }

    private String clean(String value, int maxChars) {
        String text = value == null ? "" : value.replace("\u0000", "").trim();
        return text.length() > maxChars ? text.substring(0, maxChars) : text;
    }

    private boolean looksSensitive(String value) {
        String lower = value == null ? "" : value.toLowerCase(Locale.US);
        return lower.contains("authorization:")
                || lower.contains("bearer ")
                || lower.contains("api_key")
                || lower.contains("apikey")
                || lower.contains("access_token")
                || lower.contains("refresh_token")
                || lower.contains("client_secret")
                || lower.contains("password=");
    }

    private JSONObject baseResult(String toolName, boolean ok, String status, String error) {
        JSONObject json = new JSONObject();
        try {
            json.put("tool", toolName);
            json.put("ok", ok);
            json.put("status", status == null ? "" : status);
            json.put("error", error == null ? "" : error);
        } catch (Exception ignored) {
        }
        return json;
    }

    private JSONObject toolError(String toolName, String status, String detail) {
        JSONObject json = baseResult(toolName, false, status, detail);
        try {
            json.put("detail", detail == null ? "" : detail);
        } catch (Exception ignored) {
        }
        return json;
    }

    private String safe(String value) {
        return value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
    }
}
