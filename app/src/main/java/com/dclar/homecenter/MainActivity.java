package com.dclar.homecenter;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.text.method.SingleLineTransformationMethod;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.google.android.gms.auth.api.signin.GoogleSignIn;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.auth.api.signin.GoogleSignInClient;
import com.google.android.gms.auth.api.signin.GoogleSignInOptions;
import com.google.android.gms.common.api.ApiException;
import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.AuthCredential;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.auth.GoogleAuthProvider;
import com.google.firebase.firestore.FirebaseFirestore;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity implements RecognitionListener {
    private static final int REQUEST_RECORD_AUDIO = 1001;
    private static final int REQUEST_GOOGLE_SIGN_IN = 2001;
    private static final String PREFS = "home_center";
    private static final String KEY_TICKTICK_TOKEN = "ticktick_token";
    private static final String KEY_BUCKET_CODE = "bucket_code";
    private static final String KEY_DEFAULT_LIST = "default_list";

    private TextToSpeech tts;
    private SpeechRecognizer recognizer;
    private AudioManager audioManager;
    private AudioFocusRequest speechFocusRequest;
    private boolean speechFocusHeld = false;
    private String activeSpeechUtteranceId = "";
    private TextView statusView;
    private TextView authStatusView;
    private EditText tokenEdit;
    private EditText bucketEdit;
    private EditText listEdit;
    private EditText listVisibilityEdit;
    private EditText groupNameEdit;
    private EditText taskNameEdit;
    private EditText taskDescriptionEdit;
    private EditText taskJsonEdit;
    private EditText taskDueEdit;
    private Button talkButton;
    private Button repeatButton;
    private Button nextButton;
    private Button previousButton;
    private Button doneButton;
    private Button googleSignInButton;
    private Button joinBucketButton;
    private Button createListButton;
    private Button saveTaskButton;
    private Button tickTickShowButton;

    private boolean tickTickTokenVisible = false;
    private boolean firebaseConfigured = false;
    private boolean silentSignInAttempted = false;
    private FirebaseAuth firebaseAuth;
    private FirebaseFirestore firestore;
    private GoogleSignInClient googleSignInClient;
    private FirebaseAuth.AuthStateListener authStateListener;
    private HomeTaskClient homeTaskClient;
    private String lastSpoken = "Home Center is ready.";
    private String activeReadListName = "";
    private final List<String> activeReadItems = new ArrayList<>();
    private final List<HomeTaskClient.HomeTask> activeHomeTasks = new ArrayList<>();
    private int activeReadIndex = -1;
    private boolean activeReadIsHomeCenter = false;

    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final TickTickClient tickTickClient = new TickTickClient();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LocalLog.init(this);
        LocalLog.info("app", "start");
        initFirebase();
        audioManager = (AudioManager) getSystemService(AUDIO_SERVICE);
        buildUi();
        attachAuthStateListener();
        refreshAuthStatus();
        trySilentGoogleSignIn();
        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                configureTextToSpeech();
                speak("Home Center is ready.");
            }
        });
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            recognizer.setRecognitionListener(this);
        } else {
            setStatus("Speech recognition is not available on this device.");
        }
    }

    private void initFirebase() {
        try {
            if (FirebaseApp.getApps(this).isEmpty()) {
                FirebaseApp.initializeApp(this);
            }
            if (FirebaseApp.getApps(this).isEmpty()) {
                firebaseConfigured = false;
                return;
            }
            String clientId = defaultWebClientId();
            firebaseAuth = FirebaseAuth.getInstance();
            firestore = FirebaseFirestore.getInstance();
            homeTaskClient = new HomeTaskClient(firebaseAuth, firestore);
            firebaseConfigured = clientId != null && !clientId.isEmpty();
            if (firebaseConfigured) {
                GoogleSignInOptions options = new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                        .requestIdToken(clientId)
                        .requestEmail()
                        .build();
                googleSignInClient = GoogleSignIn.getClient(this, options);
            }
        } catch (Exception ex) {
            firebaseConfigured = false;
        }
    }

    private String defaultWebClientId() {
        int id = getResources().getIdentifier("default_web_client_id", "string", getPackageName());
        if (id == 0) {
            return "";
        }
        return getString(id);
    }

    private void attachAuthStateListener() {
        if (!hasHomeClient() || authStateListener != null) {
            return;
        }
        authStateListener = auth -> main.post(() -> {
            refreshAuthStatus();
            if (auth.getCurrentUser() == null) {
                trySilentGoogleSignIn();
            }
        });
        firebaseAuth.addAuthStateListener(authStateListener);
    }

    private void trySilentGoogleSignIn() {
        if (!firebaseConfigured || googleSignInClient == null || firebaseAuth == null) {
            return;
        }
        if (firebaseAuth.getCurrentUser() != null || silentSignInAttempted) {
            refreshAuthStatus();
            return;
        }
        silentSignInAttempted = true;
        appendStatus("Restoring Google sign-in...");
        googleSignInClient.silentSignIn()
                .addOnSuccessListener(account -> signInFirebaseWithGoogle(account, false))
                .addOnFailureListener(ex -> {
                    appendStatus("Google sign-in restore needs the Sign in button once: " + shortMessage(ex.getMessage()));
                    refreshAuthStatus();
                });
    }

    private void signInFirebaseWithGoogle(GoogleSignInAccount account, boolean announce) {
        if (account == null || account.getIdToken() == null) {
            if (announce) {
                speak("Google sign in did not return an identity token.");
            }
            refreshAuthStatus();
            return;
        }
        AuthCredential credential = GoogleAuthProvider.getCredential(account.getIdToken(), null);
        firebaseAuth.signInWithCredential(credential)
                .addOnSuccessListener(result -> {
                    refreshAuthStatus();
                    if (announce) {
                        speak("Signed in with Google.");
                    } else {
                        appendStatus("Google sign-in restored.");
                    }
                })
                .addOnFailureListener(ex -> {
                    refreshAuthStatus();
                    if (announce) {
                        speak("Google sign in failed: " + shortMessage(ex.getMessage()));
                    } else {
                        appendStatus("Google sign-in restore failed: " + shortMessage(ex.getMessage()));
                    }
                });
    }

    private void buildUi() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(20), dp(20), dp(20));
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText("Home Center");
        title.setTextSize(32);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setGravity(Gravity.CENTER);
        root.addView(title, matchWrap());

        talkButton = new Button(this);
        talkButton.setText("Talk");
        talkButton.setTextSize(34);
        talkButton.setAllCaps(false);
        talkButton.setContentDescription("Talk to Home Center");
        root.addView(talkButton, matchHeight(dp(160)));

        repeatButton = button("Repeat", 20, "Repeat the last Home Center response");
        root.addView(repeatButton, matchHeight(dp(64)));

        nextButton = button("Next Item", 24, "Read the next item from the active list");
        nextButton.setEnabled(false);
        root.addView(nextButton, matchHeight(dp(78)));

        previousButton = button("Previous Item", 18, "Read the previous item from the active list");
        previousButton.setEnabled(false);
        root.addView(previousButton, matchHeight(dp(64)));

        doneButton = button("Done", 22, "Mark the current Home Center task done");
        doneButton.setEnabled(false);
        root.addView(doneButton, matchHeight(dp(72)));

        authStatusView = new TextView(this);
        authStatusView.setTextSize(17);
        authStatusView.setGravity(Gravity.CENTER);
        root.addView(authStatusView, matchWrap());

        googleSignInButton = button("Sign in with Google", 18, "Sign in to Home Center sync with Google");
        root.addView(googleSignInButton, matchHeight(dp(68)));

        bucketEdit = singleLineEdit("Household bucket code", prefs.getString(KEY_BUCKET_CODE, ""));
        bucketEdit.setContentDescription("Household bucket code");
        root.addView(bucketEdit, matchHeight(dp(64)));

        joinBucketButton = button("Join Bucket", 18, "Join or create the household bucket");
        root.addView(joinBucketButton, matchHeight(dp(64)));

        listEdit = singleLineEdit("List name", prefs.getString(KEY_DEFAULT_LIST, "shopping"));
        listEdit.setContentDescription("Default list name");
        root.addView(listEdit, matchHeight(dp(64)));

        listVisibilityEdit = singleLineEdit("List visibility: personal, household, or group", "household");
        listVisibilityEdit.setContentDescription("List visibility");
        root.addView(listVisibilityEdit, matchHeight(dp(64)));

        groupNameEdit = singleLineEdit("Family group name, for group lists", "");
        groupNameEdit.setContentDescription("Family group name for group lists");
        root.addView(groupNameEdit, matchHeight(dp(64)));

        createListButton = button("Create List", 18, "Create the named list with selected visibility");
        root.addView(createListButton, matchHeight(dp(68)));

        taskNameEdit = singleLineEdit("Task name", "");
        taskNameEdit.setContentDescription("Task name");
        root.addView(taskNameEdit, matchHeight(dp(64)));

        taskDescriptionEdit = singleLineEdit("Description", "");
        taskDescriptionEdit.setContentDescription("Task description");
        root.addView(taskDescriptionEdit, matchHeight(dp(64)));

        taskJsonEdit = singleLineEdit("JSON, optional", "");
        taskJsonEdit.setContentDescription("Optional task JSON");
        root.addView(taskJsonEdit, matchHeight(dp(64)));

        taskDueEdit = singleLineEdit("Due, optional YYYY-MM-DD HH:MM", "");
        taskDueEdit.setContentDescription("Optional due date and time");
        root.addView(taskDueEdit, matchHeight(dp(64)));

        saveTaskButton = button("Add Home Center Task", 18, "Add task to Home Center shared list");
        root.addView(saveTaskButton, matchHeight(dp(68)));

        TextView tickTitle = new TextView(this);
        tickTitle.setText("Legacy TickTick fallback");
        tickTitle.setTextSize(18);
        tickTitle.setTypeface(Typeface.DEFAULT_BOLD);
        tickTitle.setGravity(Gravity.CENTER);
        root.addView(tickTitle, matchWrap());

        tokenEdit = singleLineEdit("TickTick API token", prefs.getString(KEY_TICKTICK_TOKEN, ""));
        tokenEdit.setContentDescription("TickTick API token");
        tokenEdit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        tokenEdit.setTransformationMethod(PasswordTransformationMethod.getInstance());
        root.addView(tokenEdit, matchHeight(dp(64)));

        LinearLayout tickButtons = new LinearLayout(this);
        tickButtons.setOrientation(LinearLayout.HORIZONTAL);
        tickButtons.setGravity(Gravity.CENTER);
        Button saveTickButton = button("Save TickTick", 16, "Save TickTick token");
        tickTickShowButton = button("Show", 16, "Show or hide TickTick token");
        tickButtons.addView(saveTickButton, weightedHeight(dp(64)));
        tickButtons.addView(tickTickShowButton, weightedHeight(dp(64)));
        root.addView(tickButtons, matchWrap());

        statusView = new TextView(this);
        statusView.setText("Ready. Sign in, join a bucket, then say add eggs to shopping list.\nLogs: " + LocalLog.currentLogPath());
        statusView.setTextSize(18);
        statusView.setGravity(Gravity.CENTER);
        statusView.setPadding(0, dp(12), 0, dp(12));
        root.addView(statusView, matchWrap());

        talkButton.setOnClickListener(v -> startTalkFlow());
        repeatButton.setOnClickListener(v -> speak(lastSpoken));
        nextButton.setOnClickListener(v -> speakNextItem());
        previousButton.setOnClickListener(v -> speakPreviousItem());
        doneButton.setOnClickListener(v -> markCurrentDone());
        googleSignInButton.setOnClickListener(v -> startGoogleSignIn());
        joinBucketButton.setOnClickListener(v -> joinBucket());
        createListButton.setOnClickListener(v -> createListFromFields());
        saveTaskButton.setOnClickListener(v -> saveHomeTaskFromFields());
        saveTickButton.setOnClickListener(v -> {
            prefs.edit().putString(KEY_TICKTICK_TOKEN, tokenEdit.getText().toString().trim()).apply();
            speak("TickTick token saved.");
        });
        tickTickShowButton.setOnClickListener(v -> toggleTickTickTokenVisibility());

        setContentView(scroll);
    }

    private Button button(String text, int size, String description) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextSize(size);
        button.setAllCaps(false);
        button.setContentDescription(description);
        return button;
    }

    private EditText singleLineEdit(String hint, String value) {
        EditText edit = new EditText(this);
        edit.setHint(hint);
        edit.setSingleLine(true);
        edit.setText(value);
        edit.setInputType(InputType.TYPE_CLASS_TEXT);
        return edit;
    }

    private void toggleTickTickTokenVisibility() {
        tickTickTokenVisible = !tickTickTokenVisible;
        if (tickTickTokenVisible) {
            tokenEdit.setTransformationMethod(SingleLineTransformationMethod.getInstance());
            tickTickShowButton.setText("Hide");
        } else {
            tokenEdit.setTransformationMethod(PasswordTransformationMethod.getInstance());
            tickTickShowButton.setText("Show");
        }
        tokenEdit.setSelection(tokenEdit.length());
    }

    private void startGoogleSignIn() {
        if (!firebaseConfigured || googleSignInClient == null) {
            speak("Firebase is not configured. Add google services JSON, rebuild, and try again.");
            return;
        }
        startActivityForResult(googleSignInClient.getSignInIntent(), REQUEST_GOOGLE_SIGN_IN);
    }

    private void joinBucket() {
        saveBucketPrefs();
        if (!hasHomeClient()) {
            speak("Firebase sync is not configured yet.");
            return;
        }
        setStatus("Joining bucket...");
        homeTaskClient.joinHousehold(bucketEdit.getText().toString(), result -> main.post(() -> {
            logResult("joinBucket", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            refreshAuthStatus();
        }));
    }

    private void createListFromFields() {
        saveBucketPrefs();
        createList(Command.createList(
                listEdit.getText().toString(),
                listVisibilityEdit.getText().toString(),
                groupNameEdit.getText().toString(),
                "manual"));
    }

    private void createList(Command command) {
        saveBucketPrefs();
        listEdit.setText(command.listName);
        if (listVisibilityEdit != null && command.state != null && !command.state.isEmpty()) {
            listVisibilityEdit.setText(command.state);
        }
        if (groupNameEdit != null && command.groupName != null && !command.groupName.isEmpty()) {
            groupNameEdit.setText(command.groupName);
        }
        if (!hasSignedInHomeUser()) {
            speak("Sign in with Google first.");
            refreshAuthStatus();
            return;
        }
        if (!hasHomeBucket()) {
            speakMissingBucket();
            return;
        }
        String visibility = command.state == null || command.state.isEmpty() ? "household" : command.state;
        String groupName = command.groupName == null ? "" : command.groupName;
        setBusy(true);
        setStatus("Creating " + command.listName + " list...");
        homeTaskClient.createList(bucketEdit.getText().toString(), command.listName, visibility, groupName, result -> main.post(() -> {
            setBusy(false);
            logResult("createList", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (!result.ok) {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
        }));
    }

    private void saveHomeTaskFromFields() {
        saveBucketPrefs();
        if (!hasSignedInHomeUser()) {
            speak("Sign in with Google first.");
            refreshAuthStatus();
            return;
        }
        if (!hasHomeBucket()) {
            speakMissingBucket();
            return;
        }
        addHomeTask(
                listEdit.getText().toString(),
                taskNameEdit.getText().toString(),
                taskDescriptionEdit.getText().toString(),
                taskJsonEdit.getText().toString(),
                taskDueEdit.getText().toString());
    }

    private void addHomeTask(String listName, String taskName, String description, String jsonText, String dueText) {
        setBusy(true);
        setStatus("Adding " + taskName + " to Home Center...");
        homeTaskClient.addTask(bucketEdit.getText().toString(), listName, taskName, description, jsonText, dueText, result -> main.post(() -> {
            setBusy(false);
            logResult("addTask", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (!result.ok) {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
            if (result.ok) {
                taskNameEdit.setText("");
                taskDescriptionEdit.setText("");
                taskJsonEdit.setText("");
                taskDueEdit.setText("");
            }
        }));
    }

    private void startTalkFlow() {
        if (recognizer == null) {
            speak("Speech recognition is not available.");
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_RECORD_AUDIO);
            return;
        }
        listen();
    }

    private void listen() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.US.toString());
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Say a Home Center command");
        try {
            setStatus("Listening...");
            recognizer.startListening(intent);
        } catch (ActivityNotFoundException ex) {
            speak("No speech recognizer is installed.");
        }
    }

    private void handlePhrase(String phrase) {
        setStatus("Heard: " + phrase);
        Command command = CommandParser.parse(phrase);
        LocalLog.info("voice.command", "raw=" + phrase + " action=" + command.action + " item=" + command.item + " list=" + command.listName + " visibility=" + command.state + " group=" + command.groupName + " bucket=" + bucketValue() + " signedIn=" + hasSignedInHomeUser());
        if (Command.ADD_LIST_ITEM.equals(command.action)) {
            addListItem(command);
        } else if (Command.READ_LIST.equals(command.action)) {
            readList(command.listName);
        } else if (Command.NEXT_ITEM.equals(command.action)) {
            speakNextItem();
        } else if (Command.PREVIOUS_ITEM.equals(command.action)) {
            speakPreviousItem();
        } else if (Command.MARK_DONE.equals(command.action)) {
            markCurrentDone();
        } else if (Command.REMOVE_LIST_ITEM.equals(command.action)) {
            removeListItem(command);
        } else if (Command.CREATE_LIST.equals(command.action)) {
            createList(command);
        } else if (Command.SET_HOTSPOT.equals(command.action)) {
            speak("Hotspot control is not installed yet.");
        } else {
            speak("I do not know that command yet.");
        }
    }

    private void addListItem(Command command) {
        saveBucketPrefs();
        listEdit.setText(command.listName);
        if (hasReadyHomeSync()) {
            addHomeTask(command.listName, command.item, "", "", "");
        } else if (hasSignedInHomeUser()) {
            speakMissingBucket();
        } else {
            appendStatus("Home Center sync is not signed in; trying TickTick fallback.");
            addToTickTick(command);
        }
    }

    private void readList(String listName) {
        saveBucketPrefs();
        listEdit.setText(listName);
        if (hasReadyHomeSync()) {
            readHomeList(listName);
        } else if (hasSignedInHomeUser()) {
            speakMissingBucket();
        } else {
            appendStatus("Home Center sync is not signed in; trying TickTick fallback.");
            readTickTickList(listName);
        }
    }

    private void removeListItem(Command command) {
        saveBucketPrefs();
        listEdit.setText(command.listName);
        if (!hasSignedInHomeUser()) {
            speak("Sign in with Google first, then try that again.");
            refreshAuthStatus();
            return;
        }
        if (!hasHomeBucket()) {
            speakMissingBucket();
            return;
        }
        setBusy(true);
        setStatus("Removing " + command.item + " from " + command.listName + "...");
        homeTaskClient.removeTaskByName(bucketEdit.getText().toString(), command.listName, command.item, result -> main.post(() -> {
            setBusy(false);
            logResult("removeTask", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (!result.ok) {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
            if (result.ok) {
                removeActiveTaskById(taskIdFromDetail(result.detail));
            }
        }));
    }

    private void addToTickTick(Command command) {
        String token = getSharedPreferences(PREFS, MODE_PRIVATE).getString(KEY_TICKTICK_TOKEN, "");
        setStatus("Adding " + command.item + " to TickTick " + command.listName + "...");
        setBusy(true);
        executor.execute(() -> {
            TickTickClient.Result result = tickTickClient.addItem(token, command.listName, command.item);
            main.post(() -> {
                setBusy(false);
                logTickTickResult("addTickTick", result.ok, result.detail);
                speak(result.spokenMessage);
                appendStatus("Detail: " + result.detail);
            });
        });
    }

    private void readHomeList(String listName) {
        setBusy(true);
        setStatus("Loading Home Center " + listName + "...");
        homeTaskClient.loadActiveTasks(bucketEdit.getText().toString(), listName, result -> main.post(() -> {
            setBusy(false);
            if (!result.ok || result.tasks.isEmpty()) {
                clearActiveReadback();
                logListResult("readHomeList", result.ok, result.detail, result.listName, result.tasks.size());
                speak(result.spokenMessage);
                appendStatus("Detail: " + result.detail);
                if (!result.ok) {
                    appendStatus("Log: " + LocalLog.currentLogPath());
                }
                return;
            }
            activeReadListName = result.listName;
            activeReadItems.clear();
            activeHomeTasks.clear();
            for (HomeTaskClient.HomeTask task : result.tasks) {
                activeReadItems.add(task.name);
                activeHomeTasks.add(task);
            }
            activeReadIndex = 0;
            activeReadIsHomeCenter = true;
            updateReadbackButtons();
            speakCurrentItem();
            logListResult("readHomeList", true, result.detail, result.listName, result.tasks.size());
            appendStatus("Loaded " + result.tasks.size() + " Home Center tasks from " + result.listName + ".");
        }));
    }

    private void readTickTickList(String listName) {
        String token = getSharedPreferences(PREFS, MODE_PRIVATE).getString(KEY_TICKTICK_TOKEN, "");
        setStatus("Loading TickTick " + listName + "...");
        setBusy(true);
        executor.execute(() -> {
            TickTickClient.ListResult result = tickTickClient.fetchListItems(token, listName);
            main.post(() -> {
                setBusy(false);
                if (!result.ok || result.items.isEmpty()) {
                    clearActiveReadback();
                    speak(result.spokenMessage);
                    appendStatus("Detail: " + result.detail);
                    return;
                }
                activeReadListName = result.listName;
                activeReadItems.clear();
                activeReadItems.addAll(result.items);
                activeHomeTasks.clear();
                activeReadIndex = 0;
                activeReadIsHomeCenter = false;
                updateReadbackButtons();
                speakCurrentItem();
                logListResult("readTickTickList", true, result.detail, result.listName, result.items.size());
                appendStatus("Loaded " + result.items.size() + " TickTick items from " + result.listName + ".");
            });
        });
    }

    private String taskIdFromDetail(String detail) {
        if (detail == null) {
            return "";
        }
        String[] parts = detail.split(" ");
        for (String part : parts) {
            if (part.startsWith("removed_task=") || part.startsWith("completed_task=")) {
                int index = part.indexOf('=');
                return index >= 0 ? part.substring(index + 1).trim() : "";
            }
        }
        return "";
    }

    private void removeActiveTaskById(String taskId) {
        if (taskId == null || taskId.isEmpty() || activeHomeTasks.isEmpty()) {
            return;
        }
        for (int i = 0; i < activeHomeTasks.size(); i++) {
            if (taskId.equals(activeHomeTasks.get(i).id)) {
                activeHomeTasks.remove(i);
                activeReadItems.remove(i);
                if (activeReadItems.isEmpty()) {
                    clearActiveReadback();
                } else {
                    if (activeReadIndex >= activeReadItems.size()) {
                        activeReadIndex = activeReadItems.size() - 1;
                    }
                    updateReadbackButtons();
                }
                return;
            }
        }
    }

    private void markCurrentDone() {
        if (activeReadItems.isEmpty() || activeReadIndex < 0 || activeReadIndex >= activeReadItems.size()) {
            speak("No current item is selected. Say read shopping list first.");
            return;
        }
        if (!activeReadIsHomeCenter) {
            speak("Done is only available for Home Center tasks right now.");
            return;
        }
        if (!hasReadyHomeSync()) {
            speak("Home Center sync is not ready.");
            return;
        }
        HomeTaskClient.HomeTask task = activeHomeTasks.get(activeReadIndex);
        homeTaskClient.markDone(bucketEdit.getText().toString(), activeReadListName, task, result -> main.post(() -> {
            logResult("markDone", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (!result.ok) {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
            if (result.ok) {
                activeReadItems.remove(activeReadIndex);
                activeHomeTasks.remove(activeReadIndex);
                if (activeReadItems.isEmpty()) {
                    clearActiveReadback();
                    appendStatus("The list is now empty.");
                } else {
                    if (activeReadIndex >= activeReadItems.size()) {
                        activeReadIndex = activeReadItems.size() - 1;
                    }
                    speakCurrentItem();
                }
            }
        }));
    }

    private void speakCurrentItem() {
        if (activeReadIndex < 0 || activeReadIndex >= activeReadItems.size()) {
            speak("No list is loaded. Say read shopping list first.");
            return;
        }
        int humanIndex = activeReadIndex + 1;
        String item = activeReadItems.get(activeReadIndex);
        speak(activeReadListName + ", item " + humanIndex + " of " + activeReadItems.size() + ": " + item + ".");
        updateReadbackButtons();
    }

    private void speakNextItem() {
        if (activeReadItems.isEmpty()) {
            speak("No list is loaded. Say read shopping list first.");
            return;
        }
        if (activeReadIndex < activeReadItems.size() - 1) {
            activeReadIndex++;
            speakCurrentItem();
        } else {
            speak("End of " + activeReadListName + ". That was item " + activeReadItems.size() + " of " + activeReadItems.size() + ".");
            updateReadbackButtons();
        }
    }

    private void speakPreviousItem() {
        if (activeReadItems.isEmpty()) {
            speak("No list is loaded. Say read shopping list first.");
            return;
        }
        if (activeReadIndex > 0) {
            activeReadIndex--;
            speakCurrentItem();
        } else {
            speak("You are at the first item in " + activeReadListName + ".");
            updateReadbackButtons();
        }
    }

    private void clearActiveReadback() {
        activeReadListName = "";
        activeReadItems.clear();
        activeHomeTasks.clear();
        activeReadIndex = -1;
        activeReadIsHomeCenter = false;
        updateReadbackButtons();
    }

    private void updateReadbackButtons() {
        if (nextButton != null) {
            nextButton.setEnabled(!activeReadItems.isEmpty() && activeReadIndex < activeReadItems.size() - 1);
        }
        if (previousButton != null) {
            previousButton.setEnabled(!activeReadItems.isEmpty() && activeReadIndex > 0);
        }
        if (doneButton != null) {
            doneButton.setEnabled(activeReadIsHomeCenter && !activeReadItems.isEmpty());
        }
    }

    private String bucketValue() {
        return bucketEdit == null ? "" : bucketEdit.getText().toString().trim();
    }

    private void logResult(String area, HomeTaskClient.Result result) {
        String message = "ok=" + result.ok + " spoken=" + result.spokenMessage + " detail=" + result.detail + " bucket=" + bucketValue() + " list=" + (listEdit == null ? "" : listEdit.getText().toString().trim()) + " user=" + currentUserForLog();
        if (result.ok) {
            LocalLog.info(area, message);
        } else {
            LocalLog.warn(area, message);
        }
    }

    private void logListResult(String area, boolean ok, String detail, String listName, int count) {
        String message = "ok=" + ok + " detail=" + detail + " bucket=" + bucketValue() + " list=" + listName + " count=" + count + " user=" + currentUserForLog();
        if (ok) {
            LocalLog.info(area, message);
        } else {
            LocalLog.warn(area, message);
        }
    }

    private void logTickTickResult(String area, boolean ok, String detail) {
        String message = "ok=" + ok + " detail=" + detail;
        if (ok) {
            LocalLog.info(area, message);
        } else {
            LocalLog.warn(area, message);
        }
    }

    private String currentUserForLog() {
        FirebaseUser user = firebaseAuth == null ? null : firebaseAuth.getCurrentUser();
        if (user == null) {
            return "none";
        }
        if (user.getEmail() != null && !user.getEmail().isEmpty()) {
            return user.getEmail();
        }
        return user.getUid();
    }

    private boolean hasHomeClient() {
        return firebaseConfigured && homeTaskClient != null && firebaseAuth != null;
    }

    private boolean hasSignedInHomeUser() {
        return hasHomeClient() && firebaseAuth.getCurrentUser() != null;
    }

    private boolean hasHomeBucket() {
        return bucketEdit != null && !bucketEdit.getText().toString().trim().isEmpty();
    }

    private boolean hasReadyHomeSync() {
        return hasSignedInHomeUser() && hasHomeBucket();
    }

    private void speakMissingBucket() {
        speak("You are signed in, but no household bucket is selected. Enter a household bucket code and tap Join Bucket once.");
    }

    private void saveBucketPrefs() {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(KEY_BUCKET_CODE, bucketEdit == null ? "" : bucketEdit.getText().toString().trim())
                .putString(KEY_DEFAULT_LIST, listEdit == null ? "shopping" : listEdit.getText().toString().trim())
                .apply();
    }

    private void setBusy(boolean busy) {
        if (talkButton != null) {
            talkButton.setEnabled(!busy);
        }
        if (saveTaskButton != null) {
            saveTaskButton.setEnabled(!busy);
        }
        if (createListButton != null) {
            createListButton.setEnabled(!busy);
        }
    }

    private void refreshAuthStatus() {
        if (authStatusView == null) {
            return;
        }
        if (!firebaseConfigured) {
            authStatusView.setText("Home Center sync: Firebase config missing. Add app/google-services.json and rebuild.");
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.VISIBLE);
            }
            return;
        }
        FirebaseUser user = firebaseAuth == null ? null : firebaseAuth.getCurrentUser();
        if (user == null) {
            authStatusView.setText("Home Center sync: not signed in.");
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.VISIBLE);
            }
        } else {
            authStatusView.setText("Home Center sync: signed in as " + homeTaskClient.currentUserLabel() + ".");
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.GONE);
            }
        }
    }

    private void configureTextToSpeech() {
        tts.setLanguage(Locale.US);
        tts.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build());
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override public void onStart(String utteranceId) { }
            @Override public void onDone(String utteranceId) { abandonSpeechFocusFor(utteranceId); }
            @Override public void onError(String utteranceId) { abandonSpeechFocusFor(utteranceId); }
            @Override public void onError(String utteranceId, int errorCode) { abandonSpeechFocusFor(utteranceId); }
            @Override public void onStop(String utteranceId, boolean interrupted) { abandonSpeechFocusFor(utteranceId); }
        });
    }

    private void speak(String message) {
        lastSpoken = message;
        setStatus(message);
        if (tts != null) {
            requestSpeechFocus();
            String utteranceId = "home_center_" + System.currentTimeMillis();
            activeSpeechUtteranceId = utteranceId;
            int result = tts.speak(message, TextToSpeech.QUEUE_FLUSH, null, utteranceId);
            if (result == TextToSpeech.ERROR) {
                abandonSpeechFocusFor(utteranceId);
            }
        }
    }

    private void requestSpeechFocus() {
        if (audioManager == null || speechFocusHeld) {
            return;
        }
        if (speechFocusRequest == null) {
            AudioAttributes attributes = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build();
            speechFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                    .setAudioAttributes(attributes)
                    .setAcceptsDelayedFocusGain(false)
                    .setOnAudioFocusChangeListener(focusChange -> { })
                    .build();
        }
        speechFocusHeld = audioManager.requestAudioFocus(speechFocusRequest) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
    }

    private void abandonSpeechFocusFor(String utteranceId) {
        if (utteranceId != null && !utteranceId.equals(activeSpeechUtteranceId)) {
            return;
        }
        activeSpeechUtteranceId = "";
        abandonSpeechFocus();
    }

    private void abandonSpeechFocus() {
        if (audioManager != null && speechFocusRequest != null && speechFocusHeld) {
            audioManager.abandonAudioFocusRequest(speechFocusRequest);
        }
        speechFocusHeld = false;
    }

    private void setStatus(String message) {
        if (statusView != null) {
            statusView.setText(timeStamp() + "\n" + message);
        }
    }

    private void appendStatus(String message) {
        if (statusView != null) {
            statusView.append("\n" + message);
        }
    }

    private String shortMessage(String message) {
        if (message == null || message.trim().isEmpty()) {
            return "unknown error";
        }
        if (message.length() > 120) {
            return message.substring(0, 117) + "...";
        }
        return message;
    }

    private String timeStamp() {
        return new SimpleDateFormat("h:mm a", Locale.US).format(new Date());
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_GOOGLE_SIGN_IN) {
            try {
                GoogleSignInAccount account = GoogleSignIn.getSignedInAccountFromIntent(data).getResult(ApiException.class);
                signInFirebaseWithGoogle(account, true);
            } catch (Exception ex) {
                refreshAuthStatus();
                speak("Google sign in failed: " + shortMessage(ex.getMessage()));
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_RECORD_AUDIO
                && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            listen();
        } else if (requestCode == REQUEST_RECORD_AUDIO) {
            speak("Microphone permission is required for voice commands.");
        }
    }

    @Override public void onReadyForSpeech(Bundle params) { }
    @Override public void onBeginningOfSpeech() { }
    @Override public void onRmsChanged(float rmsdB) { }
    @Override public void onBufferReceived(byte[] buffer) { }
    @Override public void onEndOfSpeech() { setStatus("Processing speech..."); }
    @Override public void onPartialResults(Bundle partialResults) { }
    @Override public void onEvent(int eventType, Bundle params) { }

    @Override
    public void onError(int error) {
        speak("I did not catch that. Tap Talk and try again.");
    }

    @Override
    public void onResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) {
            speak("I did not hear a command.");
            return;
        }
        handlePhrase(matches.get(0));
    }

    @Override
    protected void onDestroy() {
        if (recognizer != null) {
            recognizer.destroy();
        }
        if (tts != null) {
            tts.shutdown();
        }
        abandonSpeechFocus();
        if (firebaseAuth != null && authStateListener != null) {
            firebaseAuth.removeAuthStateListener(authStateListener);
        }
        executor.shutdownNow();
        super.onDestroy();
    }

    private LinearLayout.LayoutParams matchWrap() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, dp(8), 0, dp(8));
        return params;
    }

    private LinearLayout.LayoutParams matchHeight(int height) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                height);
        params.setMargins(0, dp(8), 0, dp(8));
        return params;
    }

    private LinearLayout.LayoutParams weightedHeight(int height) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, height, 1f);
        params.setMargins(dp(4), dp(4), dp(4), dp(4));
        return params;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
