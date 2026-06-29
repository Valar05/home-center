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

final class GoogleDriveClient {
    static final String DRIVE_METADATA_SCOPE = ToolRegistry.DRIVE_SCOPE;
    private static final String FILES_URL = "https://www.googleapis.com/drive/v3/files";
    private static final String FILES_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files";
    private static final String DOCS_URL = "https://docs.googleapis.com/v1/documents";
    private static final String FOLDER_MIME_TYPE = "application/vnd.google-apps.folder";
    private static final String DOC_MIME_TYPE = "application/vnd.google-apps.document";

    private final Context context;

    GoogleDriveClient(Context context) {
        this.context = context.getApplicationContext();
    }

    DriveResult listFirstFiles(GoogleSignInAccount account) {
        return inspect(account, "");
    }

    JSONObject runTool(String toolName, JSONObject arguments, GoogleSignInAccount account) {
        if ("drive.search".equals(toolName)) return searchTool(toolName, arguments, account, "");
        if ("drive.read_metadata".equals(toolName)) return readMetadataTool(arguments, account);
        if ("drive.create_folder".equals(toolName)) return createFolderTool(arguments, account);
        if ("drive.update_metadata".equals(toolName)) return updateMetadataTool(arguments, account);
        if ("drive.upload_file".equals(toolName)) return toolError("drive.upload_file", "attachment_missing", "drive.upload_file requires an attached session file.");
        if ("drive.delete".equals(toolName)) return trashFileTool("drive.delete", arguments, account);
        if ("docs.search".equals(toolName)) return searchTool(toolName, arguments, account, DOC_MIME_TYPE);
        if ("docs.read".equals(toolName)) return readDocTool(arguments, account);
        if ("docs.create".equals(toolName)) return createDocTool(arguments, account);
        if ("docs.update".equals(toolName)) return updateDocTool(arguments, account);
        if ("docs.delete".equals(toolName)) return trashFileTool("docs.delete", arguments, account);
        return toolError(toolName, "unknown_tool", "Android does not expose that Drive or Docs tool.");
    }

    JSONObject uploadAttachedFileTool(JSONObject arguments, GoogleSignInAccount account, JSONObject attachedFile) {
        TokenResult token = tokenForTool(account, "drive.upload_file");
        if (!token.ok) return token.json;
        if (attachedFile == null) return toolError("drive.upload_file", "attachment_missing", "No attached file was available to upload.");
        String uriValue = attachedFile.optString("uri", "");
        if (uriValue.trim().isEmpty()) return toolError("drive.upload_file", "attachment_uri_missing", "The attached file cannot be read.");
        String name = cleanArg(arguments, "name");
        if (name.isEmpty()) name = attachedFile.optString("displayName", "Home Center attachment");
        String mimeType = cleanArg(arguments, "mimeType");
        if (mimeType.isEmpty()) mimeType = attachedFile.optString("mimeType", "application/octet-stream");
        String folderId = cleanArg(arguments, "folderId");
        try {
            JSONObject metadata = new JSONObject().put("name", name);
            if (!folderId.isEmpty()) metadata.put("parents", new JSONArray().put(folderId));
            JSONObject file = multipartUploadFile(token.value, Uri.parse(uriValue), metadata, mimeType);
            return resultJson("drive.upload_file", true, "", "drive_file_uploaded", new ArrayList<>(), "")
                    .put("status", "drive_file_uploaded")
                    .put("file", file)
                    .put("title", file.optString("name", name))
                    .put("webViewLink", file.optString("webViewLink", ""));
        } catch (Exception ex) {
            return toolError("drive.upload_file", "upload_file_error", safe(ex.getMessage()));
        }
    }

    private JSONObject searchTool(String toolName, JSONObject arguments, GoogleSignInAccount account, String fixedMimeType) {
        TokenResult token = tokenForTool(account, toolName);
        if (!token.ok) return token.json;
        String queryText = cleanArg(arguments, "query");
        String folderName = cleanArg(arguments, "folderName");
        String mimeType = fixedMimeType == null || fixedMimeType.isEmpty() ? cleanArg(arguments, "mimeType") : fixedMimeType;
        int pageSize = Math.max(1, Math.min(10, arguments == null ? 5 : arguments.optInt("pageSize", 5)));
        String parentId = "";
        if (!folderName.isEmpty()) {
            DriveResult folders = requestFiles(token.value, "mimeType='" + FOLDER_MIME_TYPE + "' and name contains '" + escapeQuery(folderName) + "' and trashed=false", "", 5);
            if (!folders.ok) return resultJson(toolName, false, folders.error, folders.detail, folders.files, "");
            if (folders.files.isEmpty()) return resultJson(toolName, true, "", "No folder matched " + folderName + ".", folders.files, "");
            parentId = folders.files.get(0).id;
        }
        List<String> clauses = new ArrayList<>();
        clauses.add("trashed=false");
        if (!parentId.isEmpty()) clauses.add("'" + escapeQuery(parentId) + "' in parents");
        if (!queryText.isEmpty()) clauses.add("name contains '" + escapeQuery(queryText) + "'");
        if (!mimeType.isEmpty()) clauses.add("mimeType='" + escapeQuery(mimeType) + "'");
        DriveResult result = requestFiles(token.value, joinClauses(clauses), "", pageSize);
        return resultJson(toolName, result.ok, result.error, result.detail, result.files, "");
    }

    private JSONObject readMetadataTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "drive.read_metadata");
        if (!token.ok) return token.json;
        String fileId = cleanArg(arguments, "fileId");
        if (fileId.isEmpty()) return toolError("drive.read_metadata", "missing_file_id", "drive.read_metadata requires fileId from a prior search result.");
        try {
            JSONObject file = getJson(FILES_URL + "/" + Uri.encode(fileId) + "?fields=id,name,mimeType,modifiedTime,webViewLink,parents", token.value, "application/json");
            return resultJson("drive.read_metadata", true, "", "", new ArrayList<>(), "").put("file", file);
        } catch (Exception ex) {
            return toolError("drive.read_metadata", "read_metadata_error", safe(ex.getMessage()));
        }
    }

    private JSONObject createFolderTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "drive.create_folder");
        if (!token.ok) return token.json;
        String name = cleanArg(arguments, "name");
        String parentId = cleanArg(arguments, "parentId");
        if (name.isEmpty()) return toolError("drive.create_folder", "missing_name", "drive.create_folder requires name.");
        try {
            JSONObject body = new JSONObject().put("name", name).put("mimeType", FOLDER_MIME_TYPE);
            if (!parentId.isEmpty()) body.put("parents", new JSONArray().put(parentId));
            JSONObject file = postJson(FILES_URL + "?fields=id,name,mimeType,webViewLink,parents", token.value, body);
            return resultJson("drive.create_folder", true, "", "drive_folder_created", new ArrayList<>(), "")
                    .put("status", "drive_folder_created")
                    .put("file", file)
                    .put("title", file.optString("name", name));
        } catch (Exception ex) {
            return toolError("drive.create_folder", "create_folder_error", safe(ex.getMessage()));
        }
    }

    private JSONObject updateMetadataTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "drive.update_metadata");
        if (!token.ok) return token.json;
        String fileId = cleanArg(arguments, "fileId");
        if (fileId.isEmpty()) return toolError("drive.update_metadata", "missing_file_id", "drive.update_metadata requires fileId.");
        String name = cleanArg(arguments, "name");
        String addParentId = cleanArg(arguments, "addParentId");
        String removeParentId = cleanArg(arguments, "removeParentId");
        if (name.isEmpty() && addParentId.isEmpty() && removeParentId.isEmpty()) {
            return toolError("drive.update_metadata", "missing_update", "Provide name, addParentId, or removeParentId.");
        }
        try {
            Uri.Builder builder = Uri.parse(FILES_URL + "/" + Uri.encode(fileId)).buildUpon()
                    .appendQueryParameter("fields", "id,name,mimeType,webViewLink,parents");
            if (!addParentId.isEmpty()) builder.appendQueryParameter("addParents", addParentId);
            if (!removeParentId.isEmpty()) builder.appendQueryParameter("removeParents", removeParentId);
            JSONObject patch = new JSONObject();
            if (!name.isEmpty()) patch.put("name", name);
            JSONObject file = patchJson(builder.build().toString(), token.value, patch);
            return resultJson("drive.update_metadata", true, "", "drive_metadata_updated", new ArrayList<>(), "")
                    .put("status", "drive_metadata_updated")
                    .put("file", file)
                    .put("title", file.optString("name", name));
        } catch (Exception ex) {
            return toolError("drive.update_metadata", "update_metadata_error", safe(ex.getMessage()));
        }
    }

    private JSONObject trashFileTool(String toolName, JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, toolName);
        if (!token.ok) return token.json;
        String fileId = cleanArg(arguments, "fileId");
        if (fileId.isEmpty()) return toolError(toolName, "missing_file_id", toolName + " requires fileId.");
        try {
            JSONObject file = patchJson(FILES_URL + "/" + Uri.encode(fileId) + "?fields=id,name,mimeType,trashed,webViewLink", token.value,
                    new JSONObject().put("trashed", true));
            String status = "docs.delete".equals(toolName) ? "google_doc_trashed" : "drive_file_trashed";
            return resultJson(toolName, true, "", status, new ArrayList<>(), "")
                    .put("status", status)
                    .put("file", file)
                    .put("title", file.optString("name", cleanArg(arguments, "name")))
                    .put("webViewLink", file.optString("webViewLink", ""));
        } catch (Exception ex) {
            return toolError(toolName, "trash_file_error", safe(ex.getMessage()));
        }
    }

    private JSONObject readDocTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "docs.read");
        if (!token.ok) return token.json;
        String fileId = cleanArg(arguments, "fileId");
        if (fileId.isEmpty()) return toolError("docs.read", "missing_file_id", "docs.read requires fileId from a prior docs.search result.");
        String name = cleanArg(arguments, "name");
        try {
            DriveFile file = new DriveFile(fileId, name, DOC_MIME_TYPE, "", "");
            return resultJson("docs.read", true, "", "", new ArrayList<>(), readDocumentText(token.value, file)).put("file", fileJson(file));
        } catch (Exception ex) {
            return toolError("docs.read", "document_read_error", safe(ex.getMessage()));
        }
    }

    private JSONObject createDocTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "docs.create");
        if (!token.ok) return token.json;
        String title = cleanArg(arguments, "title");
        String body = cleanArg(arguments, "body");
        String folderId = cleanArg(arguments, "folderId");
        if (title.isEmpty()) title = "Home Center Note";
        try {
            LocalLog.info("agent_trace", "google_docs_api_start tool=docs.create title=" + title);
            JSONObject created = postJson(DOCS_URL, token.value, new JSONObject().put("title", title));
            String documentId = created.optString("documentId", "");
            if (documentId.isEmpty()) return toolError("docs.create", "missing_document_id", "Google Docs did not return documentId.");
            if (!body.isEmpty()) {
                JSONArray requests = new JSONArray().put(new JSONObject().put("insertText", new JSONObject()
                        .put("location", new JSONObject().put("index", 1))
                        .put("text", body)));
                postJson(DOCS_URL + "/" + Uri.encode(documentId) + ":batchUpdate", token.value, new JSONObject().put("requests", requests));
            }
            if (!folderId.isEmpty()) {
                patchJson(FILES_URL + "/" + Uri.encode(documentId) + "?addParents=" + Uri.encode(folderId) + "&fields=id,parents", token.value, new JSONObject());
            }
            JSONObject file = getJson(FILES_URL + "/" + Uri.encode(documentId) + "?fields=id,name,mimeType,webViewLink", token.value, "application/json");
            LocalLog.info("agent_trace", "google_docs_api_success tool=docs.create documentId=" + documentId + " webViewLink=" + file.optString("webViewLink", ""));
            return resultJson("docs.create", true, "", "google_doc_created", new ArrayList<>(), "")
                    .put("status", "google_doc_created")
                    .put("file", file)
                    .put("title", file.optString("name", title))
                    .put("webViewLink", file.optString("webViewLink", ""));
        } catch (Exception ex) {
            LocalLog.warn("agent_trace", "google_docs_api_error tool=docs.create detail=" + safe(ex.getMessage()));
            return toolError("docs.create", "create_doc_error", safe(ex.getMessage()));
        }
    }

    private JSONObject updateDocTool(JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, "docs.update");
        if (!token.ok) return token.json;
        String fileId = cleanArg(arguments, "fileId");
        if (fileId.isEmpty()) return toolError("docs.update", "missing_file_id", "docs.update requires fileId.");
        String appendText = cleanArg(arguments, "appendText");
        String replaceText = cleanArg(arguments, "replaceText");
        String body = cleanArg(arguments, "body");
        if (appendText.isEmpty() && replaceText.isEmpty() && body.isEmpty()) {
            return toolError("docs.update", "missing_update", "Provide appendText, replaceText, or body.");
        }
        try {
            int endIndex = documentEndIndex(token.value, fileId);
            JSONArray requests = new JSONArray();
            if (!body.isEmpty()) {
                if (endIndex > 2) {
                    requests.put(new JSONObject().put("deleteContentRange", new JSONObject()
                            .put("range", new JSONObject().put("startIndex", 1).put("endIndex", endIndex - 1))));
                }
                requests.put(new JSONObject().put("insertText", new JSONObject()
                        .put("location", new JSONObject().put("index", 1))
                        .put("text", body)));
            } else if (!replaceText.isEmpty()) {
                requests.put(new JSONObject().put("replaceAllText", new JSONObject()
                        .put("containsText", new JSONObject().put("text", replaceText).put("matchCase", true))
                        .put("replaceText", appendText)));
            } else {
                String text = appendText.startsWith("\n") ? appendText : "\n" + appendText;
                requests.put(new JSONObject().put("insertText", new JSONObject()
                        .put("location", new JSONObject().put("index", Math.max(1, endIndex - 1)))
                        .put("text", text)));
            }
            postJson(DOCS_URL + "/" + Uri.encode(fileId) + ":batchUpdate", token.value, new JSONObject().put("requests", requests));
            JSONObject file = getJson(FILES_URL + "/" + Uri.encode(fileId) + "?fields=id,name,mimeType,webViewLink", token.value, "application/json");
            return resultJson("docs.update", true, "", "google_doc_updated", new ArrayList<>(), "")
                    .put("status", "google_doc_updated")
                    .put("file", file)
                    .put("title", file.optString("name", ""))
                    .put("webViewLink", file.optString("webViewLink", ""));
        } catch (Exception ex) {
            return toolError("docs.update", "update_doc_error", safe(ex.getMessage()));
        }
    }

    DriveResult inspect(GoogleSignInAccount account, String requestText) {
        if (account == null || account.getAccount() == null || account.getEmail() == null || account.getEmail().trim().isEmpty()) {
            return DriveResult.error("not_signed_in", "Sign in with Google first.");
        }
        if (!account.getGrantedScopes().contains(new com.google.android.gms.common.api.Scope(ToolRegistry.DRIVE_SCOPE))) {
            return DriveResult.error("drive_scope_missing", "Drive scope is missing. Reopen Google sign-in and approve Drive access.");
        }
        try {
            String token = accessToken(account, "drive.search");
            if (token == null || token.trim().isEmpty()) return DriveResult.error("token_empty", "Google returned an empty Drive token.");
            return requestFiles(token, "trashed=false", "Drive token worked. First files:");
        } catch (DriveRecoverableException ex) {
            return DriveResult.recoverable("drive_scope_recoverable", "Drive permission needs approval: " + safe(ex.getMessage()), ex.exception);
        } catch (DriveRuntimeException ex) {
            return DriveResult.error(ex.code, ex.getMessage());
        }
    }

    private String accessToken(GoogleSignInAccount account, String toolName) {
        try {
            return GoogleAuthUtil.getToken(context, account.getAccount(), ToolRegistry.tokenScopeFor(toolName));
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
        try {
            Uri.Builder builder = Uri.parse(FILES_URL).buildUpon()
                    .appendQueryParameter("pageSize", String.valueOf(Math.max(1, Math.min(10, pageSize))))
                    .appendQueryParameter("fields", "files(id,name,mimeType,modifiedTime,webViewLink)")
                    .appendQueryParameter("orderBy", "modifiedTime desc")
                    .appendQueryParameter("supportsAllDrives", "true")
                    .appendQueryParameter("includeItemsFromAllDrives", "true");
            if (query != null && !query.trim().isEmpty()) builder.appendQueryParameter("q", query);
            JSONObject root = getJson(builder.build().toString(), token, "application/json");
            return DriveResult.ok(parseFiles(root), detail);
        } catch (DriveRuntimeException ex) {
            return DriveResult.error(ex.code, ex.getMessage());
        } catch (Exception ex) {
            return DriveResult.error("drive_request_error", "Drive API request failed: " + safe(ex.getMessage()));
        }
    }

    private TokenResult tokenForTool(GoogleSignInAccount account, String toolName) {
        if (account == null || account.getAccount() == null || account.getEmail() == null || account.getEmail().trim().isEmpty()) {
            return TokenResult.error(toolError(toolName, "not_signed_in", "Sign in with Google first."));
        }
        ToolRegistry.ToolDefinition tool = ToolRegistry.definition(toolName);
        if (tool == null) return TokenResult.error(toolError(toolName, "unknown_tool", "Tool is not registered."));
        for (String scope : tool.requiredScopes) {
            if (!account.getGrantedScopes().contains(new com.google.android.gms.common.api.Scope(scope))) {
                return TokenResult.error(toolError(toolName, "scope_missing", "Reconnect Google to approve " + scope + "."));
            }
        }
        try {
            String token = accessToken(account, toolName);
            if (token == null || token.trim().isEmpty()) return TokenResult.error(toolError(toolName, "token_empty", "Google returned an empty token."));
            return TokenResult.ok(token);
        } catch (DriveRecoverableException ex) {
            return TokenResult.error(toolError(toolName, "scope_recoverable", "Google permission needs approval: " + safe(ex.getMessage())));
        } catch (DriveRuntimeException ex) {
            return TokenResult.error(toolError(toolName, ex.code, ex.getMessage()));
        }
    }

    private int documentEndIndex(String token, String documentId) throws Exception {
        JSONObject doc = getJson(DOCS_URL + "/" + Uri.encode(documentId) + "?fields=body(content(endIndex))", token, "application/json");
        JSONArray content = doc.optJSONObject("body") == null ? null : doc.optJSONObject("body").optJSONArray("content");
        int end = 1;
        if (content != null) {
            for (int i = 0; i < content.length(); i++) {
                end = Math.max(end, content.optJSONObject(i) == null ? 1 : content.optJSONObject(i).optInt("endIndex", 1));
            }
        }
        return Math.max(1, end);
    }

    private String readDocumentText(String token, DriveFile file) {
        String path = DOC_MIME_TYPE.equals(file.mimeType) ? FILES_URL + "/" + Uri.encode(file.id) + "/export" : FILES_URL + "/" + Uri.encode(file.id);
        Uri.Builder builder = Uri.parse(path).buildUpon();
        if (DOC_MIME_TYPE.equals(file.mimeType)) builder.appendQueryParameter("mimeType", "text/plain"); else builder.appendQueryParameter("alt", "media");
        return requestText("GET", builder.build().toString(), token, "text/plain", null);
    }

    private JSONObject getJson(String url, String token, String accept) throws Exception {
        String body = requestText("GET", url, token, accept, null);
        return new JSONObject(body == null || body.trim().isEmpty() ? "{}" : body);
    }

    private JSONObject postJson(String url, String token, JSONObject payload) throws Exception {
        String body = requestText("POST", url, token, "application/json", payload == null ? new JSONObject() : payload);
        return new JSONObject(body == null || body.trim().isEmpty() ? "{}" : body);
    }

    private JSONObject patchJson(String url, String token, JSONObject payload) throws Exception {
        String body = requestText("PATCH", url, token, "application/json", payload == null ? new JSONObject() : payload);
        return new JSONObject(body == null || body.trim().isEmpty() ? "{}" : body);
    }

    private JSONObject multipartUploadFile(String token, Uri fileUri, JSONObject metadata, String mimeType) throws Exception {
        String boundary = "home-center-" + System.currentTimeMillis();
        HttpURLConnection connection = null;
        try {
            Uri.Builder builder = Uri.parse(FILES_UPLOAD_URL).buildUpon()
                    .appendQueryParameter("uploadType", "multipart")
                    .appendQueryParameter("fields", "id,name,mimeType,webViewLink,parents");
            connection = (HttpURLConnection) new URL(builder.build().toString()).openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(60000);
            connection.setDoInput(true);
            connection.setDoOutput(true);
            connection.setChunkedStreamingMode(8192);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("Content-Type", "multipart/related; boundary=" + boundary);
            try (OutputStream out = connection.getOutputStream(); InputStream input = context.getContentResolver().openInputStream(fileUri)) {
                if (input == null) throw new IOException("empty file");
                writeUtf8(out, "--" + boundary + "\r\n");
                writeUtf8(out, "Content-Type: application/json; charset=UTF-8\r\n\r\n");
                writeUtf8(out, metadata.toString());
                writeUtf8(out, "\r\n--" + boundary + "\r\n");
                writeUtf8(out, "Content-Type: " + (mimeType == null || mimeType.trim().isEmpty() ? "application/octet-stream" : mimeType.trim()) + "\r\n\r\n");
                byte[] buffer = new byte[8192];
                int read;
                while ((read = input.read(buffer)) != -1) {
                    out.write(buffer, 0, read);
                }
                writeUtf8(out, "\r\n--" + boundary + "--\r\n");
            }
            int status = connection.getResponseCode();
            String body = readBody(status >= 400 ? connection.getErrorStream() : connection.getInputStream());
            if (status < 200 || status >= 300) {
                throw new DriveRuntimeException("http_" + status, "Google Drive upload HTTP " + status + ": " + abbreviate(body));
            }
            return new JSONObject(body == null || body.trim().isEmpty() ? "{}" : body);
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static void writeUtf8(OutputStream out, String text) throws IOException {
        out.write((text == null ? "" : text).getBytes(StandardCharsets.UTF_8));
    }

    private String requestText(String method, String url, String token, String accept, JSONObject payload) {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setRequestMethod(method);
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", accept == null ? "application/json" : accept);
            if (payload != null) {
                byte[] bytes = payload.toString().getBytes(StandardCharsets.UTF_8);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                connection.setFixedLengthStreamingMode(bytes.length);
                try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
            }
            int status = connection.getResponseCode();
            String body = readBody(status >= 400 ? connection.getErrorStream() : connection.getInputStream());
            if (status < 200 || status >= 300) throw new DriveRuntimeException("http_" + status, "Google API HTTP " + status + ": " + abbreviate(body));
            return body;
        } catch (DriveRuntimeException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new DriveRuntimeException("request_error", "Google API request failed: " + safe(ex.getMessage()));
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static List<DriveFile> parseFiles(JSONObject root) {
        JSONArray filesJson = root.optJSONArray("files");
        List<DriveFile> files = new ArrayList<>();
        if (filesJson != null) {
            for (int i = 0; i < filesJson.length(); i++) {
                JSONObject file = filesJson.optJSONObject(i);
                if (file == null) continue;
                files.add(new DriveFile(file.optString("id", ""), file.optString("name", ""), file.optString("mimeType", ""), file.optString("modifiedTime", ""), file.optString("webViewLink", "")));
            }
        }
        return files;
    }

    private static String cleanArg(JSONObject arguments, String name) { return arguments == null ? "" : arguments.optString(name, "").trim(); }
    private static String escapeQuery(String value) { return value == null ? "" : value.replace("'", "\\'").trim(); }

    private static String joinClauses(List<String> clauses) {
        StringBuilder builder = new StringBuilder();
        for (String clause : clauses) {
            if (clause == null || clause.trim().isEmpty()) continue;
            if (builder.length() > 0) builder.append(" and ");
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
            for (DriveFile file : files) fileArray.put(fileJson(file));
            json.put("files", fileArray);
        } catch (Exception ignored) {}
        return json;
    }

    private static JSONObject fileJson(DriveFile file) {
        JSONObject json = new JSONObject();
        try {
            json.put("id", file.id);
            json.put("name", file.name);
            json.put("mimeType", file.mimeType);
            json.put("modifiedTime", file.modifiedTime);
            json.put("webViewLink", file.webViewLink);
        } catch (Exception ignored) {}
        return json;
    }

    private static JSONObject toolError(String toolName, String error, String detail) { return resultJson(toolName, false, error, detail, new ArrayList<>(), ""); }

    private static String readBody(InputStream stream) throws IOException {
        if (stream == null) return "";
        try (InputStream input = new BufferedInputStream(stream); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
            return output.toString(StandardCharsets.UTF_8.name());
        }
    }

    private static String abbreviate(String value) {
        String clean = value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
        return clean.length() > 500 ? clean.substring(0, 497) + "..." : clean;
    }

    private static String safe(String value) { return value == null || value.trim().isEmpty() ? "unknown error" : abbreviate(value); }

    private static final class TokenResult {
        final boolean ok;
        final String value;
        final JSONObject json;
        private TokenResult(boolean ok, String value, JSONObject json) { this.ok = ok; this.value = value == null ? "" : value; this.json = json == null ? new JSONObject() : json; }
        static TokenResult ok(String value) { return new TokenResult(true, value, new JSONObject()); }
        static TokenResult error(JSONObject json) { return new TokenResult(false, "", json); }
    }

    private static final class DriveRuntimeException extends RuntimeException {
        final String code;
        DriveRuntimeException(String code, String message) { super(message); this.code = code; }
    }

    private static final class DriveRecoverableException extends RuntimeException {
        final UserRecoverableAuthException exception;
        DriveRecoverableException(UserRecoverableAuthException exception) { super(exception == null ? "approval required" : exception.getMessage()); this.exception = exception; }
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
            this.ok = ok; this.error = error; this.answer = answer == null ? "" : answer; this.content = content == null ? "" : content; this.documentId = documentId == null ? "" : documentId; this.documentName = documentName == null ? "" : documentName; this.recoverableAuthException = recoverableAuthException;
        }
        static DriveAnswer ok(String answer, String content, String documentId, String documentName) { return new DriveAnswer(true, "", answer, content, documentId, documentName, null); }
        static DriveAnswer error(String error, String detail) { return new DriveAnswer(false, error, detail, "", "", "", null); }
        static DriveAnswer recoverable(String error, String detail, UserRecoverableAuthException ex) { return new DriveAnswer(false, error, detail, "", "", "", ex); }
    }

    static final class DriveResult {
        final boolean ok;
        final String error;
        final String detail;
        final List<DriveFile> files;
        final UserRecoverableAuthException recoverableAuthException;
        private DriveResult(boolean ok, String error, String detail, List<DriveFile> files, UserRecoverableAuthException recoverableAuthException) {
            this.ok = ok; this.error = error; this.detail = detail; this.files = files; this.recoverableAuthException = recoverableAuthException;
        }
        static DriveResult ok(List<DriveFile> files, String detail) { return new DriveResult(true, "", detail, files, null); }
        static DriveResult error(String error, String detail) { return new DriveResult(false, error, detail, new ArrayList<>(), null); }
        static DriveResult recoverable(String error, String detail, UserRecoverableAuthException ex) { return new DriveResult(false, error, detail, new ArrayList<>(), ex); }
    }

    static final class DriveFile {
        final String id;
        final String name;
        final String mimeType;
        final String modifiedTime;
        final String webViewLink;
        DriveFile(String id, String name, String mimeType, String modifiedTime, String webViewLink) {
            this.id = id; this.name = name; this.mimeType = mimeType; this.modifiedTime = modifiedTime; this.webViewLink = webViewLink;
        }
    }
}
