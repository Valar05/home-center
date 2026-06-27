package com.dclar.homecenter;

import android.content.Context;

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
    static final String DRIVE_METADATA_SCOPE = "https://www.googleapis.com/auth/drive.metadata.readonly";
    private static final String TOKEN_SCOPE = "oauth2:" + DRIVE_METADATA_SCOPE;
    private static final String FILES_URL = "https://www.googleapis.com/drive/v3/files?pageSize=5&fields=files(id,name,mimeType,modifiedTime)";

    private final Context context;

    GoogleDriveClient(Context context) {
        this.context = context.getApplicationContext();
    }

    DriveResult listFirstFiles(GoogleSignInAccount account) {
        if (account == null || account.getAccount() == null || account.getEmail() == null || account.getEmail().trim().isEmpty()) {
            return DriveResult.error("not_signed_in", "Sign in with Google first.");
        }
        if (!account.getGrantedScopes().contains(new com.google.android.gms.common.api.Scope(DRIVE_METADATA_SCOPE))) {
            return DriveResult.error("drive_scope_missing", "Drive metadata scope is missing. Reopen Google sign-in and approve Drive access.");
        }
        String token;
        try {
            token = GoogleAuthUtil.getToken(context, account.getAccount(), TOKEN_SCOPE);
        } catch (UserRecoverableAuthException ex) {
            return DriveResult.recoverable("drive_scope_recoverable", "Drive permission needs approval: " + safe(ex.getMessage()), ex);
        } catch (IOException ex) {
            return DriveResult.error("token_io_error", "Could not fetch Drive token: " + safe(ex.getMessage()));
        } catch (GoogleAuthException ex) {
            return DriveResult.error("token_auth_error", "Google auth failed for Drive token: " + safe(ex.getMessage()));
        } catch (Exception ex) {
            return DriveResult.error("token_error", "Drive token failed: " + safe(ex.getMessage()));
        }
        if (token == null || token.trim().isEmpty()) {
            return DriveResult.error("token_empty", "Google returned an empty Drive token.");
        }
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(FILES_URL).openConnection();
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
            return DriveResult.ok(files, files.isEmpty() ? "Drive token worked, but no files were returned." : "Drive token worked.");
        } catch (Exception ex) {
            return DriveResult.error("drive_request_error", "Drive API request failed: " + safe(ex.getMessage()));
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
