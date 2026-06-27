package com.dclar.homecenter;

import android.content.Context;
import android.net.Uri;

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

final class GoogleSheetsClient {
    private static final String SHEETS_URL = "https://sheets.googleapis.com/v4/spreadsheets";
    private static final String DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files";
    private static final String FOLDER_MIME_TYPE = "application/vnd.google-apps.folder";
    private static final String SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet";
    private final Context context;

    GoogleSheetsClient(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject runTool(String toolName, JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, toolName);
        if (!token.ok) return token.json;
        try {
            if ("sheets.search".equals(toolName)) return searchTool(token.value, arguments);
            if ("sheets.read".equals(toolName)) return readTool(token.value, arguments);
            if ("sheets.create".equals(toolName)) return createTool(token.value, arguments);
            if ("sheets.update".equals(toolName)) return updateTool(token.value, arguments);
            return toolError(toolName, "unknown_tool", "Android does not expose that Sheets tool.");
        } catch (Exception ex) {
            return toolError(toolName, "sheets_error", safe(ex.getMessage()));
        }
    }

    private JSONObject searchTool(String token, JSONObject arguments) throws Exception {
        int pageSize = Math.max(1, Math.min(10, arguments == null ? 5 : arguments.optInt("pageSize", 5)));
        String folderName = cleanArg(arguments, "folderName");
        String parentId = "";
        if (!folderName.isEmpty()) {
            JSONArray folders = driveSearch(token, "mimeType='" + FOLDER_MIME_TYPE + "' and name contains '" + escapeQuery(folderName) + "' and trashed=false", 5);
            if (folders.length() == 0) return baseResult("sheets.search", true).put("files", new JSONArray()).put("detail", "No folder matched " + folderName + ".");
            parentId = folders.optJSONObject(0) == null ? "" : folders.optJSONObject(0).optString("id", "");
        }
        List<String> clauses = new ArrayList<>();
        clauses.add("trashed=false");
        clauses.add("mimeType='" + SHEET_MIME_TYPE + "'");
        String query = cleanArg(arguments, "query");
        if (!query.isEmpty()) clauses.add("name contains '" + escapeQuery(query) + "'");
        if (!parentId.isEmpty()) clauses.add("'" + escapeQuery(parentId) + "' in parents");
        return baseResult("sheets.search", true).put("files", driveSearch(token, joinClauses(clauses), pageSize));
    }

    private JSONObject readTool(String token, JSONObject arguments) throws Exception {
        String spreadsheetId = cleanArg(arguments, "spreadsheetId");
        String range = cleanArg(arguments, "range");
        if (spreadsheetId.isEmpty()) return toolError("sheets.read", "missing_spreadsheet_id", "sheets.read requires spreadsheetId.");
        if (range.isEmpty()) range = "A1:Z100";
        JSONObject values = getJson(SHEETS_URL + "/" + Uri.encode(spreadsheetId) + "/values/" + Uri.encode(range), token);
        JSONObject metadata = getJson(SHEETS_URL + "/" + Uri.encode(spreadsheetId) + "?fields=spreadsheetId,spreadsheetUrl,properties(title)", token);
        return baseResult("sheets.read", true)
                .put("spreadsheetId", spreadsheetId)
                .put("range", range)
                .put("values", values.optJSONArray("values") == null ? new JSONArray() : values.optJSONArray("values"))
                .put("spreadsheet", metadata);
    }

    private JSONObject createTool(String token, JSONObject arguments) throws Exception {
        String title = cleanArg(arguments, "title");
        String sheetTitle = cleanArg(arguments, "sheetTitle");
        String folderId = cleanArg(arguments, "folderId");
        if (title.isEmpty()) title = "Home Center Sheet";
        if (sheetTitle.isEmpty()) sheetTitle = "Sheet1";
        JSONObject payload = new JSONObject()
                .put("properties", new JSONObject().put("title", title))
                .put("sheets", new JSONArray().put(new JSONObject().put("properties", new JSONObject().put("title", sheetTitle))));
        JSONObject created = postJson(SHEETS_URL, token, payload);
        String spreadsheetId = created.optString("spreadsheetId", "");
        if (spreadsheetId.isEmpty()) return toolError("sheets.create", "missing_spreadsheet_id", "Google Sheets did not return spreadsheetId.");
        JSONArray values = valuesArg(arguments);
        if (values.length() > 0) {
            putJson(SHEETS_URL + "/" + Uri.encode(spreadsheetId) + "/values/" + Uri.encode(sheetTitle + "!A1") + "?valueInputOption=USER_ENTERED", token,
                    new JSONObject().put("range", sheetTitle + "!A1").put("majorDimension", "ROWS").put("values", values));
        }
        if (!folderId.isEmpty()) {
            patchJson(DRIVE_FILES_URL + "/" + Uri.encode(spreadsheetId) + "?addParents=" + Uri.encode(folderId) + "&fields=id,parents", token, new JSONObject());
        }
        return baseResult("sheets.create", true)
                .put("status", "google_sheet_created")
                .put("spreadsheetId", spreadsheetId)
                .put("title", title)
                .put("spreadsheetUrl", created.optString("spreadsheetUrl", ""))
                .put("spreadsheet", created);
    }

    private JSONObject updateTool(String token, JSONObject arguments) throws Exception {
        String spreadsheetId = cleanArg(arguments, "spreadsheetId");
        String range = cleanArg(arguments, "range");
        if (spreadsheetId.isEmpty()) return toolError("sheets.update", "missing_spreadsheet_id", "sheets.update requires spreadsheetId.");
        if (range.isEmpty()) return toolError("sheets.update", "missing_range", "sheets.update requires range.");
        JSONArray values = valuesArg(arguments);
        if (values.length() == 0) return toolError("sheets.update", "missing_values", "sheets.update requires values.");
        JSONObject updated = putJson(SHEETS_URL + "/" + Uri.encode(spreadsheetId) + "/values/" + Uri.encode(range) + "?valueInputOption=USER_ENTERED", token,
                new JSONObject().put("range", range).put("majorDimension", "ROWS").put("values", values));
        return baseResult("sheets.update", true)
                .put("status", "google_sheet_updated")
                .put("spreadsheetId", spreadsheetId)
                .put("range", range)
                .put("updated", updated);
    }

    private JSONArray valuesArg(JSONObject arguments) {
        if (arguments == null) return new JSONArray();
        JSONArray values = arguments.optJSONArray("values");
        if (values != null) return values;
        String value = cleanArg(arguments, "value");
        return value.isEmpty() ? new JSONArray() : new JSONArray().put(new JSONArray().put(value));
    }

    private JSONArray driveSearch(String token, String query, int pageSize) throws Exception {
        Uri.Builder builder = Uri.parse(DRIVE_FILES_URL).buildUpon()
                .appendQueryParameter("pageSize", String.valueOf(Math.max(1, Math.min(10, pageSize))))
                .appendQueryParameter("fields", "files(id,name,mimeType,modifiedTime,webViewLink)")
                .appendQueryParameter("orderBy", "modifiedTime desc")
                .appendQueryParameter("supportsAllDrives", "true")
                .appendQueryParameter("includeItemsFromAllDrives", "true");
        if (query != null && !query.trim().isEmpty()) builder.appendQueryParameter("q", query);
        JSONObject root = getJson(builder.build().toString(), token);
        return root.optJSONArray("files") == null ? new JSONArray() : root.optJSONArray("files");
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
            return TokenResult.ok(GoogleAuthUtil.getToken(context, account.getAccount(), ToolRegistry.tokenScopeFor(toolName)));
        } catch (UserRecoverableAuthException ex) {
            return TokenResult.error(toolError(toolName, "scope_recoverable", "Google permission needs approval: " + safe(ex.getMessage())));
        } catch (IOException | GoogleAuthException ex) {
            return TokenResult.error(toolError(toolName, "token_error", safe(ex.getMessage())));
        }
    }

    private JSONObject getJson(String url, String token) throws Exception { return new JSONObject(requestText("GET", url, token, null)); }
    private JSONObject postJson(String url, String token, JSONObject payload) throws Exception { return new JSONObject(requestText("POST", url, token, payload)); }
    private JSONObject putJson(String url, String token, JSONObject payload) throws Exception { return new JSONObject(requestText("PUT", url, token, payload)); }
    private JSONObject patchJson(String url, String token, JSONObject payload) throws Exception { return new JSONObject(requestText("PATCH", url, token, payload)); }

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
            if (status < 200 || status >= 300) throw new IOException("Sheets HTTP " + status + ": " + abbreviate(body));
            return body == null || body.trim().isEmpty() ? "{}" : body;
        } finally {
            connection.disconnect();
        }
    }

    private static JSONObject baseResult(String toolName, boolean ok) throws Exception {
        return new JSONObject().put("tool", toolName).put("ok", ok).put("error", "").put("detail", "");
    }
    private static JSONObject toolError(String toolName, String error, String detail) { JSONObject json = new JSONObject(); try { json.put("tool", toolName).put("ok", false).put("error", error).put("detail", detail == null ? "" : detail); } catch (Exception ignored) {} return json; }
    private static String cleanArg(JSONObject arguments, String name) { return arguments == null ? "" : arguments.optString(name, "").trim(); }
    private static String escapeQuery(String value) { return value == null ? "" : value.replace("'", "\\'").trim(); }
    private static String joinClauses(List<String> clauses) { StringBuilder b = new StringBuilder(); for (String c : clauses) { if (c == null || c.trim().isEmpty()) continue; if (b.length() > 0) b.append(" and "); b.append(c.trim()); } return b.toString(); }
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
