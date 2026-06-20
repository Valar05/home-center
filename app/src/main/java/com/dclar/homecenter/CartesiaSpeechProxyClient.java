package com.dclar.homecenter;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

final class CartesiaSpeechProxyClient {
    private final String baseUrl;

    CartesiaSpeechProxyClient(String baseUrl) {
        this.baseUrl = baseUrl == null ? "" : baseUrl.trim();
    }

    boolean isConfigured() {
        return !baseUrl.isEmpty();
    }

    HttpURLConnection openSpeechStream(String text) throws IOException {
        if (!isConfigured()) {
            throw new IOException("Cartesia proxy base URL is not configured");
        }
        URL url = new URL(resolveEndpoint());
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(30000);
        connection.setRequestMethod("POST");
        connection.setDoInput(true);
        connection.setDoOutput(true);
        connection.setUseCaches(false);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setRequestProperty("Accept", "application/octet-stream");
        byte[] body = toJsonPayload(text).getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(body.length);
        try (OutputStream out = connection.getOutputStream()) {
            out.write(body);
        }
        int code = connection.getResponseCode();
        if (code != HttpURLConnection.HTTP_OK) {
            throw new IOException("Cartesia proxy returned HTTP " + code + errorSuffix(connection));
        }
        return connection;
    }

    private String resolveEndpoint() {
        if (baseUrl.endsWith("/")) {
            return baseUrl + "tts";
        }
        return baseUrl + "/tts";
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

    private String toJsonPayload(String text) {
        return "{\"text\":\"" + escapeJson(text) + "\"}";
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
