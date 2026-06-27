package com.dclar.homecenter;

import android.content.Context;
import android.net.Uri;
import android.util.Base64;

import com.google.android.gms.auth.GoogleAuthException;
import com.google.android.gms.auth.GoogleAuthUtil;
import com.google.android.gms.auth.UserRecoverableAuthException;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

final class GoogleGmailClient {
    private static final String BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me";
    private final Context context;

    GoogleGmailClient(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject runTool(String toolName, JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, toolName);
        if (!token.ok) return token.json;
        try {
            if ("gmail.search".equals(toolName)) return searchTool(token.value, arguments);
            if ("gmail.read".equals(toolName)) return readTool(token.value, arguments);
            if ("gmail.create_draft".equals(toolName)) return createDraftTool(token.value, arguments);
            if ("gmail.update_draft".equals(toolName)) return updateDraftTool(token.value, arguments);
            if ("gmail.send_draft".equals(toolName)) return sendDraftTool(token.value, arguments);
            if ("gmail.send_email".equals(toolName)) return sendEmailTool(token.value, arguments);
            return toolError(toolName, "unknown_tool", "Android does not expose that Gmail tool.");
        } catch (Exception ex) {
            return toolError(toolName, "gmail_error", safe(ex.getMessage()));
        }
    }

    private JSONObject searchTool(String token, JSONObject arguments) throws Exception {
        int pageSize = Math.max(1, Math.min(10, arguments == null ? 5 : arguments.optInt("pageSize", 5)));
        Uri.Builder builder = Uri.parse(BASE_URL + "/messages").buildUpon().appendQueryParameter("maxResults", String.valueOf(pageSize));
        String query = cleanArg(arguments, "query");
        if (!query.isEmpty()) builder.appendQueryParameter("q", query);
        JSONObject listed = getJson(builder.build().toString(), token);
        JSONArray messages = listed.optJSONArray("messages");
        JSONArray out = new JSONArray();
        if (messages != null) {
            for (int i = 0; i < messages.length(); i++) {
                String id = messages.optJSONObject(i) == null ? "" : messages.optJSONObject(i).optString("id", "");
                if (!id.isEmpty()) out.put(messageSummary(token, id));
            }
        }
        return baseResult("gmail.search", true).put("messages", out);
    }

    private JSONObject readTool(String token, JSONObject arguments) throws Exception {
        String messageId = cleanArg(arguments, "messageId");
        if (messageId.isEmpty()) return toolError("gmail.read", "missing_message_id", "gmail.read requires messageId.");
        JSONObject message = getJson(BASE_URL + "/messages/" + Uri.encode(messageId) + "?format=full", token);
        JSONObject payload = message.optJSONObject("payload");
        return baseResult("gmail.read", true)
                .put("messageId", messageId)
                .put("threadId", message.optString("threadId", ""))
                .put("snippet", message.optString("snippet", ""))
                .put("headers", headersJson(payload))
                .put("body", extractBody(payload));
    }

    private JSONObject createDraftTool(String token, JSONObject arguments) throws Exception {
        JSONObject payload = new JSONObject().put("message", new JSONObject().put("raw", rawEmail(arguments)));
        JSONObject draft = postJson(BASE_URL + "/drafts", token, payload);
        return baseResult("gmail.create_draft", true).put("draft", draft).put("draftId", draft.optString("id", ""));
    }

    private JSONObject updateDraftTool(String token, JSONObject arguments) throws Exception {
        String draftId = cleanArg(arguments, "draftId");
        if (draftId.isEmpty()) return toolError("gmail.update_draft", "missing_draft_id", "gmail.update_draft requires draftId.");
        JSONObject payload = new JSONObject().put("id", draftId).put("message", new JSONObject().put("raw", rawEmail(arguments)));
        JSONObject draft = putJson(BASE_URL + "/drafts/" + Uri.encode(draftId), token, payload);
        return baseResult("gmail.update_draft", true).put("draft", draft).put("draftId", draft.optString("id", draftId));
    }

    private JSONObject sendDraftTool(String token, JSONObject arguments) throws Exception {
        String draftId = cleanArg(arguments, "draftId");
        if (draftId.isEmpty()) return toolError("gmail.send_draft", "missing_draft_id", "gmail.send_draft requires draftId.");
        JSONObject sent = postJson(BASE_URL + "/drafts/send", token, new JSONObject().put("id", draftId));
        return baseResult("gmail.send_draft", true).put("message", sent).put("messageId", sent.optString("id", ""));
    }

    private JSONObject sendEmailTool(String token, JSONObject arguments) throws Exception {
        JSONObject sent = postJson(BASE_URL + "/messages/send", token, new JSONObject().put("raw", rawEmail(arguments)));
        return baseResult("gmail.send_email", true).put("message", sent).put("messageId", sent.optString("id", ""));
    }

    private JSONObject messageSummary(String token, String messageId) throws Exception {
        JSONObject message = getJson(BASE_URL + "/messages/" + Uri.encode(messageId) + "?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date", token);
        JSONObject out = new JSONObject();
        out.put("id", message.optString("id", messageId));
        out.put("threadId", message.optString("threadId", ""));
        out.put("snippet", message.optString("snippet", ""));
        out.put("headers", headersJson(message.optJSONObject("payload")));
        return out;
    }

    private String rawEmail(JSONObject arguments) {
        StringBuilder message = new StringBuilder();
        appendHeader(message, "To", cleanArg(arguments, "to"));
        appendHeader(message, "Cc", cleanArg(arguments, "cc"));
        appendHeader(message, "Bcc", cleanArg(arguments, "bcc"));
        appendHeader(message, "Subject", cleanArg(arguments, "subject"));
        message.append("MIME-Version: 1.0\r\n");
        message.append("Content-Type: text/plain; charset=UTF-8\r\n");
        message.append("\r\n");
        message.append(cleanArg(arguments, "body"));
        return Base64.encodeToString(message.toString().getBytes(StandardCharsets.UTF_8), Base64.URL_SAFE | Base64.NO_WRAP);
    }

    private void appendHeader(StringBuilder builder, String name, String value) {
        if (value != null && !value.trim().isEmpty()) builder.append(name).append(": ").append(value.trim()).append("\r\n");
    }

    private JSONObject headersJson(JSONObject payload) throws Exception {
        JSONObject out = new JSONObject();
        if (payload == null) return out;
        JSONArray headers = payload.optJSONArray("headers");
        if (headers == null) return out;
        for (int i = 0; i < headers.length(); i++) {
            JSONObject h = headers.optJSONObject(i);
            if (h != null) out.put(h.optString("name", ""), h.optString("value", ""));
        }
        return out;
    }

    private String extractBody(JSONObject payload) {
        if (payload == null) return "";
        String mimeType = payload.optString("mimeType", "");
        JSONObject body = payload.optJSONObject("body");
        String data = body == null ? "" : body.optString("data", "");
        if (mimeType.startsWith("text/plain") && !data.isEmpty()) return decodeBody(data);
        JSONArray parts = payload.optJSONArray("parts");
        if (parts != null) {
            List<String> chunks = new ArrayList<>();
            for (int i = 0; i < parts.length(); i++) {
                String chunk = extractBody(parts.optJSONObject(i));
                if (!chunk.trim().isEmpty()) chunks.add(chunk.trim());
            }
            return join(chunks, "\n\n");
        }
        return data.isEmpty() ? "" : decodeBody(data);
    }

    private String decodeBody(String data) {
        try {
            return new String(Base64.decode(data, Base64.URL_SAFE | Base64.NO_WRAP), StandardCharsets.UTF_8);
        } catch (Exception ex) {
            return "";
        }
    }

    private TokenResult tokenForTool(GoogleSignInAccount account, String toolName) {
        if (account == null || account.getAccount() == null) return TokenResult.error(toolError(toolName, "not_signed_in", "Sign in with Google first."));
        ToolRegistry.ToolDefinition tool = ToolRegistry.definition(toolName);
        if (tool == null) return TokenResult.error(toolError(toolName, "unknown_tool", "Tool is not registered."));
        for (String scope : tool.requiredScopes) {
            if (!account.getGrantedScopes().contains(new com.google.android.gms.common.api.Scope(scope))) {
                return TokenResult.error(toolError(toolName, "scope_missing", "Reconnect Google to approve " + scope + "."));
            }
        }
        try {
            String token = GoogleAuthUtil.getToken(context, account.getAccount(), ToolRegistry.tokenScopeFor(toolName));
            return TokenResult.ok(token);
        } catch (UserRecoverableAuthException ex) {
            return TokenResult.error(toolError(toolName, "scope_recoverable", "Google permission needs approval: " + safe(ex.getMessage())));
        } catch (IOException | GoogleAuthException ex) {
            return TokenResult.error(toolError(toolName, "token_error", safe(ex.getMessage())));
        }
    }

    private JSONObject getJson(String url, String token) throws Exception { return new JSONObject(requestText("GET", url, token, null)); }
    private JSONObject postJson(String url, String token, JSONObject payload) throws Exception { return new JSONObject(requestText("POST", url, token, payload)); }
    private JSONObject putJson(String url, String token, JSONObject payload) throws Exception { return new JSONObject(requestText("PUT", url, token, payload)); }

    private String requestText(String method, String url, String token, JSONObject payload) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        try {
            connection.setRequestMethod(method);
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/json");
            if (payload != null) {
                byte[] bytes = payload.toString().getBytes(StandardCharsets.UTF_8);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                connection.setFixedLengthStreamingMode(bytes.length);
                try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
            }
            int status = connection.getResponseCode();
            String body = readBody(status >= 400 ? connection.getErrorStream() : connection.getInputStream());
            if (status < 200 || status >= 300) throw new IOException("Gmail HTTP " + status + ": " + abbreviate(body));
            return body == null || body.trim().isEmpty() ? "{}" : body;
        } finally {
            connection.disconnect();
        }
    }

    private static JSONObject baseResult(String toolName, boolean ok) throws Exception {
        return new JSONObject().put("tool", toolName).put("ok", ok).put("error", "").put("detail", "");
    }

    private static JSONObject toolError(String toolName, String error, String detail) {
        JSONObject json = new JSONObject();
        try { json.put("tool", toolName).put("ok", false).put("error", error).put("detail", detail == null ? "" : detail); } catch (Exception ignored) {}
        return json;
    }

    private static String cleanArg(JSONObject arguments, String name) { return arguments == null ? "" : arguments.optString(name, "").trim(); }
    private static String join(List<String> values, String separator) { StringBuilder b = new StringBuilder(); for (String v : values) { if (b.length() > 0) b.append(separator); b.append(v); } return b.toString(); }
    private static String readBody(InputStream stream) throws IOException { if (stream == null) return ""; try (InputStream input = new BufferedInputStream(stream); ByteArrayOutputStream output = new ByteArrayOutputStream()) { byte[] buffer = new byte[8192]; int read; while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read); return output.toString(StandardCharsets.UTF_8.name()); } }
    private static String abbreviate(String value) { String clean = value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim(); return clean.length() > 500 ? clean.substring(0, 497) + "..." : clean; }
    private static String safe(String value) { return value == null || value.trim().isEmpty() ? "unknown error" : abbreviate(value); }

    private static final class TokenResult {
        final boolean ok;
        final String value;
        final JSONObject json;
        private TokenResult(boolean ok, String value, JSONObject json) { this.ok = ok; this.value = value == null ? "" : value; this.json = json == null ? new JSONObject() : json; }
        static TokenResult ok(String value) { return new TokenResult(true, value, new JSONObject()); }
        static TokenResult error(JSONObject json) { return new TokenResult(false, "", json); }
    }
}
