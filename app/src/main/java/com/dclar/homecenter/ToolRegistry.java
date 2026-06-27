package com.dclar.homecenter;

import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.common.api.Scope;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

final class ToolRegistry {
    static final String DRIVE_SCOPE = "https://www.googleapis.com/auth/drive";
    static final String DOCS_SCOPE = "https://www.googleapis.com/auth/documents";
    static final String GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify";
    static final String GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose";
    static final String GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send";
    static final String CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events";

    private ToolRegistry() {
    }

    static List<ToolDefinition> allTools() {
        List<ToolDefinition> tools = new ArrayList<>();
        tools.add(new ToolDefinition("drive.search", "Search or list Google Drive files.", "drive", false, false,
                Arrays.asList(DRIVE_SCOPE), Arrays.asList("query", "folderName", "mimeType", "pageSize")));
        tools.add(new ToolDefinition("drive.read", "Read text content from a Google Drive file by fileId.", "drive", false, false,
                Arrays.asList(DRIVE_SCOPE), Arrays.asList("fileId", "mimeType", "name")));
        tools.add(new ToolDefinition("drive.create_doc", "Create a Google Doc and optionally insert body text.", "drive", true, true,
                Arrays.asList(DRIVE_SCOPE, DOCS_SCOPE), Arrays.asList("title", "body", "folderId")));
        tools.add(new ToolDefinition("drive.update_doc", "Update a Google Doc by appending, replacing, or replacing the body.", "drive", true, true,
                Arrays.asList(DRIVE_SCOPE, DOCS_SCOPE), Arrays.asList("fileId", "name", "appendText", "replaceText", "body")));

        tools.add(new ToolDefinition("gmail.search", "Search Gmail messages.", "gmail", false, false,
                Arrays.asList(GMAIL_MODIFY_SCOPE), Arrays.asList("query", "pageSize")));
        tools.add(new ToolDefinition("gmail.read", "Read a Gmail message by messageId.", "gmail", false, false,
                Arrays.asList(GMAIL_MODIFY_SCOPE), Arrays.asList("messageId")));
        tools.add(new ToolDefinition("gmail.create_draft", "Create a Gmail draft.", "gmail", true, false,
                Arrays.asList(GMAIL_COMPOSE_SCOPE), Arrays.asList("to", "cc", "bcc", "subject", "body")));
        tools.add(new ToolDefinition("gmail.update_draft", "Update a Gmail draft.", "gmail", true, false,
                Arrays.asList(GMAIL_COMPOSE_SCOPE), Arrays.asList("draftId", "to", "cc", "bcc", "subject", "body")));
        tools.add(new ToolDefinition("gmail.send_draft", "Send an existing Gmail draft.", "gmail", true, true,
                Arrays.asList(GMAIL_SEND_SCOPE), Arrays.asList("draftId")));
        tools.add(new ToolDefinition("gmail.send_email", "Send an email.", "gmail", true, true,
                Arrays.asList(GMAIL_SEND_SCOPE), Arrays.asList("to", "cc", "bcc", "subject", "body")));

        tools.add(new ToolDefinition("calendar.search", "Search Google Calendar events.", "calendar", false, false,
                Arrays.asList(CALENDAR_EVENTS_SCOPE), Arrays.asList("query", "timeMin", "timeMax", "pageSize")));
        tools.add(new ToolDefinition("calendar.create_event", "Create a Google Calendar event.", "calendar", true, true,
                Arrays.asList(CALENDAR_EVENTS_SCOPE), Arrays.asList("title", "startTime", "endTime", "attendees", "location", "description")));
        tools.add(new ToolDefinition("calendar.update_event", "Update a Google Calendar event.", "calendar", true, true,
                Arrays.asList(CALENDAR_EVENTS_SCOPE), Arrays.asList("eventId", "title", "startTime", "endTime", "attendeesToAdd", "attendeesToRemove", "location", "description")));
        tools.add(new ToolDefinition("calendar.respond_event", "RSVP to a Google Calendar event for the signed-in account.", "calendar", true, true,
                Arrays.asList(CALENDAR_EVENTS_SCOPE), Arrays.asList("eventId", "responseStatus")));

        tools.add(new ToolDefinition("lists.read", "Read active Home Center list items.", "lists", false, false,
                Collections.emptyList(), Arrays.asList("listName")));
        tools.add(new ToolDefinition("lists.create", "Create a Home Center list.", "lists", true, false,
                Collections.emptyList(), Arrays.asList("listName")));
        tools.add(new ToolDefinition("lists.add_item", "Add an item to a Home Center list.", "lists", true, false,
                Collections.emptyList(), Arrays.asList("listName", "text")));
        tools.add(new ToolDefinition("lists.update_item", "Update a Home Center list item text or status.", "lists", true, false,
                Collections.emptyList(), Arrays.asList("listName", "itemId", "itemText", "text", "status")));
        tools.add(new ToolDefinition("lists.mark_done", "Mark a Home Center list item done.", "lists", true, false,
                Collections.emptyList(), Arrays.asList("listName", "itemId", "itemText")));
        tools.add(new ToolDefinition("lists.remove_item", "Soft-remove a Home Center list item by setting status removed.", "lists", true, false,
                Collections.emptyList(), Arrays.asList("listName", "itemId", "itemText")));
        return tools;
    }

    static JSONArray availableTools(GoogleSignInAccount account, boolean listsAvailable) {
        JSONArray array = new JSONArray();
        for (ToolDefinition tool : allTools()) {
            if (tool.isAvailable(account, listsAvailable)) {
                array.put(tool.toJson());
            }
        }
        return array;
    }

    static JSONArray unavailableToolGroups(GoogleSignInAccount account, boolean listsAvailable) {
        JSONArray array = new JSONArray();
        addUnavailableGroup(array, "drive", account, Arrays.asList(DRIVE_SCOPE, DOCS_SCOPE));
        addUnavailableGroup(array, "gmail", account, Arrays.asList(GMAIL_MODIFY_SCOPE, GMAIL_COMPOSE_SCOPE, GMAIL_SEND_SCOPE));
        addUnavailableGroup(array, "calendar", account, Arrays.asList(CALENDAR_EVENTS_SCOPE));
        if (!listsAvailable) {
            JSONObject group = new JSONObject();
            try {
                group.put("group", "lists");
                group.put("reason", "home_center_not_signed_in");
            } catch (Exception ignored) {
            }
            array.put(group);
        }
        return array;
    }

    static boolean isRegistered(String toolName) {
        return definition(toolName) != null;
    }

    static ToolDefinition definition(String toolName) {
        for (ToolDefinition tool : allTools()) {
            if (tool.name.equals(toolName)) {
                return tool;
            }
        }
        return null;
    }

    static String tokenScopeFor(String toolName) {
        ToolDefinition tool = definition(toolName);
        if (tool == null || tool.requiredScopes.isEmpty()) {
            return "";
        }
        StringBuilder builder = new StringBuilder("oauth2:");
        for (int i = 0; i < tool.requiredScopes.size(); i++) {
            if (i > 0) {
                builder.append(' ');
            }
            builder.append(tool.requiredScopes.get(i));
        }
        return builder.toString();
    }

    static List<Scope> signInScopes() {
        return Arrays.asList(
                new Scope(DRIVE_SCOPE),
                new Scope(DOCS_SCOPE),
                new Scope(GMAIL_MODIFY_SCOPE),
                new Scope(GMAIL_COMPOSE_SCOPE),
                new Scope(GMAIL_SEND_SCOPE),
                new Scope(CALENDAR_EVENTS_SCOPE));
    }

    private static void addUnavailableGroup(JSONArray array, String group, GoogleSignInAccount account, List<String> scopes) {
        List<String> missing = missingScopes(account, scopes);
        if (missing.isEmpty()) {
            return;
        }
        JSONObject json = new JSONObject();
        try {
            json.put("group", group);
            json.put("reason", "missing_scope");
            json.put("missingScopes", new JSONArray(missing));
        } catch (Exception ignored) {
        }
        array.put(json);
    }

    private static List<String> missingScopes(GoogleSignInAccount account, List<String> scopes) {
        List<String> missing = new ArrayList<>();
        for (String scope : scopes) {
            if (account == null || !account.getGrantedScopes().contains(new Scope(scope))) {
                missing.add(scope);
            }
        }
        return missing;
    }

    static final class ToolDefinition {
        final String name;
        final String description;
        final String group;
        final boolean write;
        final boolean confirmationRequired;
        final List<String> requiredScopes;
        final List<String> arguments;

        ToolDefinition(String name, String description, String group, boolean write, boolean confirmationRequired, List<String> requiredScopes, List<String> arguments) {
            this.name = name;
            this.description = description;
            this.group = group;
            this.write = write;
            this.confirmationRequired = confirmationRequired;
            this.requiredScopes = requiredScopes;
            this.arguments = arguments;
        }

        boolean isAvailable(GoogleSignInAccount account, boolean listsAvailable) {
            if ("lists".equals(group)) {
                return listsAvailable;
            }
            return missingScopes(account, requiredScopes).isEmpty();
        }

        JSONObject toJson() {
            JSONObject json = new JSONObject();
            try {
                json.put("name", name);
                json.put("description", description);
                json.put("group", group);
                json.put("write", write);
                json.put("confirmationRequired", confirmationRequired);
                json.put("requiredScopes", new JSONArray(requiredScopes));
                json.put("arguments", new JSONArray(arguments));
            } catch (Exception ignored) {
            }
            return json;
        }
    }
}
