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

final class GeminiClient {
    private final String apiKey;
    private final String model;

    GeminiClient(String apiKey, String model) {
        this.apiKey = apiKey == null ? "" : apiKey.trim();
        this.model = model == null || model.trim().isEmpty() ? "gemini-2.5-flash" : model.trim();
    }

    String generateReply(String prompt) throws IOException {
        if (apiKey.isEmpty()) {
            throw new IOException("Add GEMINI_API_KEY to local.properties and rebuild.");
        }
        JSONObject body;
        try {
            body = new JSONObject();
            JSONArray contents = new JSONArray();
            JSONObject content = new JSONObject();
            content.put("role", "user");
            JSONArray parts = new JSONArray();
            parts.put(new JSONObject().put("text", prompt == null ? "" : prompt));
            content.put("parts", parts);
            contents.put(content);
            body.put("contents", contents);

            JSONObject generationConfig = new JSONObject();
            generationConfig.put("temperature", 0.7);
            generationConfig.put("maxOutputTokens", 1024);
            body.put("generationConfig", generationConfig);
        } catch (JSONException ex) {
            throw new IOException("Could not build Gemini request: " + ex.getMessage(), ex);
        }

        String endpoint = "https://generativelanguage.googleapis.com/v1beta/models/"
                + model
                + ":generateContent?key="
                + apiKey;

        HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(12000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");

        byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(payload.length);
        try (OutputStream out = connection.getOutputStream()) {
            out.write(payload);
        }

        int code = connection.getResponseCode();
        String responseText = readBody(code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream());
        if (code < 200 || code >= 300) {
            throw new IOException("Gemini HTTP " + code + ": " + shortBody(responseText));
        }
        return extractText(responseText);
    }

    private String extractText(String jsonText) throws IOException {
        try {
            JSONObject root = new JSONObject(jsonText == null || jsonText.trim().isEmpty() ? "{}" : jsonText);
            JSONArray candidates = root.optJSONArray("candidates");
            if (candidates == null || candidates.length() == 0) {
                throw new IOException("Gemini returned no candidates.");
            }
            JSONObject candidate = candidates.optJSONObject(0);
            if (candidate == null) {
                throw new IOException("Gemini candidate was empty.");
            }
            JSONObject content = candidate.optJSONObject("content");
            if (content == null) {
                throw new IOException("Gemini response had no content.");
            }
            JSONArray parts = content.optJSONArray("parts");
            if (parts == null || parts.length() == 0) {
                throw new IOException("Gemini response had no text parts.");
            }
            StringBuilder text = new StringBuilder();
            for (int i = 0; i < parts.length(); i++) {
                JSONObject part = parts.optJSONObject(i);
                if (part != null) {
                    text.append(part.optString("text", ""));
                }
            }
            String result = text.toString().trim();
            if (result.isEmpty()) {
                throw new IOException("Gemini response text was empty.");
            }
            return result;
        } catch (JSONException ex) {
            throw new IOException("Could not parse Gemini response: " + ex.getMessage(), ex);
        }
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
        if (trimmed.length() > 180) {
            return trimmed.substring(0, 177) + "...";
        }
        return trimmed;
    }
}
