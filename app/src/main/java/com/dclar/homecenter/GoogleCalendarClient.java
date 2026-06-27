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

final class GoogleCalendarClient {
    private static final String BASE_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events";
    private final Context context;

    GoogleCalendarClient(Context context) {
        this.context = context.getApplicationContext();
    }

    JSONObject runTool(String toolName, JSONObject arguments, GoogleSignInAccount account) {
        TokenResult token = tokenForTool(account, toolName);
        if (!token.ok) return token.json;
        try {
            if ("calendar.search".equals(toolName)) return searchTool(token.value, arguments);
            if ("calendar.create_event".equals(toolName)) return createEventTool(token.value, arguments);
            if ("calendar.update_event".equals(toolName)) return updateEventTool(token.value, arguments);
            if ("calendar.respond_event".equals(toolName)) return respondEventTool(token.value, arguments, account == null ? "" : account.getEmail());
            return toolError(toolName, "unknown_tool", "Android does not expose that Calendar tool.");
        } catch (Exception ex) {
            return toolError(toolName, "calendar_error", safe(ex.getMessage()));
        }
    }

    private JSONObject searchTool(String token, JSONObject arguments) throws Exception {
        int pageSize = Math.max(1, Math.min(10, arguments == null ? 5 : arguments.optInt("pageSize", 5)));
        Uri.Builder builder = Uri.parse(BASE_URL).buildUpon()
                .appendQueryParameter("singleEvents", "true")
                .appendQueryParameter("orderBy", "startTime")
                .appendQueryParameter("maxResults", String.valueOf(pageSize));
        putQuery(builder, arguments, "query", "q");
        putQuery(builder, arguments, "timeMin", "timeMin");
        putQuery(builder, arguments, "timeMax", "timeMax");
        JSONObject result = getJson(builder.build().toString(), token);
        return baseResult("calendar.search", true).put("events", result.optJSONArray("items") == null ? new JSONArray() : result.optJSONArray("items"));
    }

    private JSONObject createEventTool(String token, JSONObject arguments) throws Exception {
        JSONObject event = eventPatch(arguments);
        String title = cleanArg(arguments, "title");
        String start = cleanArg(arguments, "startTime");
        String end = cleanArg(arguments, "endTime");
        if (title.isEmpty() || start.isEmpty() || end.isEmpty()) return toolError("calendar.create_event", "missing_event_fields", "title, startTime, and endTime are required.");
        event.put("summary", title);
        event.put("start", new JSONObject().put("dateTime", start));
        event.put("end", new JSONObject().put("dateTime", end));
        JSONObject created = postJson(BASE_URL + "?sendUpdates=all", token, event);
        return baseResult("calendar.create_event", true).put("event", created).put("eventId", created.optString("id", ""));
    }

    private JSONObject updateEventTool(String token, JSONObject arguments) throws Exception {
        String eventId = cleanArg(arguments, "eventId");
        if (eventId.isEmpty()) return toolError("calendar.update_event", "missing_event_id", "calendar.update_event requires eventId.");
        JSONObject patch = eventPatch(arguments);
        String title = cleanArg(arguments, "title");
        if (!title.isEmpty()) patch.put("summary", title);
        String start = cleanArg(arguments, "startTime");
        if (!start.isEmpty()) patch.put("start", new JSONObject().put("dateTime", start));
        String end = cleanArg(arguments, "endTime");
        if (!end.isEmpty()) patch.put("end", new JSONObject().put("dateTime", end));
        JSONArray add = arguments == null ? null : arguments.optJSONArray("attendeesToAdd");
        JSONArray remove = arguments == null ? null : arguments.optJSONArray("attendeesToRemove");
        if ((add != null && add.length() > 0) || (remove != null && remove.length() > 0)) {
            JSONObject current = getJson(BASE_URL + "/" + Uri.encode(eventId), token);
            patch.put("attendees", mergeAttendees(current.optJSONArray("attendees"), add, remove));
        }
        JSONObject updated = patchJson(BASE_URL + "/" + Uri.encode(eventId) + "?sendUpdates=all", token, patch);
        return baseResult("calendar.update_event", true).put("event", updated).put("eventId", updated.optString("id", eventId));
    }

    private JSONObject respondEventTool(String token, JSONObject arguments, String email) throws Exception {
        String eventId = cleanArg(arguments, "eventId");
        String response = cleanArg(arguments, "responseStatus");
        if (eventId.isEmpty()) return toolError("calendar.respond_event", "missing_event_id", "calendar.respond_event requires eventId.");
        if (!("accepted".equals(response) || "declined".equals(response) || "tentative".equals(response) || "needsAction".equals(response))) {
            return toolError("calendar.respond_event", "invalid_response", "responseStatus must be accepted, declined, tentative, or needsAction.");
        }
        JSONObject current = getJson(BASE_URL + "/" + Uri.encode(eventId), token);
        JSONArray attendees = current.optJSONArray("attendees");
        if (attendees == null || email == null || email.trim().isEmpty()) return toolError("calendar.respond_event", "attendee_not_found", "Signed-in email is not an attendee on this event.");
        boolean found = false;
        for (int i = 0; i < attendees.length(); i++) {
            JSONObject attendee = attendees.optJSONObject(i);
            if (attendee != null && email.equalsIgnoreCase(attendee.optString("email", ""))) {
                attendee.put("responseStatus", response);
                found = true;
            }
        }
        if (!found) return toolError("calendar.respond_event", "attendee_not_found", "Signed-in email is not an attendee on this event.");
        JSONObject updated = patchJson(BASE_URL + "/" + Uri.encode(eventId) + "?sendUpdates=all", token, new JSONObject().put("attendees", attendees));
        return baseResult("calendar.respond_event", true).put("event", updated).put("eventId", updated.optString("id", eventId));
    }

    private JSONObject eventPatch(JSONObject arguments) throws Exception {
        JSONObject event = new JSONObject();
        putIfNotEmpty(event, "location", cleanArg(arguments, "location"));
        putIfNotEmpty(event, "description", cleanArg(arguments, "description"));
        JSONArray attendees = arguments == null ? null : arguments.optJSONArray("attendees");
        if (attendees != null) event.put("attendees", emailsToAttendees(attendees));
        return event;
    }

    private JSONArray mergeAttendees(JSONArray current, JSONArray add, JSONArray remove) throws Exception {
        JSONArray out = new JSONArray();
        if (current != null) {
            for (int i = 0; i < current.length(); i++) {
                JSONObject attendee = current.optJSONObject(i);
                if (attendee == null) continue;
                String email = attendee.optString("email", "");
                if (!containsEmail(remove, email)) out.put(attendee);
            }
        }
        if (add != null) {
            for (int i = 0; i < add.length(); i++) {
                String email = add.optString(i, "").trim();
                if (!email.isEmpty() && !containsEmail(out, email)) out.put(new JSONObject().put("email", email));
            }
        }
        return out;
    }

    private JSONArray emailsToAttendees(JSONArray emails) throws Exception {
        JSONArray out = new JSONArray();
        for (int i = 0; i < emails.length(); i++) {
            String email = emails.optString(i, "").trim();
            if (!email.isEmpty()) out.put(new JSONObject().put("email", email));
        }
        return out;
    }

    private boolean containsEmail(JSONArray array, String email) {
        if (array == null || email == null) return false;
        for (int i = 0; i < array.length(); i++) {
            Object item = array.opt(i);
            String value = item instanceof JSONObject ? ((JSONObject) item).optString("email", "") : String.valueOf(item);
            if (email.equalsIgnoreCase(value)) return true;
        }
        return false;
    }

    private void putQuery(Uri.Builder builder, JSONObject arguments, String source, String target) {
        String value = cleanArg(arguments, source);
        if (!value.isEmpty()) builder.appendQueryParameter(target, value);
    }

    private void putIfNotEmpty(JSONObject json, String key, String value) throws Exception { if (value != null && !value.trim().isEmpty()) json.put(key, value.trim()); }

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
            if (status < 200 || status >= 300) throw new IOException("Calendar HTTP " + status + ": " + abbreviate(body));
            return body == null || body.trim().isEmpty() ? "{}" : body;
        } finally {
            connection.disconnect();
        }
    }

    private static JSONObject baseResult(String toolName, boolean ok) throws Exception { return new JSONObject().put("tool", toolName).put("ok", ok).put("error", "").put("detail", ""); }
    private static JSONObject toolError(String toolName, String error, String detail) { JSONObject json = new JSONObject(); try { json.put("tool", toolName).put("ok", false).put("error", error).put("detail", detail == null ? "" : detail); } catch (Exception ignored) {} return json; }
    private static String cleanArg(JSONObject arguments, String name) { return arguments == null ? "" : arguments.optString(name, "").trim(); }
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
