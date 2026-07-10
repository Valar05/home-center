package com.dclar.homecenter;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

final class OpenAiAgentClient {
    private static final int CONNECT_TIMEOUT_MS = 10000;
    private static final int AGENT_READ_TIMEOUT_MS = 130000;

    static final class ToolTurn {
        final String type;
        final String reply;
        final String narration;
        final String status;
        final String toolName;
        final JSONObject arguments;
        final JSONObject pendingConfirmation;
        final JSONObject taskStateUpdate;
        final String technicalDetails;

        ToolTurn(String type, String reply, String narration, String status, String toolName, JSONObject arguments, JSONObject pendingConfirmation, JSONObject taskStateUpdate, String technicalDetails) {
            this.type = type == null ? "" : type.trim();
            this.reply = reply == null ? "" : reply.trim();
            this.narration = narration == null ? "" : narration.trim();
            this.status = status == null ? "" : status.trim();
            this.toolName = toolName == null ? "" : toolName.trim();
            this.arguments = arguments == null ? new JSONObject() : arguments;
            this.pendingConfirmation = pendingConfirmation == null ? null : pendingConfirmation;
            this.taskStateUpdate = taskStateUpdate == null ? null : taskStateUpdate;
            this.technicalDetails = technicalDetails == null ? "" : technicalDetails.trim();
        }

        boolean requestsTool() {
            return "tool_call".equals(type) && !toolName.isEmpty();
        }
    }

    static final class Reply {
        final String text;
        final String narration;
        final String status;
        final String technicalDetails;

        Reply(String text, String narration, String status, String technicalDetails) {
            this.text = text == null ? "" : text.trim();
            this.narration = narration == null ? "" : narration.trim();
            this.status = status == null ? "" : status.trim();
            this.technicalDetails = technicalDetails == null ? "" : technicalDetails.trim();
        }
    }

    private final String baseUrl;
    private final String apiKey;

    OpenAiAgentClient(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl == null ? "" : baseUrl.trim();
        this.apiKey = apiKey == null ? "" : apiKey.trim();
    }

    boolean isConfigured() {
        return !baseUrl.isEmpty() || !apiKey.isEmpty();
    }

    Reply sendTurn(String idToken, String message, String transcript, String summary, String bucket, String listName) throws IOException {
        if (!isConfigured()) {
            throw new IOException("GPT-5.5 is not configured in this build.");
        }
        JSONObject body = new JSONObject();
        try {
            body.put("message", message == null ? "" : message);
            body.put("transcript", transcript == null ? "" : transcript);
            body.put("summary", summary == null ? "" : summary);
            body.put("bucket", bucket == null ? "" : bucket);
            body.put("listName", listName == null ? "shopping" : listName);
            JSONArray capabilities = new JSONArray();
            capabilities.put("openai:gpt-5.5");
            capabilities.put("openai:web_search");
            capabilities.put("google:drive_docs_sheets_gmail_calendar_contacts");
            capabilities.put("home_center:firestore_lists");
            capabilities.put("ticktick:fallback_lists");
            capabilities.put("elevenlabs:hosted_narration");
            body.put("capabilities", capabilities);
        } catch (JSONException ex) {
            throw new IOException("Could not build agent request: " + ex.getMessage(), ex);
        }
        if (!baseUrl.isEmpty()) {
            try {
                JSONObject response = postJson("agentTurn", idToken, body);
                return new Reply(
                        response.optString("reply", response.optString("text", "")),
                        response.optString("narration", ""),
                        response.optString("status", ""),
                        response.optString("technicalDetails", response.optString("details", "")));
            } catch (IOException ex) {
                if (apiKey.isEmpty()) {
                    throw ex;
                }
            }
        }
        return sendDirectOpenAi(message, transcript, summary, bucket, listName);
    }

    ToolTurn sendToolTurn(String idToken, String message, String transcript, String summary, JSONArray toolResults, JSONArray tools, JSONArray unavailableToolGroups, JSONObject pendingConfirmation, JSONObject workingMemory, JSONObject timeContext, JSONObject evidenceContext, JSONArray attachmentImages, boolean finalOnly) throws IOException {
        if (!isConfigured()) {
            throw new IOException("GPT-5.5 is not configured in this build.");
        }
        JSONObject body = new JSONObject();
        try {
            body.put("message", message == null ? "" : message);
            body.put("transcript", transcript == null ? "" : transcript);
            body.put("summary", summary == null ? "" : summary);
            body.put("toolResults", toolResults == null ? new JSONArray() : toolResults);
            body.put("tools", tools == null ? new JSONArray() : tools);
            body.put("unavailableToolGroups", unavailableToolGroups == null ? new JSONArray() : unavailableToolGroups);
            body.put("workingMemory", workingMemory == null ? new JSONObject() : workingMemory);
            body.put("timeContext", timeContext == null ? new JSONObject() : timeContext);
            body.put("evidenceContext", evidenceContext == null ? new JSONObject() : evidenceContext);
            body.put("attachmentImages", attachmentImages == null ? new JSONArray() : attachmentImages);
            body.put("finalOnly", finalOnly);
            body.put("debugTrace", true);
            if (pendingConfirmation != null) {
                body.put("pendingConfirmation", pendingConfirmation);
            }
        } catch (JSONException ex) {
            throw new IOException("Could not build tool agent request: " + ex.getMessage(), ex);
        }
        if (!baseUrl.isEmpty()) {
            JSONObject response = postJson("agentToolTurn", idToken, body);
            return parseToolTurn(response);
        }
        throw new IOException("Android tool broker requires the Home Center gateway.");
    }

    private ToolTurn parseToolTurn(JSONObject response) {
        JSONObject arguments = response.optJSONObject("arguments");
        if (arguments == null) {
            JSONObject tool = response.optJSONObject("tool");
            if (tool != null) {
                arguments = tool.optJSONObject("arguments");
            }
        }
        String toolName = response.optString("toolName", response.optString("name", ""));
        JSONObject tool = response.optJSONObject("tool");
        if (tool != null && toolName.isEmpty()) {
            toolName = tool.optString("name", "");
        }
        return new ToolTurn(
                response.optString("type", ""),
                response.optString("reply", response.optString("text", "")),
                response.optString("narration", ""),
                response.optString("status", ""),
                toolName,
                arguments == null ? new JSONObject() : arguments,
                response.optJSONObject("pendingConfirmation"),
                response.optJSONObject("taskStateUpdate"),
                response.optString("technicalDetails", response.optString("details", "")));
    }

    private Reply sendDirectOpenAi(String message, String transcript, String summary, String bucket, String listName) throws IOException {
        if (apiKey.isEmpty()) {
            throw new IOException("OpenAI API key is not configured in this build.");
        }
        JSONObject body = new JSONObject();
        try {
            body.put("model", "gpt-5.5");
            body.put("reasoning", new JSONObject().put("effort", "low"));
            body.put("text", new JSONObject().put("verbosity", "low"));
            if (shouldEnableDirectWebSearch(message)) {
                JSONArray tools = new JSONArray();
                tools.put(new JSONObject().put("type", "web_search"));
                body.put("tools", tools);
            }
            body.put("input", buildDirectPrompt(message, transcript, summary, bucket, listName));
        } catch (JSONException ex) {
            throw new IOException("Could not build direct OpenAI request: " + ex.getMessage(), ex);
        }
        HttpURLConnection connection = (HttpURLConnection) new URL("https://api.openai.com/v1/responses").openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
        connection.setReadTimeout(AGENT_READ_TIMEOUT_MS);
        connection.setDoInput(true);
        connection.setDoOutput(true);
        connection.setUseCaches(false);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Authorization", "Bearer " + apiKey);
        byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(payload.length);
        try (OutputStream out = connection.getOutputStream()) {
            out.write(payload);
        }
        int code = connection.getResponseCode();
        String responseText = readBody(code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream());
        if (code < 200 || code >= 300) {
            throw new IOException("OpenAI HTTP " + code + ": " + shortBody(responseText));
        }
        try {
            JSONObject json = new JSONObject(responseText == null || responseText.trim().isEmpty() ? "{}" : responseText);
            String text = json.optString("output_text", "");
            if (text.isEmpty()) {
                text = extractOutputText(json);
            }
            return new Reply(text, text, "gpt_5_5_direct_complete", "");
        } catch (JSONException ex) {
            throw new IOException("Could not parse OpenAI response: " + ex.getMessage(), ex);
        }
    }

    private String buildDirectPrompt(String message, String transcript, String summary, String bucket, String listName) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("You are Home Center, a cohesive voice-first life dashboard for a blind user.\n");
        prompt.append("Home Center doctrine: Home Center is a life-operations system, not a chatbot with extras. The model reasons, the app executes, the storage layer remembers, and validation proves what is real. Reduce everyday cognitive load by turning tasks, calendar commitments, contacts, email, documents, research, household workflows, and memories into durable state and concrete next actions. Android owns capabilities and permissions; GPT owns judgment, tool choice, chaining, recovery, follow-up questions, and final answers. Do not narrate plumbing when an action can be completed. Never imply a capability that is not advertised by the tool registry.\n");
        prompt.append("Use concise, actionable language. Include source names when using web search.\n");
        prompt.append("For external writes like Google Docs, Gmail, Calendar, or list changes, ask for explicit confirmation.\n");
        prompt.append("Default bucket: ").append(bucket == null ? "" : bucket).append(". Default list: ").append(listName == null ? "shopping" : listName).append(".\n");
        if (summary != null && !summary.trim().isEmpty()) {
            prompt.append("Summary: ").append(summary.trim()).append("\n");
        }
        if (transcript != null && !transcript.trim().isEmpty()) {
            prompt.append("Recent transcript: ").append(transcript.trim()).append("\n");
        }
        prompt.append("Latest user request: ").append(message == null ? "" : message.trim());
        return prompt.toString();
    }

    private boolean shouldEnableDirectWebSearch(String message) {
        String lower = message == null ? "" : message.trim().toLowerCase();
        return lower.matches(".*\\b(web|search the web|internet|online|latest|current|today|news|public github|github\\.com|raw\\.githubusercontent\\.com|repo|repository|readme|documentation|docs site|website|url|http://|https://)\\b.*");
    }

    private String extractOutputText(JSONObject json) {
        StringBuilder builder = new StringBuilder();
        JSONArray output = json.optJSONArray("output");
        if (output == null) {
            return "";
        }
        for (int i = 0; i < output.length(); i++) {
            JSONObject item = output.optJSONObject(i);
            if (item == null) {
                continue;
            }
            JSONArray content = item.optJSONArray("content");
            if (content == null) {
                continue;
            }
            for (int j = 0; j < content.length(); j++) {
                JSONObject part = content.optJSONObject(j);
                if (part != null) {
                    builder.append(part.optString("text", ""));
                }
            }
        }
        return builder.toString().trim();
    }

    JSONObject createGitHubIssue(String idToken, JSONObject arguments) throws IOException {
        JSONObject body = arguments == null ? new JSONObject() : arguments;
        return postJson("githubCreateIssue", idToken, body);
    }

    void recordUsageToolEvent(String idToken, JSONObject event) throws IOException {
        postJson("usageToolEvent", idToken, event == null ? new JSONObject() : event);
    }

    JSONObject usageSummary(String idToken, String bucketId, int days) throws IOException {
        JSONObject body = new JSONObject();
        try {
            body.put("bucketId", bucketId == null ? "" : bucketId.trim());
            body.put("days", days);
        } catch (JSONException ex) {
            throw new IOException("Could not build usage summary request: " + ex.getMessage(), ex);
        }
        return postJson("usageSummary", idToken, body);
    }

    void exchangeGoogleAuthCode(String idToken, String authCode) throws IOException {
        if (!isConfigured() || authCode == null || authCode.trim().isEmpty()) {
            return;
        }
        JSONObject body = new JSONObject();
        try {
            body.put("authCode", authCode.trim());
        } catch (JSONException ex) {
            throw new IOException("Could not build Google auth exchange request: " + ex.getMessage(), ex);
        }
        postJson("googleAuthCodeExchange", idToken, body);
    }

    JSONObject approveTermuxPairing(String idToken, String pairingId, String code) throws IOException {
        if (!isConfigured()) {
            throw new IOException("Home Center gateway is not configured in this build.");
        }
        JSONObject body = new JSONObject();
        try {
            body.put("pairingId", pairingId == null ? "" : pairingId.trim());
            body.put("code", code == null ? "" : code.trim());
        } catch (JSONException ex) {
            throw new IOException("Could not build Termux pairing approval request: " + ex.getMessage(), ex);
        }
        return postJson("termuxPairingApprove", idToken, body);
    }

    Reply checkGoogleDrive(String idToken, String query) throws IOException {
        JSONObject body = new JSONObject();
        try {
            body.put("query", query == null ? "" : query);
        } catch (JSONException ex) {
            throw new IOException("Could not build Google Drive probe request: " + ex.getMessage(), ex);
        }
        JSONObject response = postJson("googleDriveProbe", idToken, body);
        return new Reply(
                response.optString("reply", ""),
                response.optString("narration", ""),
                response.optString("status", ""),
                response.optString("technicalDetails", response.optString("details", "")));
    }

    private JSONObject postJson(String path, String idToken, JSONObject body) throws IOException {
        IOException lastError = null;
        for (int attempt = 1; attempt <= 2; attempt++) {
            try {
                return postJsonOnce(path, idToken, body);
            } catch (IOException ex) {
                lastError = ex;
                if (attempt >= 2 || !isTransientGatewayTransportError(ex)) {
                    throw ex;
                }
                try {
                    Thread.sleep(700);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw ex;
                }
            }
        }
        throw lastError == null ? new IOException("Agent gateway request failed.") : lastError;
    }

    private JSONObject postJsonOnce(String path, String idToken, JSONObject body) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(resolve(path)).openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
        connection.setReadTimeout(AGENT_READ_TIMEOUT_MS);
        connection.setDoInput(true);
        connection.setDoOutput(true);
        connection.setUseCaches(false);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setRequestProperty("Accept", "application/json");
        if (idToken != null && !idToken.trim().isEmpty()) {
            connection.setRequestProperty("Authorization", "Bearer " + idToken.trim());
        }
        byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(payload.length);
        try (OutputStream out = connection.getOutputStream()) {
            out.write(payload);
        }
        int code = connection.getResponseCode();
        String responseText = readBody(code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream());
        if (code < 200 || code >= 300) {
            throw new IOException("Agent gateway HTTP " + code + ": " + shortBody(responseText));
        }
        try {
            return new JSONObject(responseText == null || responseText.trim().isEmpty() ? "{}" : responseText);
        } catch (JSONException ex) {
            throw new IOException("Could not parse agent gateway response: " + ex.getMessage(), ex);
        }
    }

    private boolean isTransientGatewayTransportError(IOException ex) {
        String message = ex == null || ex.getMessage() == null ? "" : ex.getMessage().toLowerCase();
        return message.contains("software caused connection abort")
                || message.contains("unexpected end of stream")
                || message.contains("connection reset")
                || message.contains("connection closed")
                || message.contains("stream was reset");
    }

    private String resolve(String path) {
        String cleanPath = path.startsWith("/") ? path.substring(1) : path;
        if (baseUrl.endsWith("/")) {
            return baseUrl + cleanPath;
        }
        return baseUrl + "/" + cleanPath;
    }

    private String readBody(InputStream stream) throws IOException {
        if (stream == null) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                builder.append(line).append('\n');
            }
        }
        return builder.toString().trim();
    }

    private String shortBody(String value) {
        if (value == null || value.trim().isEmpty()) {
            return "empty response";
        }
        String trimmed = value.trim();
        if (trimmed.length() > 240) {
            return trimmed.substring(0, 237) + "...";
        }
        return trimmed;
    }
}
