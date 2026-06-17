package com.dclar.homecenter;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

final class TickTickClient {
    private static final String PROJECTS_URL = "https://api.ticktick.com/open/v1/project";
    private static final String CREATE_TASK_URL = "https://api.ticktick.com/open/v1/task";

    static final class Project {
        final String id;
        final String name;

        Project(String id, String name) {
            this.id = id;
            this.name = name;
        }
    }

    static final class Result {
        final boolean ok;
        final String spokenMessage;
        final String detail;

        Result(boolean ok, String spokenMessage, String detail) {
            this.ok = ok;
            this.spokenMessage = spokenMessage;
            this.detail = detail;
        }
    }

    static final class ListResult {
        final boolean ok;
        final String spokenMessage;
        final String detail;
        final String listName;
        final List<String> items;

        ListResult(boolean ok, String spokenMessage, String detail, String listName, List<String> items) {
            this.ok = ok;
            this.spokenMessage = spokenMessage;
            this.detail = detail;
            this.listName = listName;
            this.items = items;
        }
    }

    Result addItem(String apiToken, String listName, String item) {
        if (apiToken == null || apiToken.trim().isEmpty()) {
            return new Result(false, "Paste your TickTick API token first.", "missing_token");
        }

        try {
            List<Project> projects = fetchProjects(apiToken.trim());
            Project target = findProject(projects, listName);
            if (target == null) {
                String available = describeProjects(projects);
                return new Result(false,
                        "I could not find " + listName + ". I found: " + available + ".",
                        "unknown_list; requested=" + listName + "; available=" + available);
            }
            createTask(apiToken.trim(), target.id, item);
            return new Result(true,
                    item + " added to " + target.name + ".",
                    "created_task");
        } catch (Exception ex) {
            return new Result(false,
                    "TickTick failed: " + shortMessage(ex),
                    ex.getClass().getSimpleName() + ": " + ex.getMessage());
        }
    }

    ListResult fetchListItems(String apiToken, String listName) {
        if (apiToken == null || apiToken.trim().isEmpty()) {
            return new ListResult(false, "Paste your TickTick API token first.", "missing_token", listName, new ArrayList<>());
        }

        try {
            List<Project> projects = fetchProjects(apiToken.trim());
            Project target = findProject(projects, listName);
            if (target == null) {
                String available = describeProjects(projects);
                return new ListResult(false,
                        "I could not find " + listName + ". I found: " + available + ".",
                        "unknown_list; requested=" + listName + "; available=" + available,
                        listName,
                        new ArrayList<>());
            }
            List<String> items = fetchProjectTasks(apiToken.trim(), target.id);
            if (items.isEmpty()) {
                return new ListResult(true,
                        target.name + " is empty.",
                        "empty_list",
                        target.name,
                        items);
            }
            return new ListResult(true,
                    target.name + " has " + items.size() + " items.",
                    "loaded_list",
                    target.name,
                    items);
        } catch (Exception ex) {
            return new ListResult(false,
                    "TickTick failed: " + shortMessage(ex),
                    ex.getClass().getSimpleName() + ": " + ex.getMessage(),
                    listName,
                    new ArrayList<>());
        }
    }

    private List<Project> fetchProjects(String token) throws Exception {
        HttpURLConnection connection = open(PROJECTS_URL, "GET", token);
        int code = connection.getResponseCode();
        String body = readBody(connection, code);
        if (code < 200 || code >= 300) {
            throw new IllegalStateException("project fetch returned " + code + ": " + body);
        }
        JSONArray array = new JSONArray(body);
        List<Project> projects = new ArrayList<>();
        for (int i = 0; i < array.length(); i++) {
            JSONObject obj = array.getJSONObject(i);
            String id = obj.optString("id", obj.optString("projectId", ""));
            String name = obj.optString("name", obj.optString("title", ""));
            if (!id.isEmpty() && !name.isEmpty()) {
                projects.add(new Project(id, name));
            }
        }
        return projects;
    }

    private Project findProject(List<Project> projects, String requestedName) {
        String target = simplifyListName(requestedName);

        for (Project project : projects) {
            if (simplifyListName(project.name).equals(target)) {
                return project;
            }
        }

        for (Project project : projects) {
            String candidate = simplifyListName(project.name);
            if (candidate.contains(target) || target.contains(candidate)) {
                return project;
            }
        }

        if (target.equals("shopping")) {
            for (Project project : projects) {
                String candidate = simplifyListName(project.name);
                if (candidate.contains("shopping") || candidate.contains("grocery")
                        || candidate.contains("grocerie")) {
                    return project;
                }
            }
        }
        return null;
    }

    private String describeProjects(List<Project> projects) {
        if (projects.isEmpty()) {
            return "no TickTick lists";
        }
        StringBuilder builder = new StringBuilder();
        int limit = Math.min(projects.size(), 8);
        for (int i = 0; i < limit; i++) {
            if (i > 0) {
                builder.append(", ");
            }
            builder.append(projects.get(i).name);
        }
        if (projects.size() > limit) {
            builder.append(", and ").append(projects.size() - limit).append(" more");
        }
        return builder.toString();
    }

    private List<String> fetchProjectTasks(String token, String projectId) throws Exception {
        HttpURLConnection connection = open(PROJECTS_URL + "/" + projectId + "/data", "GET", token);
        int code = connection.getResponseCode();
        String body = readBody(connection, code);
        if (code < 200 || code >= 300) {
            throw new IllegalStateException("project data returned " + code + ": " + body);
        }

        List<String> items = new ArrayList<>();
        JSONObject data = new JSONObject(body);
        JSONArray tasks = data.optJSONArray("tasks");
        if (tasks == null) {
            tasks = data.optJSONArray("syncTaskBean");
        }
        if (tasks == null) {
            return items;
        }

        for (int i = 0; i < tasks.length(); i++) {
            JSONObject task = tasks.optJSONObject(i);
            if (task == null) {
                continue;
            }
            if (isCompleted(task)) {
                continue;
            }
            String title = task.optString("title", task.optString("content", "")).trim();
            if (!title.isEmpty()) {
                items.add(title);
            }
        }
        return items;
    }

    private boolean isCompleted(JSONObject task) {
        if (task.optBoolean("completed", false)) {
            return true;
        }
        int status = task.optInt("status", 0);
        return status == 2 || status == 1 && task.has("completedTime");
    }

    private void createTask(String token, String projectId, String item) throws Exception {
        HttpURLConnection connection = open(CREATE_TASK_URL, "POST", token);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setDoOutput(true);
        JSONObject body = new JSONObject();
        body.put("title", item);
        body.put("projectId", projectId);
        BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(connection.getOutputStream(), StandardCharsets.UTF_8));
        writer.write(body.toString());
        writer.flush();
        writer.close();

        int code = connection.getResponseCode();
        String response = readBody(connection, code);
        if (code < 200 || code >= 300) {
            throw new IllegalStateException("task create returned " + code + ": " + response);
        }
    }

    private HttpURLConnection open(String url, String method, String token) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(20000);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Authorization", "Bearer " + token);
        return connection;
    }

    private String readBody(HttpURLConnection connection, int code) throws Exception {
        InputStream stream = code >= 400 ? connection.getErrorStream() : connection.getInputStream();
        if (stream == null) {
            return "";
        }
        BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8));
        StringBuilder builder = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            builder.append(line);
        }
        reader.close();
        return builder.toString();
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().replaceAll("\\s+", " ").toLowerCase(Locale.US);
    }

    private String simplifyListName(String value) {
        String cleaned = normalize(value)
                .replaceAll("[^a-z0-9 ]", " ")
                .replaceAll("\\s+", " ")
                .trim();
        if (cleaned.endsWith(" list")) {
            cleaned = cleaned.substring(0, cleaned.length() - 5).trim();
        }
        if (cleaned.equals("shopping list") || cleaned.equals("groceries") || cleaned.equals("grocery")) {
            return "shopping";
        }
        return cleaned;
    }

    private String shortMessage(Exception ex) {
        String message = ex.getMessage();
        if (message == null || message.trim().isEmpty()) {
            return "unknown error";
        }
        if (message.length() > 120) {
            return message.substring(0, 117) + "...";
        }
        return message;
    }
}
