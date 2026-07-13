package com.dclar.homecenter;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

import org.json.JSONArray;
import org.json.JSONObject;

final class HostedSpeechClient {
    private final String baseUrl;
    HostedSpeechClient(String baseUrl) {
        this.baseUrl = baseUrl == null ? "" : baseUrl.trim();
    }

    boolean isConfigured() {
        return !baseUrl.isEmpty();
    }

    HttpURLConnection openSpeechStream(String text) throws IOException {
        return openProxySpeechStream(text);
    }

    HttpURLConnection openSpeechStream(String text, String modelId, String voiceName, String voiceId, String role) throws IOException {
        return openSpeechStream(text, "cartesia", modelId, voiceName, voiceId, role, "", "", "");
    }

    HttpURLConnection openSpeechStream(String text, String provider, String modelId, String voiceName, String voiceId, String role) throws IOException {
        return openSpeechStream(text, provider, modelId, voiceName, voiceId, role, "", "", "");
    }

    HttpURLConnection openSpeechStream(String text, String provider, String modelId, String voiceName, String voiceId, String role, String characterId, String voiceAlias, String acousticDirection) throws IOException {
        if (!baseUrl.isEmpty()) {
            return openProxySpeechStream(text, provider, modelId, voiceName, voiceId, role, characterId, voiceAlias, acousticDirection);
        }
        throw new IOException("Hosted speech is not configured in this build");
    }

    JSONArray searchVoices(String query, int limit) throws IOException {
        return searchVoices("cartesia", query, limit);
    }

    JSONArray searchVoices(String provider, String query, int limit) throws IOException {
        if (baseUrl.isEmpty()) {
            throw new IOException("Hosted speech is not configured in this build");
        }
        String cleanProvider = provider == null || provider.trim().isEmpty() ? "cartesia" : provider.trim().toLowerCase();
        String endpoint = resolveVoicesEndpoint() + "?provider=" + java.net.URLEncoder.encode(cleanProvider, "UTF-8")
                + "&q=" + java.net.URLEncoder.encode(query == null ? "" : query, "UTF-8")
                + "&limit=" + Math.max(1, Math.min(200, limit));
        HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(60000);
        connection.setRequestMethod("GET");
        connection.setRequestProperty("Accept", "application/json");
        int code = connection.getResponseCode();
        if (code != HttpURLConnection.HTTP_OK) {
            throw new IOException("Hosted voice search returned HTTP " + code + errorSuffix(connection));
        }
        try (InputStream input = connection.getInputStream()) {
            JSONObject payload = new JSONObject(new String(readAll(input), StandardCharsets.UTF_8));
            JSONArray voices = payload.optJSONArray("voices");
            return voices == null ? new JSONArray() : voices;
        } catch (Exception ex) {
            throw new IOException("Could not parse hosted voice search: " + ex.getMessage(), ex);
        } finally {
            connection.disconnect();
        }
    }

    private HttpURLConnection openProxySpeechStream(String text) throws IOException {
        return openProxySpeechStream(text, "cartesia", "", "", "", "", "", "", "");
    }

    private HttpURLConnection openProxySpeechStream(String text, String provider, String modelId, String voiceName, String voiceId, String role, String characterId, String voiceAlias, String acousticDirection) throws IOException {
        URL url = new URL(resolveEndpoint());
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(60000);
        connection.setRequestMethod("POST");
        connection.setDoInput(true);
        connection.setDoOutput(true);
        connection.setUseCaches(false);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setRequestProperty("Accept", "application/octet-stream");
        byte[] body = toJsonPayload(text, provider, modelId, voiceName, voiceId, role, characterId, voiceAlias, acousticDirection).getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(body.length);
        try (OutputStream out = connection.getOutputStream()) {
            out.write(body);
        }
        int code = connection.getResponseCode();
        if (code != HttpURLConnection.HTTP_OK) {
            throw new IOException("Hosted speech endpoint returned HTTP " + code + errorSuffix(connection));
        }
        return connection;
    }

    private String resolveEndpoint() {
        if (baseUrl.endsWith("/")) {
            return baseUrl + "tts";
        }
        return baseUrl + "/tts";
    }

    private String resolveVoicesEndpoint() {
        if (baseUrl.endsWith("/")) {
            return baseUrl + "ttsVoices";
        }
        return baseUrl + "/ttsVoices";
    }

    private String errorSuffix(HttpURLConnection connection) {
        InputStream errorStream = connection.getErrorStream();
        if (errorStream == null) {
            return "";
        }
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(errorStream, StandardCharsets.UTF_8))) {
            StringBuilder builder = new StringBuilder(": ");
            String line;
            boolean first = true;
            while ((line = reader.readLine()) != null) {
                if (!first) {
                    builder.append(' ');
                }
                builder.append(line);
                first = false;
            }
            return builder.toString();
        } catch (IOException ignored) {
            return "";
        }
    }

    private String toJsonPayload(String text, String provider, String modelId, String voiceName, String voiceId, String role, String characterId, String voiceAlias, String acousticDirection) {
        StringBuilder builder = new StringBuilder();
        builder.append("{\"text\":\"").append(escapeJson(text)).append("\"");
        appendJsonField(builder, "provider", provider == null || provider.trim().isEmpty() ? "cartesia" : provider.trim().toLowerCase());
        appendJsonField(builder, "modelId", modelId);
        appendJsonField(builder, "voiceName", voiceName);
        appendJsonField(builder, "voiceId", voiceId);
        appendJsonField(builder, "role", role);
        appendJsonField(builder, "characterId", characterId);
        appendJsonField(builder, "voiceAlias", voiceAlias);
        appendJsonField(builder, "acousticDirection", acousticDirection);
        builder.append('}');
        return builder.toString();
    }

    private void appendJsonField(StringBuilder builder, String key, String value) {
        String clean = value == null ? "" : value.trim();
        if (clean.isEmpty()) return;
        builder.append(",\"").append(key).append("\":\"").append(escapeJson(clean)).append("\"");
    }

    private byte[] readAll(InputStream input) throws IOException {
        java.io.ByteArrayOutputStream output = new java.io.ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int read;
        while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
        return output.toByteArray();
    }

    private String escapeJson(String value) {
        StringBuilder builder = new StringBuilder(value.length() + 16);
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            switch (ch) {
                case '\\':
                    builder.append("\\\\");
                    break;
                case '"':
                    builder.append("\\\"");
                    break;
                case '\b':
                    builder.append("\\b");
                    break;
                case '\f':
                    builder.append("\\f");
                    break;
                case '\n':
                    builder.append("\\n");
                    break;
                case '\r':
                    builder.append("\\r");
                    break;
                case '\t':
                    builder.append("\\t");
                    break;
                default:
                    if (ch < 0x20) {
                        builder.append(String.format("\\u%04x", (int) ch));
                    } else {
                        builder.append(ch);
                    }
                    break;
            }
        }
        return builder.toString();
    }
}
