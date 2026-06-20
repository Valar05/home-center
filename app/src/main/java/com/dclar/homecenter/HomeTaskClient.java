package com.dclar.homecenter;

import com.google.firebase.Timestamp;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.DocumentReference;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.QuerySnapshot;
import com.google.firebase.firestore.SetOptions;
import com.google.android.gms.tasks.Task;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;

final class HomeTaskClient {
    interface ResultCallback {
        void onResult(Result result);
    }

    interface ListCallback {
        void onResult(ListResult result);
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

    static final class HomeTask {
        final String id;
        final String name;
        final String displayName;
        final String description;
        final String jsonText;
        final Timestamp dueAt;
        final Timestamp createdAt;

        HomeTask(String id, String name, String displayName, String description, String jsonText, Timestamp dueAt, Timestamp createdAt) {
            this.id = id;
            this.name = name;
            this.displayName = displayName;
            this.description = description;
            this.jsonText = jsonText;
            this.dueAt = dueAt;
            this.createdAt = createdAt;
        }
    }

    static final class ListResult {
        final boolean ok;
        final String spokenMessage;
        final String detail;
        final String listName;
        final List<HomeTask> tasks;

        ListResult(boolean ok, String spokenMessage, String detail, String listName, List<HomeTask> tasks) {
            this.ok = ok;
            this.spokenMessage = spokenMessage;
            this.detail = detail;
            this.listName = listName;
            this.tasks = tasks;
        }
    }

    private final FirebaseAuth auth;
    private final FirebaseFirestore db;

    HomeTaskClient(FirebaseAuth auth, FirebaseFirestore db) {
        this.auth = auth;
        this.db = db;
    }

    String currentUserLabel() {
        FirebaseUser user = auth.getCurrentUser();
        if (user == null) {
            return "not signed in";
        }
        if (user.getEmail() != null && !user.getEmail().isEmpty()) {
            return user.getEmail();
        }
        if (user.getDisplayName() != null && !user.getDisplayName().isEmpty()) {
            return user.getDisplayName();
        }
        return user.getUid();
    }

    void joinHousehold(String bucketCode, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        ensureHouseholdMembership(householdRef, bucketCode, bucketId, user)
                .addOnSuccessListener(ignored -> {
                    LocalLog.info("firebase.joinHousehold", "joined bucket=" + bucketId);
                    callback.onResult(new Result(true,
                            "Joined household bucket " + bucketCode.trim() + ".",
                            "joined_bucket=" + bucketId));
                })
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.joinHousehold", "bucket=" + bucketId, ex);
                    callback.onResult(new Result(false,
                            "Could not join household: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                });
    }


    void createList(String bucketCode, String listName, String visibility, String groupName, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String normalizedListName = normalizeListName(listName);
        String listId = listId(normalizedListName);
        String cleanVisibility = normalizeVisibility(visibility);
        String groupId = groupId(groupName);
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new Result(false, "List name is required.", "missing_list"));
            return;
        }
        if (cleanVisibility.equals("group") && groupId.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which family group can use that list.", "missing_group"));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        Map<String, Object> list = listMetadata(normalizedListName, cleanVisibility, groupName, user);
        if (cleanVisibility.equals("group")) {
            DocumentReference groupRef = householdRef.collection("groups").document(groupId);
            Map<String, Object> group = new HashMap<>();
            group.put("name", normalizeGroupName(groupName));
            group.put("createdAt", FieldValue.serverTimestamp());
            group.put("updatedAt", FieldValue.serverTimestamp());
            group.put("createdBy", user.getUid());
            Map<String, Object> member = new HashMap<>();
            member.put("email", user.getEmail());
            member.put("displayName", user.getDisplayName());
            member.put("joinedAt", FieldValue.serverTimestamp());
            ensureHouseholdMembership(householdRef, bucketCode, bucketId, user)
                    .continueWithTask(task -> groupRef.set(group, SetOptions.merge()))
                    .continueWithTask(task -> groupRef.collection("members").document(user.getUid()).set(member, SetOptions.merge()))
                    .continueWithTask(task -> listRef.set(list, SetOptions.merge()))
                    .addOnSuccessListener(ignored -> {
                        LocalLog.info("firebase.createList", "created bucket=" + bucketId + " list=" + listId + " visibility=group group=" + groupId);
                        callback.onResult(new Result(true,
                                normalizedListName + " list created for " + normalizeGroupName(groupName) + " group.",
                                "created_list=" + listId + " visibility=group group=" + groupId));
                    })
                    .addOnFailureListener(ex -> {
                        LocalLog.error("firebase.createList", "bucket=" + bucketId + " list=" + listId + " visibility=" + cleanVisibility, ex);
                        callback.onResult(new Result(false,
                                "Could not create list: " + shortMessage(ex),
                                ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                    });
        } else {
            ensureHouseholdMembership(householdRef, bucketCode, bucketId, user)
                    .continueWithTask(task -> listRef.set(list, SetOptions.merge()))
                    .addOnSuccessListener(ignored -> {
                        LocalLog.info("firebase.createList", "created bucket=" + bucketId + " list=" + listId + " visibility=" + cleanVisibility);
                        callback.onResult(new Result(true,
                                normalizedListName + " list created as " + cleanVisibility + ".",
                                "created_list=" + listId + " visibility=" + cleanVisibility));
                    })
                    .addOnFailureListener(ex -> {
                        LocalLog.error("firebase.createList", "bucket=" + bucketId + " list=" + listId + " visibility=" + cleanVisibility, ex);
                        callback.onResult(new Result(false,
                                "Could not create list: " + shortMessage(ex),
                                ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                    });
        }
    }

    void addTask(String bucketCode, String listName, String name, String description, String jsonText, String dueText, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        String cleanName = name == null ? "" : name.trim();
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which list to use.", "missing_list"));
            return;
        }
        if (cleanName.isEmpty()) {
            callback.onResult(new Result(false, "Task name is required.", "missing_name"));
            return;
        }

        Map<String, Object> parsedJson;
        try {
            parsedJson = parseJsonMap(jsonText);
        } catch (Exception ex) {
            callback.onResult(new Result(false, "The JSON field is not valid.", ex.getMessage()));
            return;
        }

        Timestamp dueAt;
        try {
            dueAt = parseDueAt(dueText);
        } catch (Exception ex) {
            callback.onResult(new Result(false, "I could not understand that date and time.", ex.getMessage()));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        Map<String, Object> task = new HashMap<>();
        task.put("name", cleanName);
        task.put("description", description == null ? "" : description.trim());
        task.put("json", parsedJson);
        task.put("jsonText", jsonText == null ? "" : jsonText.trim());
        task.put("dueAt", dueAt);
        task.put("status", "active");
        task.put("createdAt", FieldValue.serverTimestamp());
        task.put("updatedAt", FieldValue.serverTimestamp());
        task.put("createdBy", user.getUid());
        task.put("completedAt", null);
        task.put("completedBy", null);

        DocumentReference listRef = householdRef.collection("lists").document(listId);
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(t -> listRef.collection("tasks").add(task))
                .addOnSuccessListener(ref -> {
                    LocalLog.info("firebase.addTask", "created bucket=" + bucketId + " list=" + listId + " task=" + ref.getId() + " item=" + cleanName);
                    callback.onResult(new Result(true,
                            cleanName + " added to " + normalizeListName(listName) + ".",
                            "created_home_task=" + ref.getId()));
                })
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.addTask", "bucket=" + bucketId + " list=" + listId + " item=" + cleanName, ex);
                    callback.onResult(new Result(false,
                            "Could not add task: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                });
    }

    void loadActiveTasks(String bucketCode, String listName, ListCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        if (user == null) {
            callback.onResult(new ListResult(false, "Sign in with Google first.", "missing_auth", listName, new ArrayList<>()));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new ListResult(false, "Enter a household bucket code first.", "missing_bucket", listName, new ArrayList<>()));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new ListResult(false, "Tell me which list to read.", "missing_list", listName, new ArrayList<>()));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(task -> listRef.get())
                .addOnSuccessListener(listSnapshot -> listRef.collection("tasks")
                        .whereEqualTo("status", "active")
                        .get()
                        .addOnSuccessListener(snapshot -> callback.onResult(toListResult(snapshot, normalizeListName(listName), listSnapshot)))
                        .addOnFailureListener(ex -> {
                            LocalLog.error("firebase.loadActiveTasks", "bucket=" + bucketId + " list=" + listId, ex);
                            callback.onResult(new ListResult(false,
                                    "Could not read list: " + shortMessage(ex),
                                    ex.getClass().getSimpleName() + ": " + ex.getMessage(),
                                    listName,
                                    new ArrayList<>()));
                        }))
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.loadActiveTasks", "bucket=" + bucketId + " list=" + listId, ex);
                    callback.onResult(new ListResult(false,
                            "Could not read list: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage(),
                            listName,
                            new ArrayList<>()));
                });
    }

    void markDone(String bucketCode, String listName, HomeTask task, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (task == null || task.id == null || task.id.isEmpty()) {
            callback.onResult(new Result(false, "No current task is selected.", "missing_task"));
            return;
        }
        Map<String, Object> update = new HashMap<>();
        update.put("status", "done");
        update.put("completedAt", FieldValue.serverTimestamp());
        update.put("completedBy", user.getUid());
        update.put("updatedAt", FieldValue.serverTimestamp());
        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(taskBeforeWrite -> listRef.collection("tasks").document(task.id).set(update, SetOptions.merge()))
                .addOnSuccessListener(ignored -> callback.onResult(new Result(true,
                        task.name + " marked done.",
                        "completed_task=" + task.id)))
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.markDone", "bucket=" + bucketId + " list=" + listId + " task=" + task.id, ex);
                    callback.onResult(new Result(false,
                            "Could not mark done: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                });
    }


    void removeTaskByName(String bucketCode, String listName, String itemName, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        String normalizedListName = normalizeListName(listName);
        String cleanItem = itemName == null ? "" : itemName.trim();
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which list to change.", "missing_list"));
            return;
        }
        if (cleanItem.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which item to remove.", "missing_item"));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(task -> listRef.get())
                .addOnSuccessListener(listSnapshot -> listRef.collection("tasks")
                        .whereEqualTo("status", "active")
                        .get()
                        .addOnSuccessListener(snapshot -> {
                            ListResult listResult = toListResult(snapshot, normalizedListName, listSnapshot);
                            if (listResult.tasks.isEmpty()) {
                                callback.onResult(new Result(false,
                                        normalizedListName + " is empty.",
                                        "empty_list"));
                                return;
                            }
                            Match match = bestMatch(cleanItem, listResult.tasks);
                    if (match.task == null || match.score < 58) {
                        callback.onResult(new Result(false,
                                "I could not find " + cleanItem + " on " + normalizedListName + ".",
                                "no_match score=" + match.score));
                        return;
                    }
                            if (match.ambiguous) {
                                callback.onResult(new Result(false,
                                        "I found more than one close match: " + match.task.name + " and " + match.runnerUp.name + ". Please be more specific.",
                                        "ambiguous_match score=" + match.score + " runner_up=" + match.runnerUpScore));
                                return;
                            }

                            Map<String, Object> update = new HashMap<>();
                            update.put("status", "removed");
                            update.put("removedAt", FieldValue.serverTimestamp());
                            update.put("removedBy", user.getUid());
                            update.put("updatedAt", FieldValue.serverTimestamp());
                            db.collection("households").document(bucketId)
                                    .collection("lists").document(listId)
                                    .collection("tasks").document(match.task.id)
                                    .set(update, SetOptions.merge())
                                    .addOnSuccessListener(ignored -> callback.onResult(new Result(true,
                                            match.task.name + " removed from " + normalizedListName + ".",
                                            "removed_task=" + match.task.id + " match_score=" + match.score)))
                                    .addOnFailureListener(ex -> {
                                        LocalLog.error("firebase.removeTask", "bucket=" + bucketId + " list=" + listId + " task=" + match.task.id, ex);
                                        callback.onResult(new Result(false,
                                                "Could not remove task: " + shortMessage(ex),
                                                ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                                    });
                        })
                        .addOnFailureListener(ex -> {
                            LocalLog.error("firebase.removeTaskLoad", "bucket=" + bucketId + " list=" + listId + " item=" + cleanItem, ex);
                            callback.onResult(new Result(false,
                                    "Could not read list: " + shortMessage(ex),
                                    ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                        }));
    }

    void savePreference(String bucketCode, String listName, String itemName, String preferredLabel, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        String itemKey = itemFieldKey(itemName);
        String canonicalName = normalizeItem(itemName);
        String cleanLabel = preferredLabel == null ? "" : preferredLabel.trim();
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which list to update.", "missing_list"));
            return;
        }
        if (itemKey.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which item preference to save.", "missing_item"));
            return;
        }
        if (cleanLabel.isEmpty()) {
            callback.onResult(new Result(false, "Tell me the preferred grocery label.", "missing_preference"));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        Map<String, Object> record = new HashMap<>();
        record.put("canonicalName", canonicalName);
        record.put("preferredLabel", cleanLabel);
        record.put("updatedAt", FieldValue.serverTimestamp());
        record.put("updatedBy", user.getUid());
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(task -> listRef.set(java.util.Collections.singletonMap("itemPreferences", java.util.Collections.singletonMap(itemKey, record)), SetOptions.merge()))
                .addOnSuccessListener(ignored -> callback.onResult(new Result(true,
                        canonicalName + " preference saved as " + cleanLabel + ".",
                        "saved_preference=" + itemKey)))
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.savePreference", "bucket=" + bucketId + " list=" + listId + " item=" + canonicalName, ex);
                    callback.onResult(new Result(false,
                            "Could not save preference: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                });
    }

    void saveStoreTarget(String bucketCode, String listName, String itemName, String targetText, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        String itemKey = itemFieldKey(itemName);
        String canonicalName = normalizeItem(itemName);
        StoreTargetSpec target = parseStoreTargetSpec(targetText);
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which list to update.", "missing_list"));
            return;
        }
        if (itemKey.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which item to map.", "missing_item"));
            return;
        }
        if (target.sku.isEmpty() && target.productUrl.isEmpty()) {
            callback.onResult(new Result(false, "Tell me the Walmart SKU, product URL, or target spec.", "missing_store_target"));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        Map<String, Object> record = new HashMap<>();
        record.put("store", "walmart");
        record.put("canonicalName", canonicalName);
        putIfNotEmpty(record, "sku", target.sku);
        putIfNotEmpty(record, "productName", target.productName);
        putIfNotEmpty(record, "productUrl", target.productUrl);
        putIfNotEmpty(record, "unitPreference", target.unitPreference);
        putIfNotEmpty(record, "source", target.source);
        putIfNotEmpty(record, "confidence", target.confidence);
        if (target.quantity > 0) {
            record.put("quantity", target.quantity);
        }
        record.put("confirmedAt", FieldValue.serverTimestamp());
        record.put("updatedAt", FieldValue.serverTimestamp());
        record.put("updatedBy", user.getUid());
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(task -> listRef.set(java.util.Collections.singletonMap("storeTargets", java.util.Collections.singletonMap(itemKey, record)), SetOptions.merge()))
                .addOnSuccessListener(ignored -> callback.onResult(new Result(true,
                        canonicalName + " Walmart target saved.",
                        "saved_store_target=" + itemKey + " sku=" + target.sku + " url=" + target.productUrl)))
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.saveStoreTarget", "bucket=" + bucketId + " list=" + listId + " item=" + canonicalName, ex);
                    callback.onResult(new Result(false,
                            "Could not save Walmart mapping: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                });
    }

    private static final class StoreTargetSpec {
        String sku = "";
        String productName = "";
        String productUrl = "";
        int quantity = 0;
        String unitPreference = "";
        String source = "manual";
        String confidence = "confirmed";
    }

    private StoreTargetSpec parseStoreTargetSpec(String value) {
        StoreTargetSpec spec = new StoreTargetSpec();
        String clean = value == null ? "" : value.trim();
        if (clean.isEmpty()) {
            return spec;
        }
        if (!clean.contains("=") && !clean.contains("|")) {
            spec.sku = clean;
            return spec;
        }
        String[] parts = clean.split("\\|");
        for (String part : parts) {
            int eq = part.indexOf('=');
            if (eq <= 0) {
                continue;
            }
            String key = part.substring(0, eq).trim().toLowerCase(Locale.US).replaceAll("[^a-z0-9]", "");
            String partValue = part.substring(eq + 1).trim();
            if (key.equals("sku") || key.equals("productid") || key.equals("itemid")) {
                spec.sku = partValue;
            } else if (key.equals("producturl") || key.equals("url") || key.equals("link")) {
                spec.productUrl = partValue;
            } else if (key.equals("productname") || key.equals("name") || key.equals("title")) {
                spec.productName = partValue;
            } else if (key.equals("quantity") || key.equals("qty")) {
                spec.quantity = parsePositiveInt(partValue);
            } else if (key.equals("unitpreference") || key.equals("unit") || key.equals("quantitytext")) {
                spec.unitPreference = partValue;
            } else if (key.equals("source")) {
                spec.source = partValue;
            } else if (key.equals("confidence")) {
                spec.confidence = partValue;
            }
        }
        if (spec.sku.isEmpty() && !spec.productUrl.isEmpty()) {
            java.util.regex.Matcher matcher = java.util.regex.Pattern.compile("/ip/(?:[^/]+/)?([0-9]+)").matcher(spec.productUrl);
            if (matcher.find()) {
                spec.sku = matcher.group(1);
            }
        }
        return spec;
    }

    private int parsePositiveInt(String value) {
        try {
            int parsed = Integer.parseInt(value.trim());
            return parsed > 0 ? parsed : 0;
        } catch (Exception ex) {
            return 0;
        }
    }

    private void putIfNotEmpty(Map<String, Object> record, String key, String value) {
        if (value != null && !value.trim().isEmpty()) {
            record.put(key, value.trim());
        }
    }

    void readPreferences(String bucketCode, String listName, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        String normalizedListName = normalizeListName(listName);
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which list to read.", "missing_list"));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(task -> listRef.get())
                .addOnSuccessListener(snapshot -> callback.onResult(new Result(true,
                        summarizePreferenceCounts(snapshot, normalizedListName),
                        formatPreferenceSummary(snapshot, normalizedListName))))
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.readPreferences", "bucket=" + bucketId + " list=" + listId, ex);
                    callback.onResult(new Result(false,
                            "Could not read preferences: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                });
    }

    void buildCartDraft(String bucketCode, String listName, ResultCallback callback) {
        FirebaseUser user = auth.getCurrentUser();
        String bucketId = bucketId(bucketCode);
        String listId = listId(listName);
        String normalizedListName = normalizeListName(listName);
        if (user == null) {
            callback.onResult(new Result(false, "Sign in with Google first.", "missing_auth"));
            return;
        }
        if (bucketId.isEmpty()) {
            callback.onResult(new Result(false, "Enter a household bucket code first.", "missing_bucket"));
            return;
        }
        if (listId.isEmpty()) {
            callback.onResult(new Result(false, "Tell me which list to export.", "missing_list"));
            return;
        }

        DocumentReference householdRef = db.collection("households").document(bucketId);
        DocumentReference listRef = householdRef.collection("lists").document(listId);
        ensureListForAccess(householdRef, listRef, bucketCode, bucketId, listName, user)
                .continueWithTask(task -> listRef.get())
                .addOnSuccessListener(listSnapshot -> listRef.collection("tasks")
                        .whereEqualTo("status", "active")
                        .get()
                        .addOnSuccessListener(snapshot -> callback.onResult(buildCartDraftResult(snapshot, listSnapshot, bucketId, normalizedListName)))
                        .addOnFailureListener(ex -> {
                            LocalLog.error("firebase.buildCartDraft", "bucket=" + bucketId + " list=" + listId, ex);
                            callback.onResult(new Result(false,
                                    "Could not read active items: " + shortMessage(ex),
                                    ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                        }))
                .addOnFailureListener(ex -> {
                    LocalLog.error("firebase.buildCartDraftList", "bucket=" + bucketId + " list=" + listId, ex);
                    callback.onResult(new Result(false,
                            "Could not prepare cart draft: " + shortMessage(ex),
                            ex.getClass().getSimpleName() + ": " + ex.getMessage()));
                });
    }

    private ListResult toListResult(QuerySnapshot snapshot, String listName, DocumentSnapshot listSnapshot) {

        List<HomeTask> tasks = new ArrayList<>();
        for (DocumentSnapshot doc : snapshot.getDocuments()) {
            String name = doc.getString("name");
            if (name == null || name.trim().isEmpty()) {
                continue;
            }
            String cleanName = name.trim();
            tasks.add(new HomeTask(
                    doc.getId(),
                    cleanName,
                    resolveDisplayName(listSnapshot, cleanName),
                    value(doc.getString("description")),
                    value(doc.getString("jsonText")),
                    doc.getTimestamp("dueAt"),
                    doc.getTimestamp("createdAt")));
        }
        Collections.sort(tasks, taskComparator());
        if (tasks.isEmpty()) {
            return new ListResult(true, listName + " is empty.", "empty_list", listName, tasks);
        }
        return new ListResult(true, listName + " has " + tasks.size() + " active tasks.", "loaded_home_list", listName, tasks);
    }

    private String itemFieldKey(String value) {
        String cleaned = normalizeItem(value).replaceAll("[^a-z0-9]+", "_").replaceAll("_+", "_");
        cleaned = cleaned.replaceAll("^_", "").replaceAll("_$", "");
        return cleaned;
    }

    private String resolveDisplayName(DocumentSnapshot listSnapshot, String itemName) {
        String key = itemFieldKey(itemName);
        if (key.isEmpty() || listSnapshot == null || !listSnapshot.exists()) {
            return itemName;
        }
        Map<String, Object> prefs = nestedMap(listSnapshot.get("itemPreferences"));
        Map<String, Object> record = nestedMap(prefs.get(key));
        String preferred = value(record.get("preferredLabel")).trim();
        return preferred.isEmpty() ? itemName : preferred;
    }

    private String summarizePreferenceCounts(DocumentSnapshot listSnapshot, String listName) {
        Map<String, Object> prefs = nestedMap(listSnapshot == null ? null : listSnapshot.get("itemPreferences"));
        Map<String, Object> targets = nestedMap(listSnapshot == null ? null : listSnapshot.get("storeTargets"));
        return listName + " has " + prefs.size() + " item preferences and " + targets.size() + " Walmart mappings.";
    }

    private String formatPreferenceSummary(DocumentSnapshot listSnapshot, String listName) {
        Map<String, Object> prefs = nestedMap(listSnapshot == null ? null : listSnapshot.get("itemPreferences"));
        Map<String, Object> targets = nestedMap(listSnapshot == null ? null : listSnapshot.get("storeTargets"));
        StringBuilder builder = new StringBuilder();
        builder.append(listName).append(" preferences");
        if (prefs.isEmpty() && targets.isEmpty()) {
            builder.append("\nNo grocery preferences are saved yet.");
            return builder.toString();
        }
        if (!prefs.isEmpty()) {
            builder.append("\nItem preferences:");
            ArrayList<String> keys = new ArrayList<>(prefs.keySet());
            Collections.sort(keys);
            for (String key : keys) {
                Map<String, Object> record = nestedMap(prefs.get(key));
                String canonical = value(record.get("canonicalName"));
                String preferred = value(record.get("preferredLabel"));
                builder.append("\n- ").append(canonical.isEmpty() ? key : canonical);
                if (!preferred.isEmpty()) {
                    builder.append(" -> ").append(preferred);
                }
            }
        }
        if (!targets.isEmpty()) {
            builder.append("\nWalmart mappings:");
            ArrayList<String> keys = new ArrayList<>(targets.keySet());
            Collections.sort(keys);
            for (String key : keys) {
                Map<String, Object> record = nestedMap(targets.get(key));
                String canonical = value(record.get("canonicalName"));
                String sku = value(record.get("sku"));
                String productName = value(record.get("productName"));
                String quantity = value(record.get("quantity"));
                builder.append("\n- ").append(canonical.isEmpty() ? key : canonical).append(" -> SKU ").append(sku);
                if (!productName.isEmpty()) {
                    builder.append(" (").append(productName).append(")");
                }
                if (!quantity.isEmpty()) {
                    builder.append(" x ").append(quantity);
                }
            }
        }
        return builder.toString();
    }

    private Result buildCartDraftResult(QuerySnapshot snapshot, DocumentSnapshot listSnapshot, String bucketId, String listName) {
        try {
            JSONArray items = new JSONArray();
            JSONArray unmapped = new JSONArray();
            Map<String, Object> prefs = nestedMap(listSnapshot == null ? null : listSnapshot.get("itemPreferences"));
            Map<String, Object> targets = nestedMap(listSnapshot == null ? null : listSnapshot.get("storeTargets"));
            int mappedCount = 0;
            for (DocumentSnapshot doc : snapshot.getDocuments()) {
                String rawName = value(doc.getString("name")).trim();
                if (rawName.isEmpty()) {
                    continue;
                }
                String key = itemFieldKey(rawName);
                Map<String, Object> prefRecord = nestedMap(prefs.get(key));
                Map<String, Object> targetRecord = nestedMap(targets.get(key));
                String preferredLabel = value(prefRecord.get("preferredLabel")).trim();
                String displayName = preferredLabel.isEmpty() ? rawName : preferredLabel;
                String sku = value(targetRecord.get("sku")).trim();
                String productName = value(targetRecord.get("productName")).trim();
                String productUrl = value(targetRecord.get("productUrl")).trim();
                String quantity = value(targetRecord.get("quantity")).trim();
                String unitPreference = value(targetRecord.get("unitPreference")).trim();
                String source = value(targetRecord.get("source")).trim();
                String confidence = value(targetRecord.get("confidence")).trim();
                String storeName = value(targetRecord.get("store")).trim();
                boolean mapped = !sku.isEmpty();
                if (mapped) {
                    mappedCount++;
                } else {
                    unmapped.put(displayName);
                }
                JSONObject item = new JSONObject();
                item.put("name", rawName);
                item.put("preferredLabel", displayName);
                item.put("store", storeName.isEmpty() ? "walmart" : storeName);
                item.put("sku", sku);
                item.put("productName", productName);
                item.put("productUrl", productUrl);
                item.put("quantity", quantity);
                item.put("unitPreference", unitPreference);
                item.put("source", source);
                item.put("confidence", confidence);
                item.put("mapped", mapped);
                item.put("taskId", doc.getId());
                items.put(item);
            }

            JSONObject root = new JSONObject();
            root.put("bucketId", bucketId);
            root.put("listName", listName);
            root.put("generatedAt", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(new Date()));
            root.put("itemCount", items.length());
            root.put("mappedCount", mappedCount);
            root.put("unmappedCount", unmapped.length());
            root.put("unmappedItems", unmapped);
            root.put("items", items);
            return new Result(true,
                    "Built a Walmart cart draft for " + items.length() + " item" + (items.length() == 1 ? "" : "s") + ". " + unmapped.length() + " need store mappings.",
                    root.toString(2));
        } catch (Exception ex) {
            LocalLog.error("firebase.buildCartDraftResult", "bucket=" + bucketId + " list=" + listName, ex);
            return new Result(false,
                    "Could not build cart draft: " + shortMessage(ex),
                    ex.getClass().getSimpleName() + ": " + ex.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> nestedMap(Object value) {
        if (value instanceof Map) {
            return (Map<String, Object>) value;
        }
        return new HashMap<>();
    }

    private Comparator<HomeTask> taskComparator() {
        return (a, b) -> {
            int due = compareNullableTimestamp(a.dueAt, b.dueAt);
            if (due != 0) {
                return due;
            }
            return compareNullableTimestamp(a.createdAt, b.createdAt);
        };
    }

    private int compareNullableTimestamp(Timestamp a, Timestamp b) {
        if (a == null && b == null) {
            return 0;
        }
        if (a == null) {
            return 1;
        }
        if (b == null) {
            return -1;
        }
        return a.compareTo(b);
    }


    private static final class Match {
        final HomeTask task;
        final int score;
        final HomeTask runnerUp;
        final int runnerUpScore;
        final boolean ambiguous;

        Match(HomeTask task, int score, HomeTask runnerUp, int runnerUpScore, boolean ambiguous) {
            this.task = task;
            this.score = score;
            this.runnerUp = runnerUp;
            this.runnerUpScore = runnerUpScore;
            this.ambiguous = ambiguous;
        }
    }

    private Match bestMatch(String query, List<HomeTask> tasks) {
        HomeTask best = null;
        HomeTask second = null;
        int bestScore = 0;
        int secondScore = 0;
        for (HomeTask task : tasks) {
            int score = matchScore(query, task.name);
            if (score > bestScore) {
                second = best;
                secondScore = bestScore;
                best = task;
                bestScore = score;
            } else if (score > secondScore) {
                second = task;
                secondScore = score;
            }
        }
        boolean ambiguous = best != null && second != null && bestScore < 95 && secondScore >= 58 && bestScore - secondScore < 8;
        return new Match(best, bestScore, second, secondScore, ambiguous);
    }

    private int matchScore(String query, String candidate) {
        String left = normalizeItem(query);
        String right = normalizeItem(candidate);
        if (left.isEmpty() || right.isEmpty()) {
            return 0;
        }
        if (left.equals(right)) {
            return 100;
        }
        if (singularize(left).equals(singularize(right))) {
            return 98;
        }
        if (right.contains(left) || left.contains(right)) {
            int diff = Math.abs(right.length() - left.length());
            return Math.max(72, 92 - diff);
        }
        int tokenScore = tokenOverlapScore(left, right);
        int distanceScore = editDistanceScore(left, right);
        return Math.max(tokenScore, distanceScore);
    }

    private int tokenOverlapScore(String left, String right) {
        String[] leftTokens = left.split(" ");
        String[] rightTokens = right.split(" ");
        int matches = 0;
        for (String leftToken : leftTokens) {
            String singularLeft = singularize(leftToken);
            for (String rightToken : rightTokens) {
                if (singularLeft.equals(singularize(rightToken))) {
                    matches++;
                    break;
                }
            }
        }
        int max = Math.max(leftTokens.length, rightTokens.length);
        if (max == 0) {
            return 0;
        }
        return (int) Math.round((matches * 86.0) / max);
    }

    private int editDistanceScore(String left, String right) {
        int max = Math.max(left.length(), right.length());
        if (max == 0) {
            return 0;
        }
        int distance = levenshtein(left, right);
        return Math.max(0, (int) Math.round(100.0 * (max - distance) / max));
    }

    private int levenshtein(String left, String right) {
        int[] costs = new int[right.length() + 1];
        for (int j = 0; j < costs.length; j++) {
            costs[j] = j;
        }
        for (int i = 1; i <= left.length(); i++) {
            costs[0] = i;
            int northwest = i - 1;
            for (int j = 1; j <= right.length(); j++) {
                int current = costs[j];
                int replace = left.charAt(i - 1) == right.charAt(j - 1) ? northwest : northwest + 1;
                costs[j] = Math.min(Math.min(costs[j] + 1, costs[j - 1] + 1), replace);
                northwest = current;
            }
        }
        return costs[right.length()];
    }

    private String normalizeItem(String value) {
        if (value == null) {
            return "";
        }
        String cleaned = value.toLowerCase(Locale.US)
                .replaceAll("[^a-z0-9 ]", " ")
                .replaceAll("\\s+", " ")
                .trim();
        cleaned = cleaned.replaceFirst("^(the|a|an|some)\\s+", "");
        return cleaned;
    }

    private String singularize(String value) {
        if (value == null) {
            return "";
        }
        if (value.endsWith("ies") && value.length() > 3) {
            return value.substring(0, value.length() - 3) + "y";
        }
        if (value.endsWith("es") && value.length() > 3) {
            return value.substring(0, value.length() - 2);
        }
        if (value.endsWith("s") && value.length() > 2) {
            return value.substring(0, value.length() - 1);
        }
        return value;
    }

    private Map<String, Object> parseJsonMap(String jsonText) throws Exception {
        Map<String, Object> empty = new HashMap<>();
        if (jsonText == null || jsonText.trim().isEmpty()) {
            return empty;
        }
        return jsonObjectToMap(new JSONObject(jsonText));
    }

    private Map<String, Object> jsonObjectToMap(JSONObject object) throws Exception {
        Map<String, Object> map = new HashMap<>();
        Iterator<String> keys = object.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            Object value = object.get(key);
            if (value instanceof JSONObject) {
                map.put(key, jsonObjectToMap((JSONObject) value));
            } else if (value instanceof JSONArray) {
                map.put(key, jsonArrayToList((JSONArray) value));
            } else if (value == JSONObject.NULL) {
                map.put(key, null);
            } else {
                map.put(key, value);
            }
        }
        return map;
    }

    private List<Object> jsonArrayToList(JSONArray array) throws Exception {
        List<Object> list = new ArrayList<>();
        for (int i = 0; i < array.length(); i++) {
            Object value = array.get(i);
            if (value instanceof JSONObject) {
                list.add(jsonObjectToMap((JSONObject) value));
            } else if (value instanceof JSONArray) {
                list.add(jsonArrayToList((JSONArray) value));
            } else if (value == JSONObject.NULL) {
                list.add(null);
            } else {
                list.add(value);
            }
        }
        return list;
    }

    private Timestamp parseDueAt(String dueText) throws ParseException {
        if (dueText == null || dueText.trim().isEmpty()) {
            return null;
        }
        String value = dueText.trim();
        String[] patterns = {"yyyy-MM-dd HH:mm", "yyyy-MM-dd h:mm a", "yyyy-MM-dd"};
        for (String pattern : patterns) {
            try {
                SimpleDateFormat format = new SimpleDateFormat(pattern, Locale.US);
                format.setLenient(false);
                Date date = format.parse(value);
                if (date != null) {
                    return new Timestamp(date);
                }
            } catch (ParseException ignored) {
            }
        }
        throw new ParseException("Use YYYY-MM-DD or YYYY-MM-DD HH:MM", 0);
    }


    private Task<Void> ensureListForAccess(DocumentReference householdRef, DocumentReference listRef, String bucketCode, String bucketId, String listName, FirebaseUser user) {
        return ensureHouseholdMembership(householdRef, bucketCode, bucketId, user)
                .continueWithTask(task -> {
                    Map<String, Object> list = new HashMap<>();
                    list.put("name", normalizeListName(listName));
                    list.put("updatedAt", FieldValue.serverTimestamp());
                    LocalLog.info("firebase.ensureList", "bucket=" + bucketId + " list=" + listRef.getId());
                    return listRef.set(list, SetOptions.merge());
                });
    }

    private Task<Void> ensureHouseholdMembership(DocumentReference householdRef, String bucketCode, String bucketId, FirebaseUser user) {
        Map<String, Object> household = new HashMap<>();
        household.put("name", bucketCode.trim());
        household.put("updatedAt", FieldValue.serverTimestamp());
        household.put("createdBy", user.getUid());
        household.put("createdAt", FieldValue.serverTimestamp());

        Map<String, Object> member = new HashMap<>();
        member.put("email", user.getEmail());
        member.put("displayName", user.getDisplayName());
        member.put("role", "member");
        member.put("joinedAt", FieldValue.serverTimestamp());

        return householdRef.collection("members").document(user.getUid()).set(member, SetOptions.merge())
                .continueWithTask(task -> {
                    LocalLog.info("firebase.ensureMembership", "bucket=" + bucketId + " member=" + user.getUid());
                    return householdRef.set(household, SetOptions.merge());
                });
    }

    private Map<String, Object> listMetadata(String listName, String visibility, String groupName, FirebaseUser user) {
        Map<String, Object> list = new HashMap<>();
        list.put("name", normalizeListName(listName));
        list.put("visibility", normalizeVisibility(visibility));
        list.put("ownerUid", user.getUid());
        list.put("updatedAt", FieldValue.serverTimestamp());
        list.put("createdAt", FieldValue.serverTimestamp());
        if (normalizeVisibility(visibility).equals("group")) {
            list.put("groupId", groupId(groupName));
            list.put("groupName", normalizeGroupName(groupName));
        } else {
            list.put("groupId", "");
            list.put("groupName", "");
        }
        return list;
    }

    private String normalizeVisibility(String visibility) {
        String cleaned = visibility == null ? "" : visibility.trim().toLowerCase(Locale.US);
        if (cleaned.equals("private")) {
            return "personal";
        }
        if (cleaned.equals("shared") || cleaned.equals("family")) {
            return "household";
        }
        if (cleaned.equals("personal") || cleaned.equals("group") || cleaned.equals("household")) {
            return cleaned;
        }
        return "household";
    }

    private String groupId(String groupName) {
        return normalizeGroupName(groupName).replaceAll("[^a-z0-9_-]", "-").replaceAll("-+", "-");
    }

    private String normalizeGroupName(String value) {
        String cleaned = value == null ? "" : value.trim().replaceAll("\\s+", " ").toLowerCase(Locale.US);
        cleaned = cleaned.replaceFirst("^(the|a|an|my|our)\\s+", "");
        cleaned = cleaned.replaceFirst("\\s+(group|family)$", "");
        return cleaned.trim();
    }

    private String bucketId(String bucketCode) {
        if (bucketCode == null) {
            return "";
        }
        return bucketCode.trim().toLowerCase(Locale.US).replaceAll("[^a-z0-9_-]", "-").replaceAll("-+", "-");
    }

    static String listId(String listName) {
        String normalized = normalizeListName(listName);
        return normalized.toLowerCase(Locale.US).replaceAll("[^a-z0-9_-]", "-").replaceAll("-+", "-");
    }

    static String normalizeListName(String value) {
        String cleaned = value == null ? "" : value.trim().replaceAll("\\s+", " ").toLowerCase(Locale.US);
        cleaned = cleaned.replaceFirst("^(the|a|an|my|our)\\s+", "");
        cleaned = cleaned.replaceFirst("\\s+(list|lists)$", "");
        cleaned = cleaned.trim();
        if (cleaned.equals("shopping") || cleaned.equals("shop") || cleaned.equals("groceries") || cleaned.equals("grocery")) {
            return "shopping";
        }
        return cleaned;
    }

    private String value(String text) {
        return text == null ? "" : text;
    }

    private String value(Object text) {
        return text == null ? "" : String.valueOf(text);
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
