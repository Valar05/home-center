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

final class GoogleContactsClient {
    private static final String SEARCH_URL = "https://people.googleapis.com/v1/people:searchContacts";
    private static final String PERSON_URL = "https://people.googleapis.com/v1/";
    private final Context context;

    GoogleContactsClient(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject runTool(String toolName, JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, toolName);
        if (!token.ok) return token.json;
        try {
            if ("contacts.search".equals(toolName)) return searchTool(token.value, arguments);
            if ("contacts.read".equals(toolName)) return readTool(token.value, arguments);
            return toolError(toolName, "unknown_tool", "Android does not expose that Contacts tool.");
        } catch (Exception ex) {
            return toolError(toolName, "contacts_error", safe(ex.getMessage()));
        }
    }

    private JSONObject searchTool(String token, JSONObject arguments) throws Exception {
        String query = cleanArg(arguments, "query");
        if (query.isEmpty()) return toolError("contacts.search", "missing_query", "contacts.search requires query.");
        int pageSize = Math.max(1, Math.min(10, arguments == null ? 5 : arguments.optInt("pageSize", 5)));
        Uri uri = Uri.parse(SEARCH_URL).buildUpon()
                .appendQueryParameter("query", query)
                .appendQueryParameter("pageSize", String.valueOf(pageSize))
                .appendQueryParameter("readMask", "names,emailAddresses,phoneNumbers")
                .build();
        JSONObject result = getJson(uri.toString(), token);
        JSONArray people = result.optJSONArray("results");
        JSONArray contacts = new JSONArray();
        if (people != null) {
            for (int i = 0; i < people.length(); i++) {
                JSONObject person = people.optJSONObject(i) == null ? null : people.optJSONObject(i).optJSONObject("person");
                if (person == null) continue;
                contacts.put(contactSummary(person));
            }
        }
        return baseResult("contacts.search", true).put("contacts", contacts);
    }

    private JSONObject readTool(String token, JSONObject arguments) throws Exception {
        String resourceName = cleanArg(arguments, "resourceName");
        if (resourceName.isEmpty()) return toolError("contacts.read", "missing_resource_name", "contacts.read requires resourceName.");
        Uri uri = Uri.parse(PERSON_URL + Uri.encode(resourceName, "/")).buildUpon()
                .appendQueryParameter("personFields", "names,emailAddresses,phoneNumbers")
                .build();
        JSONObject person = getJson(uri.toString(), token);
        return baseResult("contacts.read", true).put("contact", contactSummary(person));
    }

    private JSONObject contactSummary(JSONObject person) throws Exception {
        JSONObject out = new JSONObject();
        out.put("resourceName", person.optString("resourceName", ""));
        JSONArray names = person.optJSONArray("names");
        if (names != null && names.length() > 0) {
            JSONObject name = names.optJSONObject(0);
            if (name != null) {
                out.put("displayName", name.optString("displayName", ""));
                out.put("givenName", name.optString("givenName", ""));
                out.put("familyName", name.optString("familyName", ""));
            }
        }
        JSONArray emails = person.optJSONArray("emailAddresses");
        JSONArray emailOut = new JSONArray();
        if (emails != null) {
            for (int i = 0; i < emails.length(); i++) {
                JSONObject email = emails.optJSONObject(i);
                if (email == null) continue;
                String value = email.optString("value", "").trim();
                if (!value.isEmpty()) emailOut.put(value);
            }
        }
        out.put("emailAddresses", emailOut);
        if (emailOut.length() > 0) out.put("primaryEmail", emailOut.optString(0, ""));
        JSONArray phones = person.optJSONArray("phoneNumbers");
        JSONArray phoneOut = new JSONArray();
        if (phones != null) {
            for (int i = 0; i < phones.length(); i++) {
                JSONObject phone = phones.optJSONObject(i);
                if (phone == null) continue;
                String value = phone.optString("value", "").trim();
                if (!value.isEmpty()) phoneOut.put(value);
            }
        }
        out.put("phoneNumbers", phoneOut);
        return out;
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

    private JSONObject getJson(String url, String token) throws Exception { return new JSONObject(requestText(url, token)); }

    private String requestText(String url, String token) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        try {
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/json");
            int status = connection.getResponseCode();
            String body = readBody(status >= 400 ? connection.getErrorStream() : connection.getInputStream());
            if (status < 200 || status >= 300) throw new IOException("People API HTTP " + status + ": " + abbreviate(body));
            return body == null || body.trim().isEmpty() ? "{}" : body;
        } finally {
            connection.disconnect();
        }
    }

    private static JSONObject baseResult(String toolName, boolean ok) throws Exception { return new JSONObject().put("tool", toolName).put("ok", ok).put("error", "").put("detail", ""); }
    private static JSONObject toolError(String toolName, String error, String detail) { JSONObject json = new JSONObject(); try { json.put("tool", toolName).put("ok", false).put("error", error == null ? "" : error).put("detail", detail == null ? "" : detail); } catch (Exception ignored) {} return json; }
    private static String cleanArg(JSONObject arguments, String name) { return arguments == null ? "" : arguments.optString(name, "").trim(); }
    private static String readBody(InputStream stream) throws IOException { if (stream == null) return ""; try (InputStream input = new BufferedInputStream(stream); ByteArrayOutputStream output = new ByteArrayOutputStream()) { byte[] buffer = new byte[8192]; int read; while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read); return output.toString("UTF-8"); } }
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
