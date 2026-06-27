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

    DriveAnswer answerRequest(GoogleSignInAccount account, String requestText, String lastDocumentId, String lastDocumentName) {
        DriveResult auth = inspect(account, "");
        if (!auth.ok && auth.recoverableAuthException != null) {
            return DriveAnswer.recoverable(auth.error, auth.detail, auth.recoverableAuthException);
        }
        if (!auth.ok) {
            return DriveAnswer.error(auth.error, auth.detail);
        }
        String token;
        try {
            token = accessToken(account);
        } catch (DriveRecoverableException ex) {
            return DriveAnswer.recoverable("drive_scope_recoverable", "Drive permission needs approval: " + safe(ex.getMessage()), ex.exception);
        } catch (DriveRuntimeException ex) {
            return DriveAnswer.error(ex.code, ex.getMessage());
        }
        String value = normalized(requestText);
        boolean wantsContent = value.contains("first sentence")
                || value.contains("summarize")
                || value.contains("summary")
                || value.contains("read chapter")
                || value.startsWith("read ")
                || value.startsWith("open ");
        if (wantsContent) {
            return answerDocumentRequest(token, requestText, lastDocumentId, lastDocumentName);
        }
        return answerFolderOrFileList(token, requestText);
    }

    private DriveAnswer answerFolderOrFileList(String token, String requestText) {
        String folderName = folderNameFrom(requestText);
        DriveResult result;
        if (!folderName.isEmpty()) {
            String folderQuery = "mimeType='" + FOLDER_MIME_TYPE + "' and name contains '" + escapeQuery(folderName) + "' and trashed=false";
            DriveResult folders = requestFiles(token, folderQuery, "");
            if (!folders.ok) {
                return DriveAnswer.error(folders.error, folders.detail);
            }
            if (folders.files.isEmpty()) {
                return DriveAnswer.ok("I could not find a folder named " + folderName + ".", "", "", "");
            }
            DriveFile folder = folders.files.get(0);
            result = requestFiles(token, "'" + escapeQuery(folder.id) + "' in parents and trashed=false", "");
            if (!result.ok) {
                return DriveAnswer.error(result.error, result.detail);
            }
            return DriveAnswer.ok(listAnswer("Found it. It contains:", result.files), "", folder.id, folder.name);
        }
        result = requestFiles(token, "trashed=false", "");
        if (!result.ok) {
            return DriveAnswer.error(result.error, result.detail);
        }
        return DriveAnswer.ok(listAnswer("I found these Drive files:", result.files), "", "", "");
    }

    private DriveAnswer answerDocumentRequest(String token, String requestText, String lastDocumentId, String lastDocumentName) {
        String title = documentTitleFrom(requestText);
        DriveFile doc = null;
        if (!title.isEmpty()) {
            DriveResult search = requestFiles(token, "name contains '" + escapeQuery(title) + "' and trashed=false", "");
            if (!search.ok) {
                return DriveAnswer.error(search.error, search.detail);
            }
            if (!search.files.isEmpty()) {
                doc = search.files.get(0);
            }
        }
        if (doc == null && lastDocumentId != null && !lastDocumentId.trim().isEmpty()) {
            doc = new DriveFile(lastDocumentId, lastDocumentName == null ? "that document" : lastDocumentName, "application/vnd.google-apps.document", "");
        }
        if (doc == null) {
            return DriveAnswer.ok("I could not find that document in Drive.", "", "", "");
        }
        String content = readDocumentText(token, doc);
        if (content.trim().isEmpty()) {
            return DriveAnswer.ok("I found " + cleanName(doc.name) + ", but it did not contain readable text.", "", doc.id, doc.name);
        }
        String value = normalized(requestText);
        if (value.contains("first sentence")) {
            return DriveAnswer.ok("The first sentence is: \"" + firstSentence(content) + "\"", content, doc.id, doc.name);
        }
        if (value.contains("summarize") || value.contains("summary")) {
            return DriveAnswer.ok("Summary: " + simpleSummary(content), content, doc.id, doc.name);
        }
        if (value.contains("chapter")) {
            String chapter = chapterText(content, value);
            return DriveAnswer.ok(chapter.isEmpty() ? "I found " + cleanName(doc.name) + ", but I could not find that chapter." : chapter, content, doc.id, doc.name);
        }
        return DriveAnswer.ok(firstReadableChunk(content), content, doc.id, doc.name);
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
        String folderName = folderNameFrom(requestText);
        if (!folderName.isEmpty()) {
            String folderQuery = "mimeType='" + FOLDER_MIME_TYPE + "' and name contains '" + escapeQuery(folderName) + "' and trashed=false";
            DriveResult folders = requestFiles(token, folderQuery, "Searched Drive folders matching " + folderName + ".");
            if (!folders.ok || folders.files.isEmpty()) {
                return folders.ok
                        ? DriveResult.ok(folders.files, "Drive is connected, but I did not find a folder matching " + folderName + ".")
                        : folders;
            }
            DriveFile folder = folders.files.get(0);
            String childQuery = "'" + escapeQuery(folder.id) + "' in parents and trashed=false";
            return requestFiles(token, childQuery, "Drive folder " + folder.name + " is visible. First files in that folder:");
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
        HttpURLConnection connection = null;
        try {
            Uri.Builder builder = Uri.parse(FILES_URL).buildUpon()
                    .appendQueryParameter("pageSize", "5")
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

    private static String folderNameFrom(String text) {
        String value = text == null ? "" : text.toLowerCase().replaceAll("[^a-z0-9 ]", " ").replaceAll("\\s+", " ").trim();
        int folderAt = value.indexOf(" folder");
        if (folderAt < 0) {
            return "";
        }
        String prefix = value.substring(0, folderAt).trim();
        String[] stopWords = {"can you read", "can you see", "can you open", "do you have access to", "open", "list", "read", "my", "the", "your", "google", "drive"};
        for (String stop : stopWords) {
            prefix = prefix.replace(stop, " ");
        }
        prefix = prefix.replaceAll("\\s+", " ").trim();
        if (prefix.isEmpty()) {
            return "";
        }
        String[] words = prefix.split(" ");
        return words[words.length - 1];
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

    private static String listAnswer(String heading, List<DriveFile> files) {
        if (files.isEmpty()) {
            return heading + "\nNo files found.";
        }
        StringBuilder answer = new StringBuilder(heading);
        for (DriveFile file : files) {
            answer.append("\n- ").append(cleanName(file.name));
        }
        return answer.toString();
    }

    private static String documentTitleFrom(String text) {
        String value = text == null ? "" : text.trim();
        String lower = value.toLowerCase();
        int of = lower.indexOf(" of ");
        if (of >= 0) {
            return cleanTitle(value.substring(of + 4));
        }
        for (String prefix : new String[]{"summarize ", "open ", "read "}) {
            if (lower.startsWith(prefix)) {
                String candidate = value.substring(prefix.length());
                if (!candidate.toLowerCase().startsWith("chapter")) {
                    return cleanTitle(candidate);
                }
            }
        }
        return "";
    }

    private static String cleanTitle(String value) {
        return value == null ? "" : value
                .replaceAll("(?i)\\bin drive\\b", "")
                .replaceAll("(?i)\\bfrom drive\\b", "")
                .replaceAll("[?.!]+$", "")
                .trim();
    }

    private static String firstSentence(String content) {
        String clean = normalizeContent(content);
        int end = sentenceEnd(clean, 0);
        return end <= 0 ? clean : clean.substring(0, Math.min(end + 1, clean.length())).trim();
    }

    private static int sentenceEnd(String clean, int start) {
        for (int i = Math.max(0, start); i < clean.length(); i++) {
            char c = clean.charAt(i);
            if (c == '.' || c == '?' || c == '!') {
                return i;
            }
        }
        return -1;
    }

    private static String simpleSummary(String content) {
        String clean = normalizeContent(content);
        int first = sentenceEnd(clean, 0);
        if (first < 0) {
            return firstReadableChunk(clean);
        }
        int second = sentenceEnd(clean, first + 1);
        if (second < 0) {
            return clean.substring(0, Math.min(first + 1, clean.length())).trim();
        }
        return clean.substring(0, Math.min(second + 1, clean.length())).trim();
    }

    private static String chapterText(String content, String request) {
        String clean = normalizeContent(content);
        String chapter = request.replaceAll(".*chapter\\s+", "").replaceAll("[^a-z0-9].*", "").trim();
        if (chapter.isEmpty()) {
            return "";
        }
        String lower = clean.toLowerCase();
        int start = lower.indexOf("chapter " + chapter);
        if (start < 0 && "three".equals(chapter)) {
            start = lower.indexOf("chapter 3");
        }
        if (start < 0) {
            return "";
        }
        int next = lower.indexOf("chapter ", start + 8);
        String section = next > start ? clean.substring(start, next) : clean.substring(start);
        return firstReadableChunk(section);
    }

    private static String firstReadableChunk(String content) {
        String clean = normalizeContent(content);
        return clean.length() <= 900 ? clean : clean.substring(0, 900).trim() + "...";
    }

    private static String normalizeContent(String content) {
        return content == null ? "" : content.replace('\r', ' ').replace('\n', ' ').replaceAll("\\s+", " ").trim();
    }

    private static String normalized(String content) {
        return content == null ? "" : content.toLowerCase().replaceAll("\\s+", " ").trim();
    }

    private static String cleanName(String name) {
        return name == null || name.trim().isEmpty() ? "Untitled" : name.trim();
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
