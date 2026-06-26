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

    OpenAiAgentClient(String baseUrl) {
        this.baseUrl = baseUrl == null ? "" : baseUrl.trim();
    }

    boolean isConfigured() {
        return !baseUrl.isEmpty();
    }

    Reply sendTurn(String idToken, String message, String transcript, String summary, String bucket, String listName) throws IOException {
        if (!isConfigured()) {
            throw new IOException("Agent gateway is not configured. Add AGENT_GATEWAY_BASE_URL to local.properties and rebuild.");
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
            capabilities.put("google:drive_docs_gmail_calendar");
            capabilities.put("home_center:firestore_lists");
            capabilities.put("ticktick:fallback_lists");
            capabilities.put("cartesia:narration");
            body.put("capabilities", capabilities);
        } catch (JSONException ex) {
            throw new IOException("Could not build agent request: " + ex.getMessage(), ex);
        }
        JSONObject response = postJson("agentTurn", idToken, body);
        return new Reply(
                response.optString("reply", response.optString("text", "")),
                response.optString("narration", ""),
                response.optString("status", ""),
                response.optString("technicalDetails", response.optString("details", "")));
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

    private JSONObject postJson(String path, String idToken, JSONObject body) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(resolve(path)).openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(45000);
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
