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
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

final class GoogleDriveClient {
    static final String DRIVE_METADATA_SCOPE = "https://www.googleapis.com/auth/drive.readonly";
    private static final String TOKEN_SCOPE = "oauth2:" + DRIVE_METADATA_SCOPE;
    private static final String FILES_URL = "https://www.googleapis.com/drive/v3/files";
    private static final String FOLDER_MIME_TYPE = "application/vnd.google-apps.folder";

    private final Context context;

    GoogleDriveClient(Context context) {
        this.context = context.getApplicationContext();
    }

    DriveResult listFirstFiles(GoogleSignInAccount account) {
        return inspect(account, "");
    }

    JSONObject runTool(String toolName, JSONObject arguments, GoogleSignInAccount account) {
        if ("drive.search".equals(toolName)) {
            return searchTool(arguments, account);
        }
        if ("drive.read".equals(toolName)) {
            return readTool(arguments, account);
        }
        return toolError(toolName, "unknown_tool", "Android does not expose that tool.");
    }

    private JSONObject searchTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "drive.search");
        if (!token.ok) {
            return token.json;
        }
        String queryText = cleanArg(arguments, "query");
        String folderName = cleanArg(arguments, "folderName");
        String mimeType = cleanArg(arguments, "mimeType");
        int pageSize = Math.max(1, Math.min(10, arguments == null ? 5 : arguments.optInt("pageSize", 5)));
        String parentId = "";
        if (!folderName.isEmpty()) {
            DriveResult folders = requestFiles(token.value, "mimeType='" + FOLDER_MIME_TYPE + "' and name contains '" + escapeQuery(folderName) + "' and trashed=false", "", 5);
            if (!folders.ok) {
                return resultJson("drive.search", false, folders.error, folders.detail, folders.files, "");
            }
            if (folders.files.isEmpty()) {
                return resultJson("drive.search", true, "", "No folder matched " + folderName + ".", folders.files, "");
            }
            parentId = folders.files.get(0).id;
        }
        List<String> clauses = new ArrayList<>();
        clauses.add("trashed=false");
        if (!parentId.isEmpty()) {
            clauses.add("'" + escapeQuery(parentId) + "' in parents");
        }
        if (!queryText.isEmpty()) {
            clauses.add("name contains '" + escapeQuery(queryText) + "'");
        }
        if (!mimeType.isEmpty()) {
            clauses.add("mimeType='" + escapeQuery(mimeType) + "'");
        }
        DriveResult result = requestFiles(token.value, joinClauses(clauses), "", pageSize);
        return resultJson("drive.search", result.ok, result.error, result.detail, result.files, "");
    }

    private JSONObject readTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "drive.read");
        if (!token.ok) {
            return token.json;
        }
        String fileId = cleanArg(arguments, "fileId");
        if (fileId.isEmpty()) {
            return toolError("drive.read", "missing_file_id", "drive.read requires fileId from a prior drive.search result.");
        }
        String name = cleanArg(arguments, "name");
        String mimeType = cleanArg(arguments, "mimeType");
        if (mimeType.isEmpty()) {
            mimeType = "application/vnd.google-apps.document";
        }
        try {
            DriveFile file = new DriveFile(fileId, name, mimeType, "");
            return resultJson("drive.read", true, "", "", new ArrayList<>(), readDocumentText(token.value, file))
                    .put("file", fileJson(file));
        } catch (Exception ex) {
            return toolError("drive.read", "document_read_error", safe(ex.getMessage()));
        }
    }

    DriveResult inspect(GoogleSignInAccount account, String requestText) {
        if (account == null || account.getAccount() == null || account.getEmail() == null || account.getEmail().trim().isEmpty()) {
            return DriveResult.error("not_signed_in", "Sign in with Google first.");
        }
        if (!account.getGrantedScopes().contains(new com.google.android.gms.common.api.Scope(DRIVE_METADATA_SCOPE))) {
            return DriveResult.error("drive_scope_missing", "Drive metadata scope is missing. Reopen Google sign-in and approve Drive access.");
        }
        String token;
        try {
            token = accessToken(account);
        } catch (DriveRecoverableException ex) {
            return DriveResult.recoverable("drive_scope_recoverable", "Drive permission needs approval: " + safe(ex.getMessage()), ex.exception);
        } catch (DriveRuntimeException ex) {
            return DriveResult.error(ex.code, ex.getMessage());
        }
        if (token == null || token.trim().isEmpty()) {
            return DriveResult.error("token_empty", "Google returned an empty Drive token.");
        }
        return requestFiles(token, "trashed=false", "Drive token worked. First files:");
    }

    private String accessToken(GoogleSignInAccount account) {
        try {
            return GoogleAuthUtil.getToken(context, account.getAccount(), TOKEN_SCOPE);
        } catch (UserRecoverableAuthException ex) {
            throw new DriveRecoverableException(ex);
        } catch (IOException ex) {
            throw new DriveRuntimeException("token_io_error", "Could not fetch Drive token: " + safe(ex.getMessage()));
        } catch (GoogleAuthException ex) {
            throw new DriveRuntimeException("token_auth_error", "Google auth failed for Drive token: " + safe(ex.getMessage()));
        } catch (Exception ex) {
            throw new DriveRuntimeException("token_error", "Drive token failed: " + safe(ex.getMessage()));
        }
    }

    private DriveResult requestFiles(String token, String query, String detail) {
        return requestFiles(token, query, detail, 5);
    }

    private DriveResult requestFiles(String token, String query, String detail, int pageSize) {
        HttpURLConnection connection = null;
        try {
            Uri.Builder builder = Uri.parse(FILES_URL).buildUpon()
                    .appendQueryParameter("pageSize", String.valueOf(Math.max(1, Math.min(10, pageSize))))
                    .appendQueryParameter("fields", "files(id,name,mimeType,modifiedTime)")
                    .appendQueryParameter("orderBy", "modifiedTime desc")
                    .appendQueryParameter("supportsAllDrives", "true")
                    .appendQueryParameter("includeItemsFromAllDrives", "true");
            if (query != null && !query.trim().isEmpty()) {
                builder.appendQueryParameter("q", query);
            }
            connection = (HttpURLConnection) new URL(builder.build().toString()).openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/json");
            int status = connection.getResponseCode();
            String body = readBody(status >= 400 ? connection.getErrorStream() : connection.getInputStream());
            if (status < 200 || status >= 300) {
                return DriveResult.error("http_" + status, "Drive API HTTP " + status + ": " + abbreviate(body));
            }
            return DriveResult.ok(parseFiles(body), detail);
        } catch (DriveRecoverableException ex) {
            return DriveResult.recoverable("drive_scope_recoverable", "Drive permission needs approval: " + safe(ex.getMessage()), ex.exception);
        } catch (DriveRuntimeException ex) {
            return DriveResult.error(ex.code, ex.getMessage());
        } catch (Exception ex) {
            return DriveResult.error("drive_request_error", "Drive API request failed: " + safe(ex.getMessage()));
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private TokenResult tokenForTool(GoogleSignInAccount account, String toolName) {
        if (account == null || account.getAccount() == null || account.getEmail() == null || account.getEmail().trim().isEmpty()) {
            return TokenResult.error(toolError(toolName, "not_signed_in", "Sign in with Google first."));
        }
        if (!account.getGrantedScopes().contains(new com.google.android.gms.common.api.Scope(DRIVE_METADATA_SCOPE))) {
            return TokenResult.error(toolError(toolName, "drive_scope_missing", "Drive readonly scope is missing. Reopen Google sign-in and approve Drive access."));
        }
        try {
            String token = accessToken(account);
            if (token == null || token.trim().isEmpty()) {
                return TokenResult.error(toolError(toolName, "token_empty", "Google returned an empty Drive token."));
            }
            return TokenResult.ok(token);
        } catch (DriveRecoverableException ex) {
            return TokenResult.error(toolError(toolName, "drive_scope_recoverable", "Drive permission needs approval: " + safe(ex.getMessage())));
        } catch (DriveRuntimeException ex) {
            return TokenResult.error(toolError(toolName, ex.code, ex.getMessage()));
        }
    }

    private static String cleanArg(JSONObject arguments, String name) {
        return arguments == null ? "" : arguments.optString(name, "").trim();
    }

    private static String joinClauses(List<String> clauses) {
        StringBuilder builder = new StringBuilder();
        for (String clause : clauses) {
            if (clause == null || clause.trim().isEmpty()) {
                continue;
            }
            if (builder.length() > 0) {
                builder.append(" and ");
            }
            builder.append(clause.trim());
        }
        return builder.toString();
    }

    private static JSONObject resultJson(String toolName, boolean ok, String error, String detail, List<DriveFile> files, String content) {
        JSONObject json = new JSONObject();
        try {
            json.put("tool", toolName);
            json.put("ok", ok);
            json.put("error", error == null ? "" : error);
            json.put("detail", detail == null ? "" : detail);
            json.put("content", content == null ? "" : content);
            JSONArray fileArray = new JSONArray();
            for (DriveFile file : files) {
                fileArray.put(fileJson(file));
            }
            json.put("files", fileArray);
        } catch (Exception ignored) {
        }
        return json;
    }

    private static JSONObject fileJson(DriveFile file) {
        JSONObject json = new JSONObject();
        try {
            json.put("id", file.id);
            json.put("name", file.name);
            json.put("mimeType", file.mimeType);
            json.put("modifiedTime", file.modifiedTime);
        } catch (Exception ignored) {
        }
        return json;
    }

    private static JSONObject toolError(String toolName, String error, String detail) {
        return resultJson(toolName, false, error, detail, new ArrayList<>(), "");
    }

    private static List<DriveFile> parseFiles(String body) throws Exception {
        JSONObject root = new JSONObject(body);
        JSONArray filesJson = root.optJSONArray("files");
        List<DriveFile> files = new ArrayList<>();
        if (filesJson != null) {
            for (int i = 0; i < filesJson.length(); i++) {
                JSONObject file = filesJson.optJSONObject(i);
                if (file == null) {
                    continue;
                }
                files.add(new DriveFile(
                        file.optString("id", ""),
                        file.optString("name", ""),
                        file.optString("mimeType", ""),
                        file.optString("modifiedTime", "")));
            }
        }
        return files;
    }

    private static String escapeQuery(String value) {
        return value == null ? "" : value.replace("'", "\\'").trim();
    }

    private String readDocumentText(String token, DriveFile file) {
        String path;
        if ("application/vnd.google-apps.document".equals(file.mimeType)) {
            path = FILES_URL + "/" + Uri.encode(file.id) + "/export";
        } else {
            path = FILES_URL + "/" + Uri.encode(file.id);
        }
        HttpURLConnection connection = null;
        try {
            Uri.Builder builder = Uri.parse(path).buildUpon();
            if ("application/vnd.google-apps.document".equals(file.mimeType)) {
                builder.appendQueryParameter("mimeType", "text/plain");
            } else {
                builder.appendQueryParameter("alt", "media");
            }
            connection = (HttpURLConnection) new URL(builder.build().toString()).openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "text/plain");
            int status = connection.getResponseCode();
            String body = readBody(status >= 400 ? connection.getErrorStream() : connection.getInputStream());
            if (status < 200 || status >= 300) {
                throw new DriveRuntimeException("http_" + status, "Drive document read HTTP " + status + ": " + abbreviate(body));
            }
            return body;
        } catch (DriveRuntimeException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new DriveRuntimeException("document_read_error", "Drive document read failed: " + safe(ex.getMessage()));
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static String readBody(InputStream stream) throws IOException {
        if (stream == null) {
            return "";
        }
        try (InputStream input = new BufferedInputStream(stream); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
            return output.toString(StandardCharsets.UTF_8.name());
        }
    }

    private static String abbreviate(String value) {
        String clean = value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
        if (clean.length() > 500) {
            return clean.substring(0, 497) + "...";
        }
        return clean;
    }

    private static String safe(String value) {
        return value == null || value.trim().isEmpty() ? "unknown error" : abbreviate(value);
    }

    private static final class TokenResult {
        final boolean ok;
        final String value;
        final JSONObject json;

        private TokenResult(boolean ok, String value, JSONObject json) {
            this.ok = ok;
            this.value = value == null ? "" : value;
            this.json = json == null ? new JSONObject() : json;
        }

        static TokenResult ok(String value) {
            return new TokenResult(true, value, new JSONObject());
        }

        static TokenResult error(JSONObject json) {
            return new TokenResult(false, "", json);
        }
    }

    private static final class DriveRuntimeException extends RuntimeException {
        final String code;

        DriveRuntimeException(String code, String message) {
            super(message);
            this.code = code;
        }
    }

    private static final class DriveRecoverableException extends RuntimeException {
        final UserRecoverableAuthException exception;

        DriveRecoverableException(UserRecoverableAuthException exception) {
            super(exception == null ? "approval required" : exception.getMessage());
            this.exception = exception;
        }
    }

    static final class DriveAnswer {
        final boolean ok;
        final String error;
        final String answer;
        final String content;
        final String documentId;
        final String documentName;
        final UserRecoverableAuthException recoverableAuthException;

        private DriveAnswer(boolean ok, String error, String answer, String content, String documentId, String documentName, UserRecoverableAuthException recoverableAuthException) {
            this.ok = ok;
            this.error = error;
            this.answer = answer == null ? "" : answer;
            this.content = content == null ? "" : content;
            this.documentId = documentId == null ? "" : documentId;
            this.documentName = documentName == null ? "" : documentName;
            this.recoverableAuthException = recoverableAuthException;
        }

        static DriveAnswer ok(String answer, String content, String documentId, String documentName) {
            return new DriveAnswer(true, "", answer, content, documentId, documentName, null);
        }

        static DriveAnswer error(String error, String detail) {
            return new DriveAnswer(false, error, detail, "", "", "", null);
        }

        static DriveAnswer recoverable(String error, String detail, UserRecoverableAuthException ex) {
            return new DriveAnswer(false, error, detail, "", "", "", ex);
        }
    }

    static final class DriveResult {
        final boolean ok;
        final String error;
        final String detail;
        final List<DriveFile> files;
        final UserRecoverableAuthException recoverableAuthException;

        private DriveResult(boolean ok, String error, String detail, List<DriveFile> files, UserRecoverableAuthException recoverableAuthException) {
            this.ok = ok;
            this.error = error;
            this.detail = detail;
            this.files = files;
            this.recoverableAuthException = recoverableAuthException;
        }

        static DriveResult ok(List<DriveFile> files, String detail) {
            return new DriveResult(true, "", detail, files, null);
        }

        static DriveResult error(String error, String detail) {
            return new DriveResult(false, error, detail, new ArrayList<>(), null);
        }

        static DriveResult recoverable(String error, String detail, UserRecoverableAuthException ex) {
            return new DriveResult(false, error, detail, new ArrayList<>(), ex);
        }
    }

    static final class DriveFile {
        final String id;
        final String name;
        final String mimeType;
        final String modifiedTime;

        DriveFile(String id, String name, String mimeType, String modifiedTime) {
            this.id = id;
            this.name = name;
            this.mimeType = mimeType;
            this.modifiedTime = modifiedTime;
        }
    }
}
