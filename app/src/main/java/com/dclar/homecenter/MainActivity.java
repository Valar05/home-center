package com.dclar.homecenter;

import android.Manifest;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.graphics.Typeface;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.media.AudioFormat;
import android.media.AudioTrack;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.MediaStore;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.text.method.SingleLineTransformationMethod;
import android.view.KeyEvent;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.inputmethod.EditorInfo;
import android.view.accessibility.AccessibilityManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.google.android.gms.auth.api.signin.GoogleSignIn;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.auth.api.signin.GoogleSignInClient;
import com.google.android.gms.auth.api.signin.GoogleSignInOptions;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.common.api.Scope;
import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.AuthCredential;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.auth.GoogleAuthProvider;
import com.google.firebase.firestore.FirebaseFirestore;

import org.json.JSONObject;

import org.json.JSONArray;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.text.SimpleDateFormat;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public final class MainActivity extends Activity implements RecognitionListener, TextToSpeech.OnInitListener {
    private static final int REQUEST_RECORD_AUDIO = 1001;
    private static final int REQUEST_GOOGLE_SIGN_IN = 2001;
    private static final int REQUEST_GOOGLE_TOOL_PERMISSIONS = 2002;
    private static final int REQUEST_CART_REVIEW_IMPORT = 3001;
    private static final int REQUEST_DRIVE_AUTH = 4001;
    private static final String WALMART_PACKAGE = "com.walmart.android";
    private static final String WALMART_BUY_AGAIN_URL = "https://www.walmart.com/my-items";
    private static final String PREFS = "home_center";
    private static final String KEY_TICKTICK_TOKEN = "ticktick_token";
    private static final String KEY_BUCKET_CODE = "bucket_code";
    private static final String KEY_DEFAULT_LIST = "default_list";
    private static final String KEY_DRAFT_MESSAGE = "draft_message";
    private static final String KEY_GEMINI_API_KEY = "gemini_api_key";
    private static final String KEY_GEMINI_SOURCE = "gemini_source";
    private static final String KEY_CHAT_TRANSCRIPT = "chat_transcript";
    private static final String KEY_CHAT_SUMMARY = "chat_summary";
    private static final String EXTRA_SMOKE_PROMPT = "home_center_smoke_prompt";
    private static final int MAX_RECORDED_TURNS = 18;
    private static final int COLOR_BACKGROUND = Color.parseColor("#121212");
    private static final int COLOR_SURFACE = Color.parseColor("#1E1E1E");
    private static final int COLOR_CARD = Color.parseColor("#2A2A2A");
    private static final int COLOR_PRIMARY = Color.parseColor("#6AA9FF");
    private static final int COLOR_ACCENT = Color.parseColor("#8BC34A");
    private static final int COLOR_TEXT = Color.parseColor("#FFFFFF");
    private static final int COLOR_SECONDARY = Color.parseColor("#B8B8B8");
    private static final int COLOR_DANGER = Color.parseColor("#C75B5B");

    private SpeechRecognizer recognizer;
    private TextToSpeech deviceTextToSpeech;
    private volatile boolean deviceTextToSpeechReady = false;
    private CartesiaSpeechProxyClient cartesiaSpeechProxyClient;
    private AudioManager audioManager;
    private AudioFocusRequest speechFocusRequest;
    private boolean speechFocusHeld = false;
    private boolean externalPlaybackPausedForSpeech = false;
    private String activeSpeechUtteranceId = "";
    private volatile long speechSequence = 0L;
    private volatile boolean speechPlaying = false;
    private volatile AudioTrack activeCartesiaTrack;
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
    private Button submitButton;
    private Button stopSpeechButton;
    private TextView workingIndicatorView;
    private Button geminiSettingsButton;
    private Button promptOneButton;
    private Button promptTwoButton;
    private Button promptThreeButton;
    private Button inventoryButton;
    private Button whatCanIMakeButton;
    private Button brainstormButton;
    private Button rescueButton;
    private Button compactButton;
    private Button cartReviewButton;
    private Button cartRunnerSettingsButton;
    private Button cartRunnerCheckButton;
    private EditText messageEdit;
    private ScrollView chatScroll;
    private LinearLayout chatLogContainer;
    private GeminiClient geminiClient;
    private OpenAiAgentClient openAiAgentClient;
    private GoogleDriveClient googleDriveClient;
    private GoogleSheetsClient googleSheetsClient;
    private GoogleGmailClient googleGmailClient;
    private GoogleCalendarClient googleCalendarClient;
    private GoogleContactsClient googleContactsClient;

    private boolean tickTickTokenVisible = false;
    private boolean firebaseConfigured = false;
    private boolean silentSignInAttempted = false;
    private FirebaseAuth firebaseAuth;
    private FirebaseFirestore firestore;
    private GoogleSignInClient googleSignInClient;
    private GoogleSignInClient googleIdentitySignInClient;
    private FirebaseAuth.AuthStateListener authStateListener;
    private HomeTaskClient homeTaskClient;
    private String lastSpoken = "Home Center is ready.";
    private String activeReadListName = "";
    private final List<String> activeReadItems = new ArrayList<>();
    private final List<HomeTaskClient.HomeTask> activeHomeTasks = new ArrayList<>();
    private int activeReadIndex = -1;
    private boolean activeReadIsHomeCenter = false;
    private boolean busy = false;
    private final List<ChatTurn> chatTurns = new ArrayList<>();
    private String conversationSummary = "";
    private String pendingAgentTurnAfterGoogleReconnect = "";
    private volatile JSONObject pendingToolConfirmation;
    private final Object workingMemoryLock = new Object();
    private final JSONObject workingMemory = new JSONObject();
    private final Object toolTraceLock = new Object();
    private final JSONArray recentToolTrace = new JSONArray();
    private String lastVisibleStatus = "";
    private String lastDriveDocumentId = "";
    private String lastDriveDocumentName = "";
    private String startupGreeting = "Home Center is ready. Try pantry inventory, what can I make, recipe brainstorm, or rescue meal.";
    private final List<CartReviewItem> cartReviewItems = new ArrayList<>();
    private int cartReviewIndex = -1;

    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final TickTickClient tickTickClient = new TickTickClient();
    private boolean visualEvidenceEnabled = false;
    private boolean thinkingHapticsActive = false;
    private final Runnable thinkingHapticPulse = new Runnable() {
        @Override
        public void run() {
            if (!thinkingHapticsActive || !busy) {
                thinkingHapticsActive = false;
                return;
            }
            View target = submitButton != null ? submitButton : chatLogContainer;
            if (target != null) {
                target.performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK);
            }
            main.postDelayed(this, 900L);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LocalLog.init(this);
        getWindow().setStatusBarColor(COLOR_BACKGROUND);
        getWindow().setNavigationBarColor(Color.BLACK);
        LocalLog.info("app", "start versionName=" + BuildConfig.VERSION_NAME + " versionCode=" + BuildConfig.VERSION_CODE);
        initFirebase();
        audioManager = (AudioManager) getSystemService(AUDIO_SERVICE);
        cartesiaSpeechProxyClient = new CartesiaSpeechProxyClient(BuildConfig.CARTESIA_PROXY_BASE_URL, BuildConfig.CARTESIA_API_KEY);
        deviceTextToSpeech = new TextToSpeech(this, this);
        googleDriveClient = new GoogleDriveClient(this);
        googleSheetsClient = new GoogleSheetsClient(this);
        googleGmailClient = new GoogleGmailClient(this);
        googleCalendarClient = new GoogleCalendarClient(this);
        googleContactsClient = new GoogleContactsClient(this);
        refreshGeminiClient();
        buildUi();
        boolean restoredConversation = restoreConversationHistory();
        startupGreeting = ChatSystemShape.startupGreeting(restoredConversation);
        boolean coldStart = savedInstanceState == null;
        if (coldStart) {
            appendStatus(startupGreeting);
        }
        if (coldStart) {
            lastSpoken = startupGreeting;
        }
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            recognizer.setRecognitionListener(this);
        } else {
            setStatus("Speech recognition is not available on this device.");
        }
        runInstalledSmokePromptIfRequested(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        runInstalledSmokePromptIfRequested(intent);
    }

    private void runInstalledSmokePromptIfRequested(Intent intent) {
        if (intent == null || !BuildConfig.DEBUG) {
            return;
        }
        String prompt = intent.getStringExtra(EXTRA_SMOKE_PROMPT);
        if (prompt == null || prompt.trim().isEmpty()) {
            return;
        }
        visualEvidenceEnabled = true;
        LocalLog.info("installed_smoke", "prompt_requested: " + shortMessage(prompt));
        main.postDelayed(() -> {
            if (messageEdit == null) {
                LocalLog.warn("installed_smoke", "message composer unavailable");
                return;
            }
            messageEdit.setText(prompt.trim());
            submitTypedMessage();
        }, 1200L);
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
                GoogleSignInOptions identityOptions = new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                        .requestIdToken(clientId)
                        .requestServerAuthCode(clientId, false)
                        .requestEmail()
                        .build();
                GoogleSignInOptions.Builder fullSignInBuilder = new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                        .requestIdToken(clientId)
                        .requestServerAuthCode(clientId, false)
                        .requestEmail();
                for (Scope scope : ToolRegistry.signInScopes()) {
                    fullSignInBuilder.requestScopes(scope);
                }
                googleIdentitySignInClient = GoogleSignIn.getClient(this, identityOptions);
                googleSignInClient = GoogleSignIn.getClient(this, fullSignInBuilder.build());
            }
        } catch (Exception ex) {
            firebaseConfigured = false;
        }
    }


    private void exchangeGoogleServerAuthCode(GoogleSignInAccount account) {
        if (openAiAgentClient == null || !openAiAgentClient.isConfigured() || account == null) {
            return;
        }
        String authCode = account.getServerAuthCode();
        FirebaseUser user = firebaseAuth == null ? null : firebaseAuth.getCurrentUser();
        if (user == null || authCode == null || authCode.trim().isEmpty()) {
            return;
        }
        user.getIdToken(false)
                .addOnSuccessListener(token -> executor.execute(() -> {
                    try {
                        openAiAgentClient.exchangeGoogleAuthCode(token.getToken(), authCode);
                        main.post(() -> appendStatus("Google tools connected."));
                    } catch (Exception ex) {
                        main.post(() -> appendStatus("Google tools need reconnection: " + shortMessage(ex.getMessage())));
                    }
                }))
                .addOnFailureListener(ex -> appendStatus("Could not verify Google tools connection: " + shortMessage(ex.getMessage())));
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
        if (!firebaseConfigured || googleIdentitySignInClient == null || firebaseAuth == null) {
            return;
        }
        if (firebaseAuth.getCurrentUser() != null || silentSignInAttempted) {
            refreshAuthStatus();
            return;
        }
        silentSignInAttempted = true;
        appendStatus("Restoring Google sign-in...");
        googleIdentitySignInClient.silentSignIn()
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
                    exchangeGoogleServerAuthCode(account);
                    String pending = pendingAgentTurnAfterGoogleReconnect;
                    if (!hasAllGoogleToolScopes(account)) {
                        if (announce || (pending != null && !pending.trim().isEmpty())) {
                            appendStatus("Google identity connected. Requesting tool permissions.");
                            requestGoogleToolPermissions(account);
                        } else {
                            appendStatus("Google sign-in restored. Tool permissions still need approval.");
                        }
                        return;
                    }
                    if (pending != null && !pending.trim().isEmpty()) {
                        pendingAgentTurnAfterGoogleReconnect = "";
                        appendStatus("Google connected. Continuing the pending request.");
                        sendAgentTurn(pending);
                        return;
                    }
                    pendingAgentTurnAfterGoogleReconnect = "";
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
        initializePortableCommandFields(prefs);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(12), dp(8), dp(12), dp(10));
        root.setBackgroundColor(COLOR_BACKGROUND);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        authStatusView = new TextView(this);
        authStatusView.setTextSize(14);
        authStatusView.setTypeface(Typeface.DEFAULT_BOLD);
        authStatusView.setTextColor(COLOR_ACCENT);
        authStatusView.setGravity(Gravity.CENTER_VERTICAL);
        authStatusView.setPadding(dp(10), dp(6), dp(10), dp(6));
        header.addView(authStatusView, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        googleSignInButton = new Button(this);
        googleSignInButton.setText("Sign in with Google");
        googleSignInButton.setAllCaps(false);
        googleSignInButton.setTextSize(13);
        googleSignInButton.setTextColor(COLOR_TEXT);
        googleSignInButton.setBackgroundColor(COLOR_PRIMARY);
        googleSignInButton.setContentDescription("Sign in with Google");
        header.addView(googleSignInButton, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        Button menuButton = new Button(this);
        menuButton.setText("Menu");
        menuButton.setAllCaps(false);
        menuButton.setTextSize(13);
        menuButton.setTextColor(COLOR_TEXT);
        menuButton.setBackgroundColor(COLOR_CARD);
        menuButton.setContentDescription("Open Home Center menu");
        LinearLayout.LayoutParams menuParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        menuParams.setMargins(dp(8), 0, 0, 0);
        header.addView(menuButton, menuParams);
        root.addView(header, matchWrap());

        statusView = new TextView(this);
        statusView.setTextSize(13);
        statusView.setTextColor(COLOR_SECONDARY);
        statusView.setGravity(Gravity.CENTER_HORIZONTAL);
        statusView.setPadding(0, dp(2), 0, dp(6));
        root.addView(statusView, matchWrap());
        updateBackendStatus();

        chatScroll = new ScrollView(this);
        chatScroll.setFillViewport(true);
        chatScroll.setBackgroundColor(COLOR_BACKGROUND);
        LinearLayout.LayoutParams chatScrollParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f);
        chatScrollParams.setMargins(0, dp(6), 0, dp(8));
        chatScroll.setLayoutParams(chatScrollParams);

        chatLogContainer = new LinearLayout(this);
        chatLogContainer.setOrientation(LinearLayout.VERTICAL);
        chatLogContainer.setPadding(dp(2), dp(2), dp(2), dp(10));
        chatScroll.addView(chatLogContainer, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(chatScroll);

        LinearLayout bottomPanel = new LinearLayout(this);
        bottomPanel.setOrientation(LinearLayout.VERTICAL);
        bottomPanel.setPadding(dp(10), dp(10), dp(10), dp(10));
        bottomPanel.setBackground(makePanelBackground());

        workingIndicatorView = new TextView(this);
        workingIndicatorView.setText("Working...");
        workingIndicatorView.setTextSize(14);
        workingIndicatorView.setTypeface(Typeface.DEFAULT_BOLD);
        workingIndicatorView.setTextColor(COLOR_BACKGROUND);
        workingIndicatorView.setGravity(Gravity.CENTER_VERTICAL);
        workingIndicatorView.setPadding(dp(12), dp(8), dp(12), dp(8));
        workingIndicatorView.setBackgroundColor(COLOR_PRIMARY);
        workingIndicatorView.setVisibility(View.GONE);
        workingIndicatorView.setContentDescription("Home Center is working");
        LinearLayout.LayoutParams workingParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        workingParams.setMargins(0, 0, 0, dp(8));
        bottomPanel.addView(workingIndicatorView, workingParams);

        LinearLayout composeRow = new LinearLayout(this);
        composeRow.setOrientation(LinearLayout.HORIZONTAL);
        composeRow.setGravity(Gravity.CENTER_VERTICAL);

        messageEdit = new EditText(this);
        messageEdit.setHint("Ask Home Center...");
        messageEdit.setHintTextColor(COLOR_SECONDARY);
        messageEdit.setTextColor(COLOR_TEXT);
        messageEdit.setSingleLine(true);
        messageEdit.setText(prefs.getString(KEY_DRAFT_MESSAGE, ""));
        messageEdit.setImeOptions(EditorInfo.IME_ACTION_SEND);
        messageEdit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        messageEdit.setContentDescription("Message Home Center");
        messageEdit.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        composeRow.addView(messageEdit);

        submitButton = new Button(this);
        submitButton.setText("Send");
        submitButton.setAllCaps(false);
        submitButton.setTextColor(COLOR_BACKGROUND);
        submitButton.setBackgroundColor(COLOR_ACCENT);
        LinearLayout.LayoutParams sendParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        sendParams.setMargins(dp(10), 0, 0, 0);
        submitButton.setLayoutParams(sendParams);
        composeRow.addView(submitButton);

        stopSpeechButton = new Button(this);
        stopSpeechButton.setText("Stop");
        stopSpeechButton.setAllCaps(false);
        stopSpeechButton.setTextColor(COLOR_TEXT);
        stopSpeechButton.setBackgroundColor(COLOR_DANGER);
        stopSpeechButton.setVisibility(View.GONE);
        LinearLayout.LayoutParams stopParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        stopParams.setMargins(dp(8), 0, 0, 0);
        stopSpeechButton.setLayoutParams(stopParams);
        composeRow.addView(stopSpeechButton);

        bottomPanel.addView(composeRow, matchWrap());
        root.addView(bottomPanel, matchWrap());

        submitButton.setOnClickListener(v -> submitTypedMessage());
        stopSpeechButton.setOnClickListener(v -> stopSpeechPlayback());
        googleSignInButton.setOnClickListener(v -> startGoogleSignIn());
        menuButton.setOnClickListener(v -> showHomeCenterMenu());
        messageEdit.setOnEditorActionListener((v, actionId, event) -> {
            boolean send = actionId == EditorInfo.IME_ACTION_SEND
                    || (event != null && event.getAction() == KeyEvent.ACTION_DOWN && event.getKeyCode() == KeyEvent.KEYCODE_ENTER);
            if (send) {
                submitTypedMessage();
                return true;
            }
            return false;
        });

        setContentView(root);
        refreshAuthStatus();
        setSpeechPlaying(false);
    }

    private void initializePortableCommandFields(SharedPreferences prefs) {
        bucketEdit = singleLineEdit("Household bucket", prefs.getString(KEY_BUCKET_CODE, ""));
        listEdit = singleLineEdit("Default list", prefs.getString(KEY_DEFAULT_LIST, "shopping"));
        listVisibilityEdit = singleLineEdit("Visibility", "household");
        groupNameEdit = singleLineEdit("Family group", "");
        taskNameEdit = singleLineEdit("Task name", "");
        taskDescriptionEdit = singleLineEdit("Task description", "");
        taskJsonEdit = singleLineEdit("Task details", "");
        taskDueEdit = singleLineEdit("Due date", "");
    }


    private void showHomeCenterMenu() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(20), dp(12), dp(20), dp(4));

        TextView help = new TextView(this);
        help.setText("Secondary controls and diagnostics. Chat stays primary.");
        help.setTextSize(14);
        help.setTextColor(COLOR_SECONDARY);
        help.setPadding(0, 0, 0, dp(10));
        panel.addView(help, matchWrap());

        Button household = button("Household and list", 16, "Set household bucket and default list");
        Button ticktick = button("TickTick token", 16, "Set TickTick fallback token");
        Button cartReview = button("Walmart cart review", 16, "Import a Walmart cart review bundle");
        Button cartHelper = button("Cart helper settings", 16, "Open Android accessibility settings for the cart helper");
        Button diagnostics = button("Check cart helper", 16, "Check whether the cart helper is installed and enabled");
        Button driveCheck = button("Check Google Drive", 16, "Check whether Home Center can list Google Drive files");
        Button netrunner = button("Netrunner browser", 16, "Open the secondary browser tool");
        Button compact = button("Compact chat", 16, "Compact the current chat history");

        panel.addView(household, matchHeight(dp(52)));
        panel.addView(ticktick, matchHeight(dp(52)));
        panel.addView(cartReview, matchHeight(dp(52)));
        panel.addView(cartHelper, matchHeight(dp(52)));
        panel.addView(diagnostics, matchHeight(dp(52)));
        panel.addView(driveCheck, matchHeight(dp(52)));
        panel.addView(netrunner, matchHeight(dp(52)));
        panel.addView(compact, matchHeight(dp(52)));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Home Center menu")
                .setView(panel)
                .setNegativeButton("Close", null)
                .create();
        household.setOnClickListener(v -> {
            dialog.dismiss();
            showHouseholdSettings();
        });
        ticktick.setOnClickListener(v -> {
            dialog.dismiss();
            showTickTickSettings();
        });
        cartReview.setOnClickListener(v -> {
            dialog.dismiss();
            startCartReviewImport();
        });
        cartHelper.setOnClickListener(v -> {
            dialog.dismiss();
            openAccessibilitySettings();
        });
        diagnostics.setOnClickListener(v -> {
            dialog.dismiss();
            showCartHelperDiagnostics();
        });
        driveCheck.setOnClickListener(v -> {
            dialog.dismiss();
            checkGoogleDriveDiagnostic();
        });
        netrunner.setOnClickListener(v -> {
            dialog.dismiss();
            startActivity(new Intent(this, NetrunnerActivity.class));
        });
        compact.setOnClickListener(v -> {
            dialog.dismiss();
            compactConversation();
        });
        dialog.show();
    }

    private void showHouseholdSettings() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(20), dp(12), dp(20), dp(4));

        TextView help = new TextView(this);
        help.setText("Pick the shared Home Center bucket and default list used by voice commands.");
        help.setTextSize(14);
        help.setTextColor(Color.parseColor("#3F3A31"));
        help.setPadding(0, 0, 0, dp(10));
        panel.addView(help, matchWrap());

        EditText bucket = singleLineEdit("Household bucket", bucketEdit == null ? prefs.getString(KEY_BUCKET_CODE, "") : bucketEdit.getText().toString());
        EditText list = singleLineEdit("Default list", listEdit == null ? prefs.getString(KEY_DEFAULT_LIST, "shopping") : listEdit.getText().toString());
        panel.addView(bucket, matchHeight(dp(64)));
        panel.addView(list, matchHeight(dp(64)));

        new AlertDialog.Builder(this)
                .setTitle("Household")
                .setView(panel)
                .setNegativeButton("Cancel", null)
                .setNeutralButton("Join bucket", null)
                .setPositiveButton("Save", (dialog, which) -> {
                    bucketEdit.setText(bucket.getText().toString().trim());
                    listEdit.setText(list.getText().toString().trim().isEmpty() ? "shopping" : list.getText().toString().trim());
                    saveBucketPrefs();
                    refreshAuthStatus();
                    showAssistantMessage("Household settings saved.");
                })
                .show()
                .getButton(AlertDialog.BUTTON_NEUTRAL)
                .setOnClickListener(v -> {
                    bucketEdit.setText(bucket.getText().toString().trim());
                    listEdit.setText(list.getText().toString().trim().isEmpty() ? "shopping" : list.getText().toString().trim());
                    joinBucket();
                });
    }

    private void showTickTickSettings() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(20), dp(12), dp(20), dp(4));

        TextView help = new TextView(this);
        help.setText("TickTick is a legacy fallback when Home Center sync is unavailable.");
        help.setTextSize(14);
        help.setTextColor(Color.parseColor("#3F3A31"));
        help.setPadding(0, 0, 0, dp(10));
        panel.addView(help, matchWrap());

        EditText token = singleLineEdit("TickTick API token", prefs.getString(KEY_TICKTICK_TOKEN, ""));
        token.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        panel.addView(token, matchHeight(dp(64)));

        new AlertDialog.Builder(this)
                .setTitle("TickTick fallback")
                .setView(panel)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Save", (dialog, which) -> {
                    prefs.edit().putString(KEY_TICKTICK_TOKEN, token.getText().toString().trim()).apply();
                    showAssistantMessage("TickTick fallback token saved.");
                })
                .show();
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

    private Button promptButton(String label, String prompt) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextSize(12);
        button.setPadding(dp(8), dp(8), dp(8), dp(8));
        button.setBackgroundColor(COLOR_CARD);
        button.setTextColor(COLOR_TEXT);
        button.setMinWidth(0);
        button.setMinHeight(0);
        button.setTag(prompt);
        return button;
    }

    private void fillPrompt(String prompt) {
        if (messageEdit == null) {
            return;
        }
        messageEdit.setText(prompt);
        messageEdit.setSelection(messageEdit.length());
    }

    private void showGeminiSettings() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(20), dp(12), dp(20), dp(4));

        TextView help = new TextView(this);
        help.setText("Paste a Gemini API key. Runtime model: " + effectiveGeminiModel() + ".");
        help.setTextSize(14);
        help.setTextColor(Color.parseColor("#3F3A31"));
        help.setPadding(0, 0, 0, dp(10));
        panel.addView(help);

        EditText keyEdit = new EditText(this);
        keyEdit.setHint("Gemini API key");
        keyEdit.setSingleLine(true);
        keyEdit.setText(effectiveGeminiApiKey());
        keyEdit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        panel.addView(keyEdit, matchHeight(dp(64)));

        new AlertDialog.Builder(this)
                .setTitle("Gemini key")
                .setView(panel)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Save", (dialog, which) -> {
                    prefs.edit()
                            .putString(KEY_GEMINI_API_KEY, keyEdit.getText().toString().trim())
                            .putString(KEY_GEMINI_SOURCE, "saved")
                            .apply();
                    refreshGeminiClient();
                    appendAssistantMessage("Gemini key saved.");
                    speak("Gemini key saved.");
                })
                .show();
    }

    private GeminiConfig effectiveGeminiConfig() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String envKey = clean(System.getenv("GEMINI_API_KEY"));
        if (!envKey.isEmpty()) {
            return new GeminiConfig(envKey, fixedGeminiModel(), "env");
        }
        String savedKey = clean(prefs.getString(KEY_GEMINI_API_KEY, ""));
        if (!savedKey.isEmpty()) {
            return new GeminiConfig(savedKey, fixedGeminiModel(), "saved");
        }
        String buildKey = clean(BuildConfig.GEMINI_API_KEY);
        if (!buildKey.isEmpty()) {
            return new GeminiConfig(buildKey, fixedGeminiModel(), "build");
        }
        return new GeminiConfig("", fixedGeminiModel(), "missing");
    }

    private String fixedGeminiModel() {
        return clean(BuildConfig.GEMINI_MODEL).isEmpty() ? "gemini-2.0-flash" : clean(BuildConfig.GEMINI_MODEL);
    }

    private String effectiveGeminiApiKey() {
        return effectiveGeminiConfig().apiKey;
    }

    private String effectiveGeminiModel() {
        return fixedGeminiModel();
    }

    private void refreshGeminiClient() {
        GeminiConfig config = effectiveGeminiConfig();
        geminiClient = new GeminiClient(config.apiKey, config.model);
        openAiAgentClient = new OpenAiAgentClient(BuildConfig.AGENT_GATEWAY_BASE_URL, BuildConfig.OPENAI_API_KEY);
        updateBackendStatus();
    }

    private void submitTypedMessage() {
        if (messageEdit == null) {
            return;
        }
        String text = messageEdit.getText().toString().trim();
        if (text.isEmpty()) {
            showAssistantMessage("Type a message first.");
            return;
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_DRAFT_MESSAGE, "").apply();
        messageEdit.setText("");
        submitMessage(text, false);
    }

    private void submitMessage(String text, boolean fromVoice) {
        String clean = text == null ? "" : text.trim();
        if (clean.isEmpty()) {
            return;
        }
        if (messageEdit != null) {
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_DRAFT_MESSAGE, messageEdit.getText().toString()).apply();
        }
        appendUserMessage(clean, fromVoice);
        chatTurns.add(new ChatTurn("user", clean));
        trimChatTurns();
        recordTranscriptTurn("user", clean);
        sendAgentTurn(clean);
    }


    private boolean ensureGoogleToolScopesForTurn(String clean) {
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (hasAllGoogleToolScopes(account)) {
            return true;
        }
        pendingAgentTurnAfterGoogleReconnect = clean == null ? "" : clean.trim();
        showAssistantMessage("Google needs one more approval for Drive, Docs, Sheets, Gmail, Calendar, and Contacts tools. I am opening Google permission approval now, then I will continue this request.");
        requestGoogleToolPermissions(account);
        return false;
    }

    private boolean hasAllGoogleToolScopes(GoogleSignInAccount account) {
        if (account == null || account.getAccount() == null) {
            return false;
        }
        for (Scope scope : ToolRegistry.signInScopes()) {
            if (!account.getGrantedScopes().contains(scope)) {
                return false;
            }
        }
        return true;
    }

    private void requestGoogleToolPermissions(GoogleSignInAccount account) {
        if (account == null) {
            startGoogleSignIn();
            return;
        }
        List<Scope> scopes = ToolRegistry.signInScopes();
        if (scopes.isEmpty()) {
            return;
        }
        GoogleSignIn.requestPermissions(this, REQUEST_GOOGLE_TOOL_PERMISSIONS, account, scopes.toArray(new Scope[0]));
    }

    private void sendAgentTurn(String clean) {
        if (openAiAgentClient == null || !openAiAgentClient.isConfigured()) {
            showAssistantMessage("GPT-5.5 is not configured in this build.");
            return;
        }
        if (!hasSignedInHomeUser()) {
            pendingAgentTurnAfterGoogleReconnect = clean == null ? "" : clean.trim();
            showAssistantMessage("Sign in with Google first. That one sign-in unlocks GPT-5.5, web search, Google tools, Home Center lists, TickTick fallback, and Cartesia narration.");
            refreshAuthStatus();
            startGoogleSignIn();
            return;
        }
        if (!ensureGoogleToolScopesForTurn(clean)) {
            return;
        }
        FirebaseUser user = firebaseAuth.getCurrentUser();
        setBusy(true);
        setStatus("Asking GPT-5.5...");
        user.getIdToken(false)
                .addOnSuccessListener(token -> executor.execute(() -> runAgentToolLoop(token.getToken(), clean)))
                .addOnFailureListener(ex -> {
                    setBusy(false);
                    showAssistantMessage("Could not verify Google sign-in: " + shortMessage(ex.getMessage()));
                });
    }

    private void runAgentToolLoop(String idToken, String clean) {
        JSONArray toolResults = new JSONArray();
        try {
            OpenAiAgentClient.ToolTurn turn = null;
            for (int step = 0; step < 6; step++) {
                GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
                JSONArray availableTools = ToolRegistry.availableTools(account, hasSignedInHomeUser());
                JSONArray unavailableGroups = ToolRegistry.unavailableToolGroups(account, hasSignedInHomeUser());
                LocalLog.info("agent_trace", "step=" + step + " availableTools=" + shortMessage(availableTools.toString()));
                turn = openAiAgentClient.sendToolTurn(
                        idToken,
                        clean,
                        recentTranscriptSnapshot(),
                        conversationSummary,
                        toolResults,
                        availableTools,
                        unavailableGroups,
                        cloneJson(pendingToolConfirmation),
                        workingMemorySnapshot(),
                        currentTimeContext(),
                        evidenceContextSnapshot(clean));
                LocalLog.info("agent_trace", "step=" + step + " gateway_type=" + turn.type + " status=" + turn.status + " requestedTool=" + turn.toolName + " technicalDetails=" + shortMessage(turn.technicalDetails));
                if (turn.requestsTool()) {
                    LocalLog.info("agent_trace", "android_received_tool=" + turn.toolName);
                    JSONObject pendingForRetry = turn.arguments.optBoolean("_confirmedByGateway", false)
                            ? cloneJson(pendingToolConfirmation)
                            : null;
                    JSONObject result = executeRegisteredTool(turn.toolName, turn.arguments, idToken);
                    updateWorkingMemoryFromToolResult(turn.toolName, turn.arguments, result);
                    JSONObject resultFile = result.optJSONObject("file");
                    String resultDocumentId = resultFile == null ? "" : resultFile.optString("id", "");
                    LocalLog.info("agent_trace", "android_dispatch_result tool=" + turn.toolName + " ok=" + result.optBoolean("ok", false) + " status=" + result.optString("status", "") + " error=" + result.optString("error", "") + " documentId=" + resultDocumentId + " webViewLink=" + result.optString("webViewLink", "") + " workingMemory=" + shortMessage(workingMemorySnapshot().toString()));
                    rememberToolTrace(turn.toolName, turn.arguments, result);
                    if (isGoogleToolAuthFailure(result)) {
                        requestGoogleToolReconnect(clean, pendingForRetry, result);
                        return;
                    }
                    if (turn.arguments.optBoolean("_confirmedByGateway", false)) {
                        pendingToolConfirmation = null;
                    }
                    toolResults.put(new JSONObject()
                            .put("name", turn.toolName)
                            .put("arguments", turn.arguments)
                            .put("result", result));
                    continue;
                }
                JSONObject pendingForUi = null;
                if ("confirmation_required".equals(turn.status) && turn.pendingConfirmation != null) {
                    pendingToolConfirmation = cloneJson(turn.pendingConfirmation);
                    pendingForUi = cloneJson(turn.pendingConfirmation);
                } else if (!"confirmation_required".equals(turn.status)) {
                    pendingToolConfirmation = null;
                }
                finishAgentReply(clean, turn.reply, turn.narration, turn.status, pendingForUi);
                return;
            }
            pendingToolConfirmation = null;
            finishAgentReply(clean, "I could not finish that request because the tool plan did not converge.", "I could not finish that request because the tool plan did not converge.", "tool_loop_limit", null);
        } catch (Exception ex) {
            main.post(() -> {
                LocalLog.info("agent", "tool_loop_failed: " + shortMessage(ex.getMessage()));
                setBusy(false);
                showAssistantMessage("The agent gateway failed: " + shortMessage(ex.getMessage()));
            });
        }
    }

    private boolean isGoogleToolAuthFailure(JSONObject result) {
        if (result == null) {
            return false;
        }
        String tool = result.optString("tool", "");
        if (!(tool.startsWith("drive.") || tool.startsWith("docs.") || tool.startsWith("sheets.") || tool.startsWith("gmail.") || tool.startsWith("calendar.") || tool.startsWith("contacts."))) {
            return false;
        }
        String error = result.optString("error", "").toLowerCase(Locale.US);
        return "scope_missing".equals(error)
                || "scope_recoverable".equals(error)
                || "token_auth_error".equals(error)
                || "token_error".equals(error)
                || "token_empty".equals(error);
    }

    private void requestGoogleToolReconnect(String clean, JSONObject pendingForRetry, JSONObject result) {
        main.post(() -> {
            setBusy(false);
            pendingAgentTurnAfterGoogleReconnect = clean == null ? "" : clean.trim();
            pendingToolConfirmation = cloneJson(pendingForRetry);
            String detail = result == null ? "Google needs another approval." : shortMessage(result.optString("detail", result.optString("error", "Google needs another approval.")));
            showAssistantMessage("Google needs one more approval before I can run that action. I am reopening Google sign-in now, then I will retry it. Detail: " + detail);
            forceGoogleToolReconnect();
        });
    }

    private void forceGoogleToolReconnect() {
        if (!firebaseConfigured || googleSignInClient == null) {
            startGoogleSignIn();
            return;
        }
        googleSignInClient.signOut()
                .addOnCompleteListener(task -> {
                    if (googleIdentitySignInClient != null) {
                        googleIdentitySignInClient.signOut().addOnCompleteListener(identityTask -> startGoogleSignIn());
                    } else {
                        startGoogleSignIn();
                    }
                })
                .addOnFailureListener(ex -> startGoogleSignIn());
    }

    private JSONObject executeRegisteredTool(String toolName, JSONObject arguments, String idToken) {
        LocalLog.info("agent", "tool_call " + toolName);
        ToolRegistry.ToolDefinition definition = ToolRegistry.definition(toolName);
        if (definition == null) {
            return toolError(toolName, "unknown_tool", "No Android tool is registered with that name.");
        }
        if (definition.confirmationRequired && (arguments == null || !arguments.optBoolean("_confirmedByGateway", false))) {
            return toolError(toolName, "confirmation_required", "This write tool requires explicit gateway confirmation.");
        }
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if ("drive".equals(definition.group) || "docs".equals(definition.group)) {
            if (googleDriveClient == null) {
                return toolError(toolName, "drive_unavailable", "Google Drive and Docs tools are not available in this build.");
            }
            return googleDriveClient.runTool(toolName, arguments, account);
        }
        if ("sheets".equals(definition.group)) {
            if (googleSheetsClient == null) {
                return toolError(toolName, "sheets_unavailable", "Google Sheets tool is not available in this build.");
            }
            return googleSheetsClient.runTool(toolName, arguments, account);
        }
        if ("gmail".equals(definition.group)) {
            if (googleGmailClient == null) {
                return toolError(toolName, "gmail_unavailable", "Gmail tool is not available in this build.");
            }
            return googleGmailClient.runTool(toolName, arguments, account);
        }
        if ("calendar".equals(definition.group)) {
            if (googleCalendarClient == null) {
                return toolError(toolName, "calendar_unavailable", "Calendar tool is not available in this build.");
            }
            return googleCalendarClient.runTool(toolName, arguments, account);
        }
        if ("contacts".equals(definition.group)) {
            if (googleContactsClient == null) {
                return toolError(toolName, "contacts_unavailable", "Contacts tool is not available in this build.");
            }
            return googleContactsClient.runTool(toolName, arguments, account);
        }
        if ("lists".equals(definition.group)) {
            return executeListTool(toolName, arguments);
        }
        if ("github.create_issue".equals(toolName)) {
            if (openAiAgentClient == null || !openAiAgentClient.isConfigured()) {
                return toolError(toolName, "github_unavailable", "GitHub issue creation requires the Home Center gateway.");
            }
            try {
                JSONObject response = openAiAgentClient.createGitHubIssue(idToken, arguments);
                response.put("tool", toolName);
                return response;
            } catch (Exception ex) {
                return toolError(toolName, "github_error", shortMessage(ex.getMessage()));
            }
        }
        return toolError(toolName, "unknown_tool_group", "No Android dispatcher exists for that tool group.");
    }

    private JSONObject executeListTool(String toolName, JSONObject arguments) {
        if (!hasHomeClient() || !hasSignedInHomeUser()) {
            return toolError(toolName, "not_signed_in", "Sign in with Google first.");
        }
        String listName = toolArg(arguments, "listName", listEdit == null ? "shopping" : listEdit.getText().toString());
        String bucket = bucketEdit == null ? "" : bucketEdit.getText().toString();
        CountDownLatch latch = new CountDownLatch(1);
        JSONObject[] holder = new JSONObject[]{toolError(toolName, "timeout", "List tool timed out.")};
        if ("lists.read".equals(toolName)) {
            homeTaskClient.loadActiveTasks(bucket, listName, result -> {
                holder[0] = listResultJson(toolName, result);
                latch.countDown();
            });
        } else if ("lists.create".equals(toolName)) {
            homeTaskClient.createList(bucket, listName, "household", "", result -> {
                holder[0] = resultJson(toolName, result);
                latch.countDown();
            });
        } else if ("lists.add_item".equals(toolName)) {
            String text = toolArg(arguments, "text", "");
            homeTaskClient.addTask(bucket, listName, text, "", "", "", result -> {
                holder[0] = resultJson(toolName, result);
                latch.countDown();
            });
        } else if ("lists.update_item".equals(toolName)) {
            homeTaskClient.updateTaskByIdOrName(bucket, listName, toolArg(arguments, "itemId", ""), toolArg(arguments, "itemText", ""), toolArg(arguments, "text", ""), toolArg(arguments, "status", ""), result -> {
                holder[0] = resultJson(toolName, result);
                latch.countDown();
            });
        } else if ("lists.mark_done".equals(toolName)) {
            homeTaskClient.updateTaskByIdOrName(bucket, listName, toolArg(arguments, "itemId", ""), toolArg(arguments, "itemText", ""), "", "done", result -> {
                holder[0] = resultJson(toolName, result);
                latch.countDown();
            });
        } else if ("lists.remove_item".equals(toolName)) {
            homeTaskClient.updateTaskByIdOrName(bucket, listName, toolArg(arguments, "itemId", ""), toolArg(arguments, "itemText", ""), "", "removed", result -> {
                holder[0] = resultJson(toolName, result);
                latch.countDown();
            });
        } else {
            return toolError(toolName, "unknown_tool", "No list dispatcher exists for that tool.");
        }
        try {
            if (!latch.await(35, TimeUnit.SECONDS)) {
                return toolError(toolName, "timeout", "List tool timed out.");
            }
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            return toolError(toolName, "interrupted", "List tool was interrupted.");
        }
        return holder[0];
    }

    private String toolArg(JSONObject arguments, String name, String fallback) {
        String value = arguments == null ? "" : arguments.optString(name, "").trim();
        return value.isEmpty() ? fallback : value;
    }

    private JSONObject evidenceContextSnapshot(String latestUserText) {
        JSONObject json = new JSONObject();
        try {
            json.put("latestUserReport", latestUserText == null ? "" : latestUserText.trim());
            json.put("recentConversationEvidence", recentConversationEvidence());
            json.put("recentToolTrace", recentToolTraceSnapshot());
            json.put("pendingConfirmation", pendingToolConfirmation == null ? new JSONObject() : cloneJson(pendingToolConfirmation));
            json.put("lastVisibleStatus", lastVisibleStatus == null ? "" : lastVisibleStatus);
            json.put("appVersionName", BuildConfig.VERSION_NAME);
            json.put("versionCode", BuildConfig.VERSION_CODE);
            json.put("providerStatus", statusView == null ? "" : statusView.getText().toString());
            json.put("signedInState", hasSignedInHomeUser() ? "signed_in" : "signed_out");
            json.put("timestamp", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.US).format(new Date()));
        } catch (Exception ignored) {
        }
        return json;
    }

    private JSONArray recentConversationEvidence() {
        JSONArray array = new JSONArray();
        int start = Math.max(0, chatTurns.size() - 6);
        for (int i = start; i < chatTurns.size(); i++) {
            ChatTurn turn = chatTurns.get(i);
            try {
                array.put(new JSONObject().put("role", turn.role).put("text", turn.text));
            } catch (Exception ignored) {
            }
        }
        return array;
    }

    private JSONArray recentToolTraceSnapshot() {
        JSONArray copy = new JSONArray();
        synchronized (toolTraceLock) {
            for (int i = 0; i < recentToolTrace.length(); i++) {
                JSONObject item = recentToolTrace.optJSONObject(i);
                if (item != null) {
                    copy.put(cloneJson(item));
                }
            }
        }
        return copy;
    }

    private void rememberToolTrace(String toolName, JSONObject arguments, JSONObject result) {
        synchronized (toolTraceLock) {
            try {
                recentToolTrace.put(new JSONObject()
                        .put("toolName", toolName == null ? "" : toolName)
                        .put("arguments", arguments == null ? new JSONObject() : cloneJson(arguments))
                        .put("result", result == null ? new JSONObject() : cloneJson(result)));
                while (recentToolTrace.length() > 6) {
                    recentToolTrace.remove(0);
                }
            } catch (Exception ignored) {
            }
        }
    }

    private JSONObject resultJson(String toolName, HomeTaskClient.Result result) {
        JSONObject json = new JSONObject();
        try {
            json.put("tool", toolName);
            json.put("ok", result != null && result.ok);
            json.put("error", result != null && result.ok ? "" : "list_error");
            json.put("spokenMessage", result == null ? "" : result.spokenMessage);
            json.put("detail", result == null ? "empty result" : result.detail);
        } catch (Exception ignored) {
        }
        return json;
    }

    private JSONObject listResultJson(String toolName, HomeTaskClient.ListResult result) {
        JSONObject json = new JSONObject();
        try {
            json.put("tool", toolName);
            json.put("ok", result != null && result.ok);
            json.put("error", result != null && result.ok ? "" : "list_error");
            json.put("spokenMessage", result == null ? "" : result.spokenMessage);
            json.put("detail", result == null ? "empty result" : result.detail);
            json.put("listName", result == null ? "" : result.listName);
            JSONArray items = new JSONArray();
            if (result != null) {
                for (HomeTaskClient.HomeTask task : result.tasks) {
                    items.put(new JSONObject()
                            .put("id", task.id)
                            .put("name", task.name)
                            .put("displayName", task.displayName)
                            .put("description", task.description));
                }
            }
            json.put("items", items);
        } catch (Exception ignored) {
        }
        return json;
    }

    private JSONObject toolError(String toolName, String error, String detail) {
        JSONObject result = new JSONObject();
        try {
            result.put("tool", toolName == null ? "" : toolName);
            result.put("ok", false);
            result.put("error", error == null ? "" : error);
            result.put("detail", detail == null ? "" : detail);
        } catch (Exception ignored) {
        }
        return result;
    }

    private void finishAgentReply(String clean, String replyText, String narration, String status, JSONObject pendingConfirmation) {
        String finalResponse = replyText == null || replyText.trim().isEmpty() ? "I did not get a useful reply from GPT-5.5." : replyText.trim();
        chatTurns.add(new ChatTurn("assistant", finalResponse));
        trimChatTurns();
        JSONObject pendingForUi = cloneJson(pendingConfirmation);
        main.post(() -> {
            setBusy(false);
            String displayedResponse = pendingForUi != null
                    ? appendAssistantMessageRaw(finalResponse)
                    : appendAssistantMessage(finalResponse, clean);
            if (pendingForUi != null) {
                appendPendingConfirmationCard(pendingForUi);
            }
            if (status != null && !status.trim().isEmpty()) {
                appendStatus(status.trim());
            }
            speak(displayedResponse);
        });
    }

    private JSONObject cloneJson(JSONObject json) {
        if (json == null) {
            return null;
        }
        try {
            return new JSONObject(json.toString());
        } catch (Exception ex) {
            LocalLog.warn("agent", "pending_confirmation_clone_failed: " + shortMessage(ex.getMessage()));
            return null;
        }
    }

    private JSONObject currentTimeContext() {
        JSONObject json = new JSONObject();
        try {
            long nowMillis = System.currentTimeMillis();
            TimeZone zone = TimeZone.getDefault();
            SimpleDateFormat iso = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US);
            iso.setTimeZone(zone);
            json.put("nowEpochMillis", nowMillis);
            json.put("nowIso", iso.format(new Date(nowMillis)));
            json.put("timeZoneId", zone.getID());
            json.put("timeZoneOffsetMillis", zone.getOffset(nowMillis));
            json.put("locale", Locale.getDefault().toLanguageTag());
        } catch (Exception ex) {
            LocalLog.warn("agent", "time_context_failed: " + shortMessage(ex.getMessage()));
        }
        return json;
    }

    private JSONObject workingMemorySnapshot() {
        synchronized (workingMemoryLock) {
            try {
                return new JSONObject(workingMemory.toString());
            } catch (Exception ex) {
                LocalLog.warn("agent", "working_memory_clone_failed: " + shortMessage(ex.getMessage()));
                return new JSONObject();
            }
        }
    }

    private void updateWorkingMemoryFromToolResult(String toolName, JSONObject arguments, JSONObject result) {
        if (toolName == null || result == null || !result.optBoolean("ok", false)) {
            return;
        }
        try {
            if ("docs.create".equals(toolName) || "docs.update".equals(toolName)) {
                JSONObject file = result.optJSONObject("file");
                rememberEntity("lastDocument", toolName,
                        file == null ? "" : file.optString("id", ""),
                        result.optString("title", file == null ? toolArg(arguments, "name", "") : file.optString("name", toolArg(arguments, "name", ""))),
                        result.optString("webViewLink", file == null ? "" : file.optString("webViewLink", "")));
                return;
            }
            if ("docs.read".equals(toolName)) {
                JSONObject file = result.optJSONObject("file");
                rememberEntity("lastDocument", toolName,
                        file == null ? toolArg(arguments, "fileId", "") : file.optString("id", toolArg(arguments, "fileId", "")),
                        file == null ? toolArg(arguments, "name", "") : file.optString("name", toolArg(arguments, "name", "")),
                        file == null ? "" : file.optString("webViewLink", ""));
                return;
            }
            if ("docs.search".equals(toolName)) {
                rememberSingleFileResult("lastDocument", toolName, result.optJSONArray("files"));
                return;
            }
            if ("drive.create_folder".equals(toolName)) {
                JSONObject file = result.optJSONObject("file");
                rememberEntity("lastFolder", toolName,
                        file == null ? "" : file.optString("id", ""),
                        result.optString("title", file == null ? toolArg(arguments, "name", "") : file.optString("name", toolArg(arguments, "name", ""))),
                        file == null ? "" : file.optString("webViewLink", ""));
                return;
            }
            if ("sheets.create".equals(toolName)) {
                rememberEntity("lastSheet", toolName,
                        result.optString("spreadsheetId", ""),
                        result.optString("title", toolArg(arguments, "title", "")),
                        result.optString("spreadsheetUrl", ""));
                return;
            }
            if ("sheets.search".equals(toolName)) {
                rememberSingleFileResult("lastSheet", toolName, result.optJSONArray("files"));
                return;
            }
            if ("sheets.read".equals(toolName) || "sheets.update".equals(toolName)) {
                JSONObject spreadsheet = result.optJSONObject("spreadsheet");
                String title = spreadsheet == null || spreadsheet.optJSONObject("properties") == null
                        ? toolArg(arguments, "name", "")
                        : spreadsheet.optJSONObject("properties").optString("title", toolArg(arguments, "name", ""));
                rememberEntity("lastSheet", toolName,
                        result.optString("spreadsheetId", toolArg(arguments, "spreadsheetId", "")),
                        title,
                        spreadsheet == null ? "" : spreadsheet.optString("spreadsheetUrl", ""));
                return;
            }
            if ("gmail.create_draft".equals(toolName) || "gmail.update_draft".equals(toolName)) {
                rememberDraft(toolName, result.optString("draftId", toolArg(arguments, "draftId", "")), toolArg(arguments, "subject", ""));
                return;
            }
            if ("calendar.search".equals(toolName)) {
                JSONArray events = result.optJSONArray("events");
                if (events != null && events.length() == 1) rememberCalendarEvent(toolName, events.optJSONObject(0));
                return;
            }
            if ("calendar.read".equals(toolName) || "calendar.create_event".equals(toolName) || "calendar.update_event".equals(toolName) || "calendar.respond_event".equals(toolName)) {
                rememberCalendarEvent(toolName, result.optJSONObject("event"));
            }
            if ("contacts.search".equals(toolName)) {
                JSONArray contacts = result.optJSONArray("contacts");
                if (contacts != null && contacts.length() == 1) rememberContact(toolName, contacts.optJSONObject(0));
                return;
            }
            if ("contacts.read".equals(toolName)) {
                rememberContact(toolName, result.optJSONObject("contact"));
            }
        } catch (Exception ex) {
            LocalLog.warn("agent", "working_memory_update_failed tool=" + toolName + " detail=" + shortMessage(ex.getMessage()));
        }
    }

    private void rememberSingleFileResult(String key, String sourceTool, JSONArray files) throws Exception {
        if (files == null || files.length() != 1) return;
        JSONObject file = files.optJSONObject(0);
        if (file == null) return;
        rememberEntity(key, sourceTool, file.optString("id", ""), file.optString("name", ""), file.optString("webViewLink", ""));
    }

    private void rememberEntity(String key, String sourceTool, String fileId, String name, String link) throws Exception {
        if (fileId == null || fileId.trim().isEmpty()) return;
        JSONObject entity = new JSONObject()
                .put("fileId", fileId.trim())
                .put("name", name == null ? "" : name.trim())
                .put("webViewLink", link == null ? "" : link.trim())
                .put("sourceTool", sourceTool == null ? "" : sourceTool);
        synchronized (workingMemoryLock) {
            workingMemory.put(key, entity);
        }
        LocalLog.info("agent_trace", "working_memory_update " + key + "=" + entity.toString());
    }

    private void rememberDraft(String sourceTool, String draftId, String subject) throws Exception {
        if (draftId == null || draftId.trim().isEmpty()) return;
        JSONObject draft = new JSONObject()
                .put("draftId", draftId.trim())
                .put("subject", subject == null ? "" : subject.trim())
                .put("sourceTool", sourceTool == null ? "" : sourceTool);
        synchronized (workingMemoryLock) {
            workingMemory.put("lastEmailDraft", draft);
        }
        LocalLog.info("agent_trace", "working_memory_update lastEmailDraft=" + draft.toString());
    }

    private void rememberContact(String sourceTool, JSONObject contact) throws Exception {
        if (contact == null) return;
        JSONObject memory = new JSONObject();
        memory.put("resourceName", contact.optString("resourceName", ""));
        memory.put("displayName", contact.optString("displayName", ""));
        memory.put("primaryEmail", contact.optString("primaryEmail", ""));
        memory.put("emailAddresses", contact.optJSONArray("emailAddresses") == null ? new JSONArray() : contact.optJSONArray("emailAddresses"));
        memory.put("sourceTool", sourceTool);
        synchronized (workingMemoryLock) {
            workingMemory.put("lastContact", memory);
        }
        LocalLog.info("agent_trace", "working_memory_update lastContact=" + memory.toString());
    }

    private void rememberCalendarEvent(String sourceTool, JSONObject event) throws Exception {
        if (event == null || event.optString("id", "").trim().isEmpty()) return;
        JSONObject memory = new JSONObject()
                .put("eventId", event.optString("id", "").trim())
                .put("title", event.optString("summary", ""))
                .put("sourceTool", sourceTool == null ? "" : sourceTool);
        synchronized (workingMemoryLock) {
            workingMemory.put("lastCalendarEvent", memory);
        }
        LocalLog.info("agent_trace", "working_memory_update lastCalendarEvent=" + memory.toString());
    }

    private void appendPendingConfirmationCard(JSONObject pending) {
        if (chatLogContainer == null || pending == null) {
            return;
        }
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(14), dp(16), dp(14));
        card.setBackground(makeActionCardBackground());
        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        cardParams.setMargins(0, dp(8), 0, dp(8));
        card.setLayoutParams(cardParams);

        TextView title = new TextView(this);
        title.setText(pending.optString("title", "Confirm Action"));
        title.setTextSize(16);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(COLOR_TEXT);
        card.addView(title, matchWrap());

        TextView summary = new TextView(this);
        summary.setText(pending.optString("summary", "Confirm this action."));
        summary.setTextSize(14);
        summary.setTextColor(COLOR_SECONDARY);
        summary.setPadding(0, dp(6), 0, dp(10));
        card.addView(summary, matchWrap());

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.CENTER_VERTICAL);

        Button confirm = button("Confirm", 14, "Confirm and run this action");
        confirm.setBackgroundColor(COLOR_ACCENT);
        confirm.setTextColor(COLOR_BACKGROUND);
        Button cancel = button("Cancel", 14, "Cancel this pending action");
        cancel.setBackgroundColor(COLOR_CARD);
        cancel.setTextColor(COLOR_TEXT);
        buttons.addView(confirm, weightedHeight(dp(46)));
        buttons.addView(cancel, weightedHeight(dp(46)));
        card.addView(buttons, matchWrap());

        confirm.setOnClickListener(v -> submitPendingToolConfirmation());
        cancel.setOnClickListener(v -> cancelPendingToolConfirmation());
        chatLogContainer.addView(card);
        chatLogContainer.post(this::scrollChatToBottom);
    }

    private void submitPendingToolConfirmation() {
        JSONObject pending = cloneJson(pendingToolConfirmation);
        if (pending == null) {
            showAssistantMessage("There is no pending action to confirm.");
            return;
        }
        String action = pending.optString("action", "confirm").trim();
        submitMessage("confirm " + (action.isEmpty() ? "action" : action), false);
    }

    private void cancelPendingToolConfirmation() {
        pendingToolConfirmation = null;
        showAssistantMessage("Canceled.");
    }

    private String buildGeminiPrompt(String latestUserText) {
        String transcript = recentTranscriptSnapshot();
        if (ChatSystemShape.isBrainstormIntent(latestUserText)) {
            return ChatSystemShape.buildBrainstormPrompt(latestUserText, conversationSummary, transcript);
        }
        if (ChatSystemShape.isRecipeIntent(latestUserText)) {
            return ChatSystemShape.buildRecipePrompt(latestUserText, conversationSummary, transcript);
        }
        return ChatSystemShape.buildMainPrompt(latestUserText, conversationSummary, transcript);
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
        if (!firebaseConfigured || googleIdentitySignInClient == null) {
            speak("Firebase is not configured. Add google services JSON, rebuild, and try again.");
            return;
        }
        startActivityForResult(googleIdentitySignInClient.getSignInIntent(), REQUEST_GOOGLE_SIGN_IN);
    }

    private void checkGoogleDriveDiagnostic() {
        if (googleDriveClient == null) {
            showAssistantMessage("Google Drive diagnostic is not available in this build.");
            return;
        }
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (account == null || account.getAccount() == null) {
            showAssistantMessage("Sign in with Google first.");
            startGoogleSignIn();
            return;
        }
        if (!account.getGrantedScopes().contains(new Scope(GoogleDriveClient.DRIVE_METADATA_SCOPE))) {
            showAssistantMessage("Google Drive permission is missing. I am reopening Google sign-in for Drive access.");
            startGoogleSignIn();
            return;
        }
        appendStatus("Checking Google Drive directly...");
        executor.execute(() -> {
            GoogleDriveClient.DriveResult result = googleDriveClient.listFirstFiles(account);
            main.post(() -> handleDriveDiagnosticResult(result, "Check Google Drive"));
        });
    }

    private void showDriveAnswer(String text) {
        appendChatBubble("Home Center", text, false, false);
        recordTranscriptTurn("assistant", text);
        speak(text);
    }

    private void handleDriveAnswer(GoogleDriveClient.DriveAnswer answer, String latestUserText) {
        if (answer == null) {
            showDriveAnswer("Google Drive failed: empty result.");
            return;
        }
        if (answer.recoverableAuthException != null) {
            appendStatus("Google Drive permission needs approval: " + shortMessage(answer.answer));
            try {
                startActivityForResult(answer.recoverableAuthException.getIntent(), REQUEST_DRIVE_AUTH);
            } catch (Exception ex) {
                showDriveAnswer("Google Drive permission approval failed to open: " + shortMessage(ex.getMessage()));
            }
            return;
        }
        if (!answer.ok) {
            showDriveAnswer("Google Drive failed [" + answer.error + "]: " + answer.answer);
            return;
        }
        if (!answer.documentId.isEmpty()) {
            lastDriveDocumentId = answer.documentId;
            lastDriveDocumentName = answer.documentName;
        }
        showDriveAnswer(answer.answer);
    }

    private void handleDriveDiagnosticResult(GoogleDriveClient.DriveResult result) {
        handleDriveDiagnosticResult(result, null);
    }

    private void handleDriveDiagnosticResult(GoogleDriveClient.DriveResult result, String latestUserText) {
        if (result == null) {
            showAssistantMessage("Google Drive diagnostic failed: empty result.", latestUserText);
            return;
        }
        if (result.recoverableAuthException != null) {
            appendStatus("Google Drive permission needs approval: " + shortMessage(result.detail));
            try {
                startActivityForResult(result.recoverableAuthException.getIntent(), REQUEST_DRIVE_AUTH);
            } catch (Exception ex) {
                showDriveAnswer("Google Drive permission approval failed to open: " + shortMessage(ex.getMessage()));
            }
            return;
        }
        if (!result.ok) {
            showAssistantMessage("Google Drive check failed [" + result.error + "]: " + result.detail, latestUserText);
            return;
        }
        StringBuilder answer = new StringBuilder("Google Drive is connected. ").append(result.detail);
        if (result.files.isEmpty()) {
            answer.append("\nNo files returned. ").append(result.detail);
        } else {
            for (GoogleDriveClient.DriveFile file : result.files) {
                String name = file.name == null || file.name.trim().isEmpty() ? "untitled" : file.name.trim();
                answer.append("\n- ").append(name);
            }
        }
        showAssistantMessage(answer.toString(), latestUserText);
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

    private void savePreference(Command command) {
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
        String listName = command.listName == null || command.listName.isEmpty() ? listEdit.getText().toString() : command.listName;
        homeTaskClient.savePreference(bucketEdit.getText().toString(), listName, command.item, command.state, result -> main.post(() -> {
            logResult("savePreference", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (!result.ok) {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
        }));
    }

    private void saveStoreTarget(Command command) {
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
        String listName = command.listName == null || command.listName.isEmpty() ? listEdit.getText().toString() : command.listName;
        homeTaskClient.saveStoreTarget(bucketEdit.getText().toString(), listName, command.item, command.state, result -> main.post(() -> {
            logResult("saveStoreTarget", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (!result.ok) {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
        }));
    }

    private void readGroceryPreferences(String listName) {
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
        String targetList = listName == null || listName.isEmpty() ? listEdit.getText().toString() : listName;
        setBusy(true);
        homeTaskClient.readPreferences(bucketEdit.getText().toString(), targetList, result -> main.post(() -> {
            setBusy(false);
            logResult("readPreferences", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (!result.ok) {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
        }));
    }

    private void buildWalmartCartDraft(String listName) {
        saveBucketPrefs();
        if (!hasHomeBucket()) {
            speakMissingBucket();
            return;
        }
        String targetList = listName == null || listName.isEmpty() ? listEdit.getText().toString() : listName;
        setBusy(true);
        homeTaskClient.buildCartDraft(bucketEdit.getText().toString(), targetList, result -> main.post(() -> {
            setBusy(false);
            logResult("buildCartDraft", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (result.ok) {
                String path = GroceryCartExport.writeDraft(this, result.detail);
                if (!path.isEmpty()) {
                    appendStatus("Saved cart draft: " + path);
                }
            } else {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
        }));
    }

    private void startCartReviewImport() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/json");
        try {
            startActivityForResult(intent, REQUEST_CART_REVIEW_IMPORT);
        } catch (ActivityNotFoundException ex) {
            showAssistantMessage("No file picker is available. Open the review bundle from Downloads and share it with Home Center if needed.");
        }
    }

    private void importCartReview(Intent data) {
        if (data == null || data.getData() == null) {
            showAssistantMessage("No cart review file was selected.");
            return;
        }
        try {
            String jsonText = readTextFromUri(data.getData());
            loadCartReview(jsonText);
            showCurrentCartReviewItem();
        } catch (Exception ex) {
            showAssistantMessage("Could not import cart review: " + shortMessage(ex.getMessage()));
        }
    }

    private String readTextFromUri(Uri uri) throws IOException {
        try (InputStream input = getContentResolver().openInputStream(uri)) {
            if (input == null) {
                throw new IOException("empty file");
            }
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
            return output.toString(StandardCharsets.UTF_8.name());
        }
    }

    private void loadCartReview(String jsonText) throws Exception {
        JSONObject root = new JSONObject(jsonText);
        CartRunStore.saveReview(this, jsonText);
        JSONArray review = root.optJSONArray("review");
        if (review == null) {
            throw new IllegalArgumentException("review array missing");
        }
        cartReviewItems.clear();
        for (int i = 0; i < review.length(); i++) {
            JSONObject obj = review.optJSONObject(i);
            if (obj == null) {
                continue;
            }
            CartReviewItem item = CartReviewItem.fromJson(obj);
            if (!item.item.isEmpty()) {
                cartReviewItems.add(item);
            }
        }
        cartReviewIndex = firstReviewIndex();
        appendStatus("Imported " + cartReviewItems.size() + " Walmart review item" + (cartReviewItems.size() == 1 ? "" : "s") + ".");
    }

    private int firstReviewIndex() {
        for (int i = 0; i < cartReviewItems.size(); i++) {
            String status = cartReviewItems.get(i).status;
            if (!isCartReviewDoneStatus(status)) {
                return i;
            }
        }
        return cartReviewItems.isEmpty() ? -1 : 0;
    }

    private void showCurrentCartReviewItem() {
        if (cartReviewItems.isEmpty() || cartReviewIndex < 0 || cartReviewIndex >= cartReviewItems.size()) {
            showAssistantMessage("No Walmart review items are loaded. Tap Cart review and import review-latest.json.");
            return;
        }
        CartReviewItem item = cartReviewItems.get(cartReviewIndex);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(18), dp(10), dp(18), dp(4));

        TextView summary = new TextView(this);
        summary.setText((cartReviewIndex + 1) + " of " + cartReviewItems.size()
                + "\n" + item.item
                + "\nQuantity: " + item.quantityText
                + "\nStatus: " + item.status
                + "\n" + item.reason
                + "\n" + walmartHandoffStatus(item.walmartBuyAgainUrl).label());
        summary.setTextSize(14);
        summary.setTextColor(Color.parseColor("#2E2E2E"));
        panel.addView(summary, matchWrap());

        EditText skuEdit = singleLineEdit("Walmart SKU", item.sku);
        EditText urlEdit = singleLineEdit("Product URL", item.productUrl);
        EditText nameEdit = singleLineEdit("Product name", item.productName);
        EditText quantityEdit = singleLineEdit("Quantity", item.quantityValue());
        EditText sourceEdit = singleLineEdit("Source", item.source.isEmpty() ? "buy_again" : item.source);
        EditText confidenceEdit = singleLineEdit("Confidence", item.confidence.isEmpty() ? "confirmed" : item.confidence);
        panel.addView(skuEdit, matchHeight(dp(54)));
        panel.addView(urlEdit, matchHeight(dp(54)));
        panel.addView(nameEdit, matchHeight(dp(54)));
        panel.addView(quantityEdit, matchHeight(dp(54)));
        panel.addView(sourceEdit, matchHeight(dp(54)));
        panel.addView(confidenceEdit, matchHeight(dp(54)));

        LinearLayout linkRow = new LinearLayout(this);
        linkRow.setOrientation(LinearLayout.HORIZONTAL);
        Button buyAgain = button("Buy Again", 12, "Open Walmart Buy Again");
        Button search = button("Search", 12, "Open Walmart search");
        linkRow.addView(buyAgain, weightedHeight(dp(46)));
        linkRow.addView(search, weightedHeight(dp(46)));
        panel.addView(linkRow, matchWrap());

        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setOrientation(LinearLayout.HORIZONTAL);
        Button skip = button("Skip", 12, "Skip this Walmart item");
        Button save = button("Save Mapping", 12, "Save this Walmart target");
        actionRow.addView(skip, weightedHeight(dp(46)));
        actionRow.addView(save, weightedHeight(dp(46)));
        panel.addView(actionRow, matchWrap());

        LinearLayout runnerRow = new LinearLayout(this);
        runnerRow.setOrientation(LinearLayout.HORIZONTAL);
        Button openProduct = button("Open Product", 12, "Open verified Walmart product");
        Button attemptAdd = button("Attempt Add", 12, "Ask Home Center cart runner to add this verified product");
        Button manualAdd = button("Manual Add", 12, "Open product for manual Walmart add");
        runnerRow.addView(openProduct, weightedHeight(dp(46)));
        runnerRow.addView(attemptAdd, weightedHeight(dp(46)));
        runnerRow.addView(manualAdd, weightedHeight(dp(46)));
        panel.addView(runnerRow, matchWrap());

        LinearLayout resultRow = new LinearLayout(this);
        resultRow.setOrientation(LinearLayout.HORIZONTAL);
        Button markAdded = button("Mark Added", 12, "Mark this Walmart item added");
        Button markBlocked = button("Blocked", 12, "Mark this Walmart item blocked");
        resultRow.addView(markAdded, weightedHeight(dp(46)));
        resultRow.addView(markBlocked, weightedHeight(dp(46)));
        panel.addView(resultRow, matchWrap());

        final AlertDialog[] dialogRef = new AlertDialog[1];
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Cart Review")
                .setView(panel)
                .setNegativeButton("Close", null)
                .create();
        dialogRef[0] = dialog;
        buyAgain.setOnClickListener(v -> openReviewUrl(item.walmartBuyAgainUrl));
        search.setOnClickListener(v -> openReviewUrl(item.walmartSearchUrl));
        skip.setOnClickListener(v -> {
            moveToNextCartReviewItem();
            dialogRef[0].dismiss();
            showCurrentCartReviewItem();
        });
        save.setOnClickListener(v -> saveCartReviewMapping(item, skuEdit, urlEdit, nameEdit, quantityEdit, sourceEdit, confidenceEdit, dialogRef[0]));
        openProduct.setOnClickListener(v -> openVerifiedProduct(item));
        attemptAdd.setOnClickListener(v -> armCartRunner(item, dialogRef[0]));
        manualAdd.setOnClickListener(v -> openProductForManualAdd(item, dialogRef[0]));
        markAdded.setOnClickListener(v -> markCartReviewStatus(item, CartRunStore.STATUS_ADDED, dialogRef[0]));
        markBlocked.setOnClickListener(v -> markCartReviewStatus(item, CartRunStore.STATUS_BLOCKED, dialogRef[0]));
        dialog.show();
    }

    private void openAccessibilitySettings() {
        showCartHelperDiagnostics();
        try {
            startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
            appendStatus("Enable Home Center cart helper, then return to Cart Review.");
        } catch (Exception ex) {
            showAssistantMessage("Could not open Accessibility settings: " + shortMessage(ex.getMessage()));
        }
    }

    private void showCartHelperDiagnostics() {
        String component = new ComponentName(this, WalmartCartAccessibilityService.class).flattenToString();
        boolean installed = false;
        boolean enabled = false;
        StringBuilder installedLabels = new StringBuilder();
        try {
            AccessibilityManager manager = (AccessibilityManager) getSystemService(ACCESSIBILITY_SERVICE);
            if (manager != null) {
                for (AccessibilityServiceInfo info : manager.getInstalledAccessibilityServiceList()) {
                    String id = info.getId();
                    String label = info.getResolveInfo() == null ? "unknown" : String.valueOf(info.getResolveInfo().loadLabel(getPackageManager()));
                    if (installedLabels.length() > 0) {
                        installedLabels.append(", ");
                    }
                    installedLabels.append(label).append(" [").append(id).append("]");
                    if (component.equals(id)) {
                        installed = true;
                    }
                }
                enabled = isCartHelperEnabled();
            }
        } catch (Exception ex) {
            appendStatus("Cart helper diagnostic failed: " + shortMessage(ex.getMessage()));
        }
        String message = "Cart helper component=" + component
                + " installed=" + installed
                + " enabled=" + enabled
                + " appVersion=" + BuildConfig.VERSION_NAME + " (" + BuildConfig.VERSION_CODE + ")"
                + " services=" + (installedLabels.length() == 0 ? "none visible" : installedLabels.toString());
        LocalLog.info("cart_runner", message);
        appendStatus(message);
        if (installed && !enabled) {
            appendStatus("Android restricted settings may block cart automation. Use Manual Add, then return and tap Mark Added.");
        }
    }

    private boolean isCartHelperEnabled() {
        String component = new ComponentName(this, WalmartCartAccessibilityService.class).flattenToString();
        try {
            AccessibilityManager manager = (AccessibilityManager) getSystemService(ACCESSIBILITY_SERVICE);
            if (manager == null) {
                return false;
            }
            for (AccessibilityServiceInfo info : manager.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)) {
                if (component.equals(info.getId())) {
                    return true;
                }
            }
        } catch (Exception ex) {
            LocalLog.warn("cart_runner", "enabled_check_failed " + shortMessage(ex.getMessage()));
        }
        return false;
    }

    private void openVerifiedProduct(CartReviewItem item) {
        if (!item.isVerified()) {
            showAssistantMessage("Verify brand, size, and quantity before opening the cart runner product.");
            return;
        }
        String url = item.verifiedProductUrl();
        if (url.isEmpty()) {
            showAssistantMessage("This verified item needs a Walmart product URL or SKU before cart running.");
            return;
        }
        openReviewUrl(url);
    }

    private void openProductForManualAdd(CartReviewItem item, AlertDialog dialog) {
        if (!item.isVerified()) {
            showAssistantMessage("Manual Add still needs a verified brand, size, quantity, and Walmart product URL.");
            return;
        }
        String url = item.verifiedProductUrl();
        if (url.isEmpty()) {
            showAssistantMessage("This verified item needs a Walmart product URL or SKU before manual add.");
            return;
        }
        CartRunStore.recordEvent(this, "manual_add_pressed", item.toJson());
        appendStatus("Manual Add: Walmart is opening. Cart event bridge: " + CartEventBridge.currentEventPath() + ". Tap Add in Walmart, return here, then tap Mark Added.");
        openReviewUrl(url);
        dialog.dismiss();
    }

    private void armCartRunner(CartReviewItem item, AlertDialog dialog) {
        if (!item.isVerified()) {
            showAssistantMessage("Cart runner only arms verified items. Verify brand, size, and quantity first.");
            return;
        }
        String url = item.verifiedProductUrl();
        if (url.isEmpty()) {
            showAssistantMessage("This verified item needs a Walmart product URL or SKU before cart running.");
            return;
        }
        if (!isCartHelperEnabled()) {
            appendStatus("Android restricted settings may block cart automation. Opening Manual Add instead.");
            openProductForManualAdd(item, dialog);
            return;
        }
        try {
            JSONObject armed = item.toJson();
            armed.put("status", CartRunStore.STATUS_ARMED);
            armed.put("armedAt", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(new Date()));
            armed.put("armedAtElapsed", SystemClock.elapsedRealtime());
            CartRunStore.armItem(this, armed);
            item.status = "opened";
            persistCartReviewState();
            appendStatus("Cart runner armed for " + item.item + ".");
            openReviewUrl(url);
            dialog.dismiss();
        } catch (Exception ex) {
            showAssistantMessage("Could not arm cart runner: " + shortMessage(ex.getMessage()));
        }
    }

    private void markCartReviewStatus(CartReviewItem item, String status, AlertDialog dialog) {
        item.status = status;
        item.reason = CartRunStore.STATUS_ADDED.equals(status) ? "Marked added after Walmart cart runner." : "Blocked during Walmart cart runner.";
        CartRunStore.recordEvent(this, status, item.toJson());
        persistCartReviewState();
        moveToNextCartReviewItem();
        dialog.dismiss();
        showCurrentCartReviewItem();
    }

    private boolean isCartReviewDoneStatus(String status) {
        return "mapped".equals(status) || "saved".equals(status) || CartRunStore.STATUS_ADDED.equals(status) || CartRunStore.STATUS_BLOCKED.equals(status);
    }

    private void persistCartReviewState() {
        try {
            JSONObject root = new JSONObject();
            JSONArray review = new JSONArray();
            for (CartReviewItem item : cartReviewItems) {
                review.put(item.toJson());
            }
            root.put("review", review);
            root.put("itemCount", cartReviewItems.size());
            root.put("updatedAt", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(new Date()));
            CartRunStore.saveReview(this, root.toString());
        } catch (Exception ex) {
            LocalLog.warn("cart_runner", "persist_failed " + shortMessage(ex.getMessage()));
        }
    }

    private void saveCartReviewMapping(CartReviewItem item, EditText skuEdit, EditText urlEdit, EditText nameEdit,
                                       EditText quantityEdit, EditText sourceEdit, EditText confidenceEdit, AlertDialog dialog) {
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
        String targetSpec = buildTargetSpec(
                skuEdit.getText().toString(),
                urlEdit.getText().toString(),
                nameEdit.getText().toString(),
                quantityEdit.getText().toString(),
                sourceEdit.getText().toString(),
                confidenceEdit.getText().toString());
        if (!targetSpec.contains("sku=") && !targetSpec.contains("productUrl=")) {
            showAssistantMessage("Paste a Walmart SKU or product URL before saving.");
            return;
        }
        String listName = listEdit == null || listEdit.getText().toString().trim().isEmpty() ? "shopping" : listEdit.getText().toString().trim();
        setBusy(true);
        homeTaskClient.saveStoreTarget(bucketEdit.getText().toString(), listName, item.item, targetSpec, result -> main.post(() -> {
            setBusy(false);
            logResult("saveCartReviewMapping", result);
            speak(result.spokenMessage);
            appendStatus("Detail: " + result.detail);
            if (result.ok) {
                item.status = "saved";
                moveToNextCartReviewItem();
                dialog.dismiss();
                showCurrentCartReviewItem();
            } else {
                appendStatus("Log: " + LocalLog.currentLogPath());
            }
        }));
    }

    private String buildTargetSpec(String sku, String url, String name, String quantity, String source, String confidence) {
        StringBuilder builder = new StringBuilder();
        appendSpec(builder, "sku", sku);
        appendSpec(builder, "productUrl", url);
        appendSpec(builder, "productName", name);
        appendSpec(builder, "quantity", quantity);
        appendSpec(builder, "source", source);
        appendSpec(builder, "confidence", confidence);
        return builder.toString();
    }

    private void appendSpec(StringBuilder builder, String key, String value) {
        String clean = value == null ? "" : value.trim().replace('|', ' ');
        if (clean.isEmpty()) {
            return;
        }
        if (builder.length() > 0) {
            builder.append('|');
        }
        builder.append(key).append('=').append(clean);
    }

    private void moveToNextCartReviewItem() {
        if (cartReviewItems.isEmpty()) {
            cartReviewIndex = -1;
            return;
        }
        int start = cartReviewIndex;
        for (int offset = 1; offset <= cartReviewItems.size(); offset++) {
            int candidate = (start + offset) % cartReviewItems.size();
            String status = cartReviewItems.get(candidate).status;
            if (!isCartReviewDoneStatus(status)) {
                cartReviewIndex = candidate;
                return;
            }
        }
        cartReviewIndex = Math.min(start, cartReviewItems.size() - 1);
        showAssistantMessage("All loaded Walmart review items are mapped or saved.");
    }

    private void openReviewUrl(String url) {
        String cleanUrl = url == null ? "" : url.trim();
        if (cleanUrl.isEmpty()) {
            showAssistantMessage("No Walmart link is available for this item.");
            return;
        }
        WalmartHandoffStatus status = walmartHandoffStatus(cleanUrl);
        LocalLog.info("walmart_handoff", "before_open " + status.summary());
        try {
            startActivity(walmartViewIntent(cleanUrl, true));
            appendStatus("Opened Walmart app link. " + status.summary());
            LocalLog.info("walmart_handoff", "direct_app_url_success " + cleanUrl);
            return;
        } catch (Exception directEx) {
            LocalLog.warn("walmart_handoff", "direct_app_url_failed " + shortMessage(directEx.getMessage()) + " " + status.summary());
        }
        try {
            startActivity(walmartViewIntent(cleanUrl, false));
            appendStatus("Opened Walmart link through Android chooser or browser. " + status.summary());
            LocalLog.info("walmart_handoff", "unscoped_url_success " + cleanUrl);
            return;
        } catch (Exception unscopedEx) {
            LocalLog.warn("walmart_handoff", "unscoped_url_failed " + shortMessage(unscopedEx.getMessage()) + " " + status.summary());
        }
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage(WALMART_PACKAGE);
            if (launch != null) {
                startActivity(launch);
                appendStatus("Opened Walmart app. Use Buy Again or Search there. " + status.summary());
                LocalLog.info("walmart_handoff", "launch_fallback_success");
                return;
            }
        } catch (Exception launchEx) {
            LocalLog.warn("walmart_handoff", "launch_fallback_failed " + shortMessage(launchEx.getMessage()) + " " + status.summary());
        }
        showAssistantMessage("Android could not route this Walmart link to an installed app or browser. " + status.summary());
    }

    private Intent walmartViewIntent(String url, boolean forceWalmartPackage) {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        intent.addCategory(Intent.CATEGORY_BROWSABLE);
        if (forceWalmartPackage) {
            intent.setPackage(WALMART_PACKAGE);
        }
        return intent;
    }

    private WalmartHandoffStatus walmartHandoffStatus(String url) {
        WalmartHandoffStatus status = new WalmartHandoffStatus();
        String cleanUrl = url == null || url.trim().isEmpty() ? WALMART_BUY_AGAIN_URL : url.trim();
        PackageManager packageManager = getPackageManager();
        try {
            packageManager.getPackageInfo(WALMART_PACKAGE, 0);
            status.packageVisible = true;
        } catch (Exception ex) {
            status.packageError = shortMessage(ex.getClass().getSimpleName() + ": " + ex.getMessage());
        }
        try {
            status.launchIntentAvailable = packageManager.getLaunchIntentForPackage(WALMART_PACKAGE) != null;
        } catch (Exception ex) {
            status.launchError = shortMessage(ex.getClass().getSimpleName() + ": " + ex.getMessage());
        }
        try {
            status.directUrlResolvable = packageManager.resolveActivity(walmartViewIntent(cleanUrl, true), PackageManager.MATCH_DEFAULT_ONLY) != null;
        } catch (Exception ex) {
            status.directError = shortMessage(ex.getClass().getSimpleName() + ": " + ex.getMessage());
        }
        try {
            status.unscopedUrlResolvable = packageManager.resolveActivity(walmartViewIntent(cleanUrl, false), PackageManager.MATCH_DEFAULT_ONLY) != null;
        } catch (Exception ex) {
            status.unscopedError = shortMessage(ex.getClass().getSimpleName() + ": " + ex.getMessage());
        }
        return status;
    }

    private boolean walmartAppInstalled() {
        WalmartHandoffStatus status = walmartHandoffStatus(WALMART_BUY_AGAIN_URL);
        LocalLog.info("walmart_handoff", "detect " + status.summary());
        return status.canReachWalmartApp();
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
            showAssistantMessage("Speech recognition is not available.");
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
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Say a Home Center message");
        try {
            setStatus("Listening...");
            recognizer.startListening(intent);
        } catch (ActivityNotFoundException ex) {
            showAssistantMessage("No speech recognizer is installed.");
        }
    }

    private void handlePhrase(String phrase) {
        setStatus("Heard: " + phrase);
        submitMessage(phrase, true);
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
                activeReadItems.add(task.displayName);
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

    private void setBusy(boolean busyState) {
        busy = busyState;
        updateThinkingHaptics(busyState);
        updateWorkingUi(busyState);
        if (submitButton != null) {
            submitButton.setEnabled(!busyState);
        }
        if (saveTaskButton != null) {
            saveTaskButton.setEnabled(!busyState);
        }
        if (createListButton != null) {
            createListButton.setEnabled(!busyState);
        }
        if (compactButton != null) {
            compactButton.setEnabled(!busyState);
        }
        if (inventoryButton != null) {
            inventoryButton.setEnabled(!busyState);
        }
        if (whatCanIMakeButton != null) {
            whatCanIMakeButton.setEnabled(!busyState);
        }
        if (brainstormButton != null) {
            brainstormButton.setEnabled(!busyState);
        }
        if (rescueButton != null) {
            rescueButton.setEnabled(!busyState);
        }
        if (promptOneButton != null) {
            promptOneButton.setEnabled(!busyState);
        }
        if (promptTwoButton != null) {
            promptTwoButton.setEnabled(!busyState);
        }
        if (promptThreeButton != null) {
            promptThreeButton.setEnabled(!busyState);
        }
        if (geminiSettingsButton != null) {
            geminiSettingsButton.setEnabled(!busyState);
        }
        if (cartReviewButton != null) {
            cartReviewButton.setEnabled(!busyState);
        }
        if (cartRunnerSettingsButton != null) {
            cartRunnerSettingsButton.setEnabled(!busyState);
        }
        if (cartRunnerCheckButton != null) {
            cartRunnerCheckButton.setEnabled(!busyState);
        }
    }

    private void updateWorkingUi(boolean active) {
        if (workingIndicatorView != null) {
            workingIndicatorView.setVisibility(active ? View.VISIBLE : View.GONE);
            workingIndicatorView.setText(active ? "Working..." : "");
        }
        if (submitButton != null) {
            submitButton.setText(active ? "Working..." : "Send");
            submitButton.setTextColor(active ? COLOR_TEXT : COLOR_BACKGROUND);
            submitButton.setBackgroundColor(active ? COLOR_PRIMARY : COLOR_ACCENT);
            submitButton.setContentDescription(active ? "Home Center is working" : "Send message");
            submitButton.setAlpha(active ? 0.85f : 1.0f);
        }
        if (messageEdit != null) {
            messageEdit.setEnabled(!active);
            messageEdit.setHint(active ? "Home Center is working..." : "Ask Home Center...");
            messageEdit.setAlpha(active ? 0.65f : 1.0f);
        }
        if (statusView != null) {
            if (active) {
                statusView.setText("Working...");
                statusView.setTextColor(COLOR_PRIMARY);
            } else {
                statusView.setTextColor(COLOR_SECONDARY);
                updateBackendStatus();
            }
        }
    }

    private void updateThinkingHaptics(boolean active) {
        if (!active) {
            thinkingHapticsActive = false;
            main.removeCallbacks(thinkingHapticPulse);
            return;
        }
        if (thinkingHapticsActive) {
            return;
        }
        thinkingHapticsActive = true;
        main.removeCallbacks(thinkingHapticPulse);
        main.post(thinkingHapticPulse);
    }

    private void refreshAuthStatus() {
        if (authStatusView == null) {
            return;
        }
        if (!firebaseConfigured) {
            authStatusView.setText("Google sign-in needs setup");
            authStatusView.setTextColor(COLOR_DANGER);
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.VISIBLE);
            }
            updateBackendStatus();
            return;
        }
        FirebaseUser user = firebaseAuth == null ? null : firebaseAuth.getCurrentUser();
        if (user == null) {
            authStatusView.setText("Sign in with Google");
            authStatusView.setTextColor(COLOR_PRIMARY);
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.VISIBLE);
            }
        } else {
            authStatusView.setText("Connected");
            authStatusView.setTextColor(COLOR_ACCENT);
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.GONE);
            }
        }
        updateBackendStatus();
    }

    private void speak(String message) {
        String clean = message == null ? "" : message.trim();
        if (clean.isEmpty()) {
            LocalLog.info("speech", "skip_empty_message");
            return;
        }
        lastSpoken = clean;
        setStatus(clean);
        pauseExternalPlaybackForSpeech();
        requestSpeechFocus();
        String utteranceId = "home_center_" + System.currentTimeMillis();
        activeSpeechUtteranceId = utteranceId;
        long sequence = beginSpeechSequence("new_speech_request");
        if (shouldUseCartesiaProxy()) {
            setSpeechPlaying(true);
            speakWithCartesia(clean, utteranceId, sequence);
            return;
        }
        String cause = cartesiaUnavailableCause();
        LocalLog.info("speech", "cartesia_unavailable cause=" + cause);
        speakWithDeviceTtsFallback(clean, utteranceId, sequence, cause);
    }

    private boolean shouldUseCartesiaProxy() {
        return cartesiaSpeechProxyClient != null && cartesiaSpeechProxyClient.isConfigured();
    }

    private String cartesiaUnavailableCause() {
        if (cartesiaSpeechProxyClient == null) {
            return "speech client missing";
        }
        if (!cartesiaSpeechProxyClient.isConfigured()) {
            return "config missing: set CARTESIA_PROXY_BASE_URL or CARTESIA_API_KEY";
        }
        return "unknown configuration failure";
    }

    private long beginSpeechSequence(String reason) {
        synchronized (this) {
            speechSequence += 1L;
            LocalLog.info("speech", "stop_reason=" + reason + " sequence=" + speechSequence); // includes stop_reason=new_speech_request
            stopCartesiaPlaybackLocked(reason);
            return speechSequence;
        }
    }

    private boolean isCurrentSpeechSequence(long sequence) {
        return speechSequence == sequence;
    }

    private void speakWithCartesia(String message, String utteranceId, long sequence) {
        executor.execute(() -> {
            HttpURLConnection connection = null;
            AudioTrack track = null;
            try {
                if (!isCurrentSpeechSequence(sequence)) {
                    LocalLog.info("speech", "stop_reason=stale_sequence sequence=" + sequence);
                    return;
                }
                connection = cartesiaSpeechProxyClient.openSpeechStream(message);
                if (!isCurrentSpeechSequence(sequence)) {
                    LocalLog.info("speech", "stop_reason=stale_sequence sequence=" + sequence);
                    return;
                }
                int minBufferSize = AudioTrack.getMinBufferSize(44100, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
                if (minBufferSize <= 0) {
                    throw new IOException("Unable to create audio track buffer");
                }
                track = new AudioTrack.Builder()
                        .setAudioAttributes(new AudioAttributes.Builder()
                                .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                                .build())
                        .setAudioFormat(new AudioFormat.Builder()
                                .setSampleRate(44100)
                                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                                .build())
                        .setTransferMode(AudioTrack.MODE_STREAM)
                        .setBufferSizeInBytes(Math.max(minBufferSize * 2, 8192))
                        .build();
                synchronized (this) {
                    if (!isCurrentSpeechSequence(sequence)) {
                        LocalLog.info("speech", "stop_reason=stale_sequence sequence=" + sequence);
                        track.release();
                        return;
                    }
                    activeCartesiaTrack = track;
                    track.play();
                }
                byte[] pcm = readSpeechPcm(connection.getInputStream(), sequence);
                saveSpeechDebugPcm(pcm, "latest-cartesia");
                long receivedBytes = pcm.length;
                long writtenBytes = writePcmToTrack(track, pcm, sequence);
                long finalReceivedBytes = receivedBytes;
                long finalWrittenBytes = writtenBytes;
                if (isCurrentSpeechSequence(sequence)) {
                    main.post(() -> {
                        LocalLog.info("speech", "stop_reason=stream_complete receivedBytes=" + finalReceivedBytes + " writtenBytes=" + finalWrittenBytes);
                        setSpeechPlaying(false);
                        abandonSpeechFocusFor(utteranceId);
                    });
                }
            } catch (Exception ex) {
                if (isCurrentSpeechSequence(sequence)) {
                    main.post(() -> {
                        if (!isCurrentSpeechSequence(sequence)) {
                            return;
                        }
                        String cause = speechFailureCause(ex);
                        LocalLog.info("speech", "stop_reason=cartesia_error detail=" + cause);
                        stopCartesiaPlayback("cartesia_error");
                        speakWithDeviceTtsFallback(message, utteranceId, sequence, cause);
                    });
                }
            } finally {
                if (track != null) {
                    boolean releaseTrack;
                    synchronized (this) {
                        releaseTrack = activeCartesiaTrack == track;
                        if (releaseTrack) {
                            activeCartesiaTrack = null;
                        }
                    }
                    if (releaseTrack) {
                        try {
                            track.stop();
                        } catch (Exception ignored) {
                        }
                        track.release();
                    }
                }
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private String speechFailureCause(Exception ex) {
        String message = ex == null ? "unknown playback failure" : shortMessage(ex.getMessage());
        String lower = message.toLowerCase(Locale.US);
        if (lower.contains("not configured") || lower.contains("config")) {
            return "config missing: " + message;
        }
        if (lower.contains("proxy returned http")) {
            return "proxy HTTP error: " + message;
        }
        if (lower.contains("api returned http")) {
            return "Cartesia API error: " + message;
        }
        if (lower.contains("connect") || lower.contains("failed to connect") || lower.contains("connection refused")) {
            return "proxy missing or unreachable: " + message;
        }
        if (lower.contains("stalled") || lower.contains("audio track") || lower.contains("write=")) {
            return "playback failure: " + message;
        }
        return "playback failure: " + message;
    }

    private void speakWithDeviceTtsFallback(String message, String utteranceId, long sequence, String cartesiaCause) {
        if (!isCurrentSpeechSequence(sequence)) {
            LocalLog.info("speech", "device_tts_skip_stale sequence=" + sequence);
            return;
        }
        if (deviceTextToSpeech != null && deviceTextToSpeechReady) {
            LocalLog.info("speech", "device_tts_fallback cause=" + shortMessage(cartesiaCause));
            setSpeechPlaying(true);
            int result = deviceTextToSpeech.speak(message, TextToSpeech.QUEUE_FLUSH, null, utteranceId);
            if (result != TextToSpeech.ERROR) {
                main.postDelayed(() -> {
                    if (isCurrentSpeechSequence(sequence)) {
                        setSpeechPlaying(false);
                        abandonSpeechFocusFor(utteranceId);
                    }
                }, Math.max(2500L, Math.min(60000L, message.length() * 85L)));
                return;
            }
            LocalLog.warn("speech", "device_tts_speak_failed cause=" + shortMessage(cartesiaCause));
        } else {
            LocalLog.warn("speech", "device_tts_unavailable ready=" + deviceTextToSpeechReady + " cause=" + shortMessage(cartesiaCause));
        }
        setStatus("Narration is unavailable right now: " + cartesiaCause + ".");
        setSpeechPlaying(false);
        abandonSpeechFocusFor(utteranceId);
    }

    private byte[] readSpeechPcm(InputStream rawInput, long sequence) throws IOException {
        try (InputStream input = new BufferedInputStream(rawInput); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while (isCurrentSpeechSequence(sequence) && (read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
            return output.toByteArray();
        }
    }

    private long writePcmToTrack(AudioTrack track, byte[] pcm, long sequence) throws IOException {
        long writtenBytes = 0L;
        int offset = 0;
        int zeroWrites = 0;
        while (offset < pcm.length && isCurrentSpeechSequence(sequence)) {
            int count = track.write(pcm, offset, pcm.length - offset, AudioTrack.WRITE_BLOCKING);
            if (count < 0) {
                throw new IOException("Cartesia audio playback failed: write=" + count + " receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes);
            }
            if (count == 0) {
                zeroWrites += 1;
                LocalLog.warn("speech", "audio_track_zero_write receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes + " zeroWrites=" + zeroWrites);
                if (zeroWrites > 500) {
                    break;
                }
                SystemClock.sleep(20L);
                continue;
            }
            zeroWrites = 0;
            offset += count;
            writtenBytes += count;
        }
        LocalLog.info("speech", "cartesia_pcm_write receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes);
        return writtenBytes;
    }

    private void saveSpeechDebugPcm(byte[] pcm, String name) {
        if (pcm == null || pcm.length == 0) {
            return;
        }
        try {
            File dir = new File(getExternalFilesDir(null), "speech-debug");
            if (!dir.exists() && !dir.mkdirs()) {
                return;
            }
            File file = new File(dir, name + ".pcm");
            try (FileOutputStream output = new FileOutputStream(file, false)) {
                output.write(pcm);
            }
            LocalLog.info("speech", "cartesia_debug_pcm path=" + file.getAbsolutePath() + " bytes=" + pcm.length);
        } catch (Exception ex) {
            LocalLog.warn("speech", "cartesia_debug_pcm_failed " + shortMessage(ex.getMessage()));
        }
    }

    private void stopCartesiaPlayback(String reason) {
        synchronized (this) {
            stopCartesiaPlaybackLocked(reason);
        }
    }

    private void stopSpeechPlayback() {
        synchronized (this) {
            speechSequence += 1L;
            LocalLog.info("speech", "stop_reason=user_stop sequence=" + speechSequence);
            stopCartesiaPlaybackLocked("user_stop");
            activeSpeechUtteranceId = "";
        }
        setSpeechPlaying(false);
        abandonSpeechFocus();
        setStatus("Speech stopped.");
    }

    private void stopCartesiaPlaybackLocked(String reason) {
        if (activeCartesiaTrack != null) {
            LocalLog.info("speech", "stopping_active_track reason=" + reason);
            try {
                activeCartesiaTrack.stop();
            } catch (Exception ignored) {
            }
            activeCartesiaTrack.release();
            activeCartesiaTrack = null;
        }
    }

    private void pauseExternalPlaybackForSpeech() {
        if (audioManager == null || externalPlaybackPausedForSpeech) {
            return;
        }
        if (!audioManager.isMusicActive()) {
            return;
        }
        dispatchMediaKey(KeyEvent.KEYCODE_MEDIA_PAUSE);
        externalPlaybackPausedForSpeech = true;
        LocalLog.info("audio", "paused_external_playback_for_speech");
    }

    private void resumeExternalPlaybackAfterSpeech() {
        if (audioManager == null || !externalPlaybackPausedForSpeech) {
            return;
        }
        dispatchMediaKey(KeyEvent.KEYCODE_MEDIA_PLAY);
        externalPlaybackPausedForSpeech = false;
        LocalLog.info("audio", "resumed_external_playback_after_speech");
    }

    private void dispatchMediaKey(int keyCode) {
        if (audioManager == null) {
            return;
        }
        long eventTime = System.currentTimeMillis();
        audioManager.dispatchMediaKeyEvent(new KeyEvent(eventTime, eventTime, KeyEvent.ACTION_DOWN, keyCode, 0));
        audioManager.dispatchMediaKeyEvent(new KeyEvent(eventTime, eventTime, KeyEvent.ACTION_UP, keyCode, 0));
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
            speechFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE)
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
        if (activeSpeechUtteranceId.isEmpty()) {
            resumeExternalPlaybackAfterSpeech();
        }
    }

    private void setStatus(String message) {
        if (message != null && !message.trim().isEmpty()) {
            LocalLog.info("status", shortMessage(message));
        }
        updateBackendStatus();
    }

    private void appendStatus(String message) {
        if (message != null && !message.trim().isEmpty()) {
            LocalLog.info("status", shortMessage(message));
        }
        updateBackendStatus();
    }

    private void setSpeechPlaying(boolean playing) {
        speechPlaying = playing;
        if (stopSpeechButton != null) {
            stopSpeechButton.setVisibility(playing ? View.VISIBLE : View.GONE);
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

    private void updateBackendStatus() {
        if (statusView == null) {
            return;
        }
        boolean hasGateway = BuildConfig.AGENT_GATEWAY_BASE_URL != null && !BuildConfig.AGENT_GATEWAY_BASE_URL.trim().isEmpty();
        boolean hasDirectOpenAi = BuildConfig.OPENAI_API_KEY != null && !BuildConfig.OPENAI_API_KEY.trim().isEmpty();
        boolean hasCartesia = BuildConfig.CARTESIA_API_KEY != null && !BuildConfig.CARTESIA_API_KEY.trim().isEmpty()
                || (BuildConfig.CARTESIA_PROXY_BASE_URL != null && !BuildConfig.CARTESIA_PROXY_BASE_URL.trim().isEmpty());
        String gptState = (hasGateway || hasDirectOpenAi) ? "GPT-5.5" : "GPT offline";
        String speechState = hasCartesia ? "Cartesia" : "Cartesia off";
        String model = effectiveGeminiModel().toLowerCase(Locale.US).contains("flash") ? "Gemini Flash" : effectiveGeminiModel();
        statusView.setText(gptState + " | " + speechState + " | " + model);
    }

    private void appendUserMessage(String text, boolean fromVoice) {
        appendChatBubble(fromVoice ? "You (voice)" : "You", text, true, false);
    }

    private String appendAssistantMessage(String text) {
        return appendAssistantMessage(text, null);
    }

    private String appendAssistantMessage(String text, String latestUserText) {
        String finalText = ChatSystemShape.enforceNextStep(text, latestUserText);
        return appendAssistantMessageRaw(finalText);
    }

    private String appendAssistantMessageRaw(String text) {
        String finalText = text == null ? "" : text.trim();
        appendChatBubble("Home Center", finalText, false, false);
        recordTranscriptTurn("assistant", finalText);
        return finalText;
    }

    private String showAssistantMessage(String text) {
        return showAssistantMessage(text, null);
    }

    private String showAssistantMessage(String text, String latestUserText) {
        String finalText = appendAssistantMessage(text, latestUserText);
        speak(finalText);
        return finalText;
    }


    private void appendDashboardCard() {
        if (chatLogContainer == null) {
            return;
        }
        String sync = hasSignedInHomeUser() ? "Google is signed in." : "Sign in with Google to enable the dashboard.";
        String gateway = BuildConfig.AGENT_GATEWAY_BASE_URL == null || BuildConfig.AGENT_GATEWAY_BASE_URL.trim().isEmpty()
                ? "GPT-5.5 gateway is not configured yet."
                : "GPT-5.5, web search, Google tools, lists, TickTick, and Cartesia route through the gateway.";
        appendChatBubble("Dashboard", startupGreeting + "\n\n" + sync + "\n" + gateway
                + "\n\nTry: add eggs to shopping, read shopping list, search the web for dinner ideas, or create a Google Doc.", false, true);
    }

    private void appendQuickActionsCard() {
        if (chatLogContainer == null) {
            return;
        }
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(14), dp(16), dp(14));
        card.setBackground(makeActionCardBackground());
        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        cardParams.setMargins(0, dp(8), 0, dp(8));
        card.setLayoutParams(cardParams);

        TextView title = new TextView(this);
        title.setText("Quick actions");
        title.setTextSize(14);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(Color.parseColor("#5B4B2A"));
        card.addView(title, matchWrap());

        TextView subtitle = new TextView(this);
        subtitle.setText("Tap one to send it like a support reply.");
        subtitle.setTextSize(12);
        subtitle.setTextColor(Color.parseColor("#7A6F5E"));
        subtitle.setPadding(0, dp(2), 0, dp(10));
        card.addView(subtitle, matchWrap());

        List<ChatSystemShape.QuickAction> actions = ChatSystemShape.defaultQuickActions();
        for (int i = 0; i < actions.size(); i += 3) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, 0, 0, dp(8));
            for (int j = i; j < Math.min(i + 3, actions.size()); j++) {
                ChatSystemShape.QuickAction action = actions.get(j);
                row.addView(chatActionButton(action), weightedHeight(dp(44)));
            }
            card.addView(row, matchWrap());
        }

        chatLogContainer.addView(card);
        chatLogContainer.post(this::scrollChatToBottom);
    }

    private LinearLayout buildTemplateBlocksPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(14), dp(12), dp(14), dp(12));
        panel.setBackground(makeActionCardBackground());

        LinearLayout.LayoutParams panelParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        panelParams.setMargins(0, dp(8), 0, dp(8));
        panel.setLayoutParams(panelParams);

        TextView title = new TextView(this);
        title.setText("Blocks");
        title.setTextSize(14);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(Color.parseColor("#5B4B2A"));
        panel.addView(title, matchWrap());

        TextView subtitle = new TextView(this);
        subtitle.setText("Tap a reusable block to prefill the composer.");
        subtitle.setTextSize(12);
        subtitle.setTextColor(Color.parseColor("#7A6F5E"));
        subtitle.setPadding(0, dp(2), 0, dp(10));
        panel.addView(subtitle, matchWrap());

        List<ChatSystemShape.TemplateBlock> blocks = ChatSystemShape.defaultTemplateBlocks();
        for (int i = 0; i < blocks.size(); i += 2) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, 0, 0, dp(8));
            for (int j = i; j < Math.min(i + 2, blocks.size()); j++) {
                ChatSystemShape.TemplateBlock block = blocks.get(j);
                row.addView(templateBlockButton(block), weightedHeight(dp(60)));
            }
            panel.addView(row, matchWrap());
        }

        return panel;
    }

    private LinearLayout buildCartReviewPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(14), dp(10), dp(14), dp(10));
        panel.setBackground(makeActionCardBackground());

        TextView title = new TextView(this);
        title.setText("Walmart cart review");
        title.setTextSize(14);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(Color.parseColor("#5B4B2A"));
        panel.addView(title, matchWrap());

        TextView subtitle = new TextView(this);
        subtitle.setText(walmartHandoffStatus(WALMART_BUY_AGAIN_URL).label() + " Import a review bundle.");
        subtitle.setTextSize(12);
        subtitle.setTextColor(Color.parseColor("#7A6F5E"));
        panel.addView(subtitle, matchWrap());

        cartReviewButton = new Button(this);
        cartReviewButton.setText("Cart review");
        cartReviewButton.setAllCaps(false);
        cartReviewButton.setTextSize(14);
        cartReviewButton.setTextColor(Color.WHITE);
        cartReviewButton.setBackgroundColor(Color.parseColor("#34634C"));
        panel.addView(cartReviewButton, matchHeight(dp(48)));
        cartRunnerSettingsButton = new Button(this);
        cartRunnerSettingsButton.setText("Enable cart helper");
        cartRunnerSettingsButton.setAllCaps(false);
        cartRunnerSettingsButton.setTextSize(14);
        cartRunnerSettingsButton.setTextColor(Color.WHITE);
        cartRunnerSettingsButton.setBackgroundColor(Color.parseColor("#5B4B2A"));
        panel.addView(cartRunnerSettingsButton, matchHeight(dp(48)));
        cartRunnerCheckButton = new Button(this);
        cartRunnerCheckButton.setText("Check helper");
        cartRunnerCheckButton.setAllCaps(false);
        cartRunnerCheckButton.setTextSize(14);
        cartRunnerCheckButton.setTextColor(Color.WHITE);
        cartRunnerCheckButton.setBackgroundColor(Color.parseColor("#4B5870"));
        panel.addView(cartRunnerCheckButton, matchHeight(dp(48)));
        return panel;
    }

    private void appendTemplateBlocksCard() {
        if (chatLogContainer == null) {
            return;
        }
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(14), dp(16), dp(14));
        card.setBackground(makeActionCardBackground());
        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        cardParams.setMargins(0, dp(8), 0, dp(8));
        card.setLayoutParams(cardParams);

        TextView title = new TextView(this);
        title.setText("Template blocks");
        title.setTextSize(14);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(Color.parseColor("#5B4B2A"));
        card.addView(title, matchWrap());

        TextView subtitle = new TextView(this);
        subtitle.setText("Tap one to fill a reusable response block into the composer.");
        subtitle.setTextSize(12);
        subtitle.setTextColor(Color.parseColor("#7A6F5E"));
        subtitle.setPadding(0, dp(2), 0, dp(10));
        card.addView(subtitle, matchWrap());

        List<ChatSystemShape.TemplateBlock> blocks = ChatSystemShape.defaultTemplateBlocks();
        for (int i = 0; i < blocks.size(); i += 2) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, 0, 0, dp(8));
            for (int j = i; j < Math.min(i + 2, blocks.size()); j++) {
                ChatSystemShape.TemplateBlock block = blocks.get(j);
                row.addView(templateBlockButton(block), weightedHeight(dp(56)));
            }
            card.addView(row, matchWrap());
        }

        chatLogContainer.addView(card);
        chatLogContainer.post(this::scrollChatToBottom);
    }

    private Button templateBlockButton(ChatSystemShape.TemplateBlock block) {
        Button button = promptButton(block.label, ChatSystemShape.renderTemplateBlock(block));
        button.setTextSize(11);
        button.setBackgroundColor(Color.parseColor("#EAF1FF"));
        button.setTextColor(Color.parseColor("#23406A"));
        button.setOnClickListener(v -> fillPrompt(ChatSystemShape.renderTemplateBlock(block)));
        return button;
    }

    private Button chatActionButton(ChatSystemShape.QuickAction action) {
        Button button = new Button(this);
        button.setText(action.label);
        button.setTextSize(12);
        button.setAllCaps(false);
        button.setBackgroundColor(Color.parseColor("#FFF1C7"));
        button.setTextColor(Color.parseColor("#6B4C00"));
        button.setMinWidth(0);
        button.setMinHeight(0);
        button.setPadding(dp(8), dp(8), dp(8), dp(8));
        if (action.isSettings()) {
            button.setOnClickListener(v -> showGeminiSettings());
        } else if (action.isCompact()) {
            button.setOnClickListener(v -> compactConversation());
        } else {
            button.setOnClickListener(v -> runQuickAction(action.prompt));
        }
        return button;
    }

    private void runQuickAction(String prompt) {
        if (busy) {
            appendStatus("Finish the current request first.");
            return;
        }
        if (prompt == null || prompt.trim().isEmpty()) {
            return;
        }
        fillPrompt(prompt);
        submitTypedMessage();
    }

    private GradientDrawable makeActionCardBackground() {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setCornerRadius(dp(20));
        drawable.setColor(COLOR_SURFACE);
        drawable.setStroke(dp(1), COLOR_CARD);
        return drawable;
    }

    private void appendChatBubble(String label, String text, boolean user, boolean system) {
        if (chatLogContainer == null || text == null || text.trim().isEmpty()) {
            return;
        }
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));
        row.setPadding(0, dp(6), 0, dp(6));
        row.setGravity(user ? Gravity.END : Gravity.START);

        TextView chip = new TextView(this);
        chip.setText(label);
        chip.setTextSize(11);
        chip.setTypeface(Typeface.DEFAULT_BOLD);
        chip.setTextColor(system ? COLOR_SECONDARY : COLOR_PRIMARY);
        chip.setPadding(dp(6), 0, dp(6), dp(3));
        row.addView(chip);

        TextView bubble = new TextView(this);
        bubble.setText(text);
        bubble.setTextSize(16);
        bubble.setTextColor(COLOR_TEXT);
        bubble.setPadding(dp(18), dp(14), dp(18), dp(14));
        bubble.setMaxWidth((int) (getResources().getDisplayMetrics().widthPixels * 0.80f));
        bubble.setBackground(makeBubbleBackground(user, system));
        wireMessageBubbleInteractions(bubble, text);
        LinearLayout.LayoutParams bubbleParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        bubbleParams.setMargins(user ? dp(42) : 0, 0, user ? 0 : dp(42), 0);
        bubble.setLayoutParams(bubbleParams);
        row.addView(bubble);

        chatLogContainer.addView(row);
        chatLogContainer.post(() -> {
            scrollChatToBottom();
            captureVisualEvidenceIfDebugBuild("chat");
        });
    }

    private void wireMessageBubbleInteractions(TextView bubble, String text) {
        final long[] lastTapAt = new long[]{0L};
        bubble.setClickable(true);
        bubble.setLongClickable(true);
        bubble.setContentDescription("Message. Long press to copy. Double tap to replay. " + text);
        bubble.setOnLongClickListener(v -> {
            copyMessageToClipboard(text);
            return true;
        });
        bubble.setOnClickListener(v -> {
            long now = SystemClock.uptimeMillis();
            if (now - lastTapAt[0] <= ViewConfiguration.getDoubleTapTimeout()) {
                lastTapAt[0] = 0L;
                replayMessageText(text);
                return;
            }
            lastTapAt[0] = now;
        });
    }

    private void copyMessageToClipboard(String text) {
        String clean = text == null ? "" : text.trim();
        if (clean.isEmpty()) {
            return;
        }
        ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        if (clipboard != null) {
            clipboard.setPrimaryClip(ClipData.newPlainText("Home Center message", clean));
            Toast.makeText(this, "Message copied", Toast.LENGTH_SHORT).show();
            LocalLog.info("chat", "message_copied chars=" + clean.length());
        }
    }

    private void replayMessageText(String text) {
        String clean = text == null ? "" : text.trim();
        if (clean.isEmpty()) {
            return;
        }
        Toast.makeText(this, "Replaying message", Toast.LENGTH_SHORT).show();
        LocalLog.info("chat", "message_replay chars=" + clean.length());
        speak(clean);
    }

    private void captureVisualEvidenceIfDebugBuild(String reason) {
        if (!BuildConfig.DEBUG || !visualEvidenceEnabled) {
            return;
        }
        main.postDelayed(() -> {
            try {
                View root = getWindow() == null ? null : getWindow().getDecorView().getRootView();
                if (root == null || root.getWidth() <= 0 || root.getHeight() <= 0) {
                    return;
                }
                Bitmap bitmap = Bitmap.createBitmap(root.getWidth(), root.getHeight(), Bitmap.Config.ARGB_8888);
                Canvas canvas = new Canvas(bitmap);
                root.draw(canvas);
                writeVisualEvidenceBitmap(bitmap, reason);
                bitmap.recycle();
            } catch (Exception ex) {
                LocalLog.warn("visual_evidence", "capture_failed: " + shortMessage(ex.getMessage()));
            }
        }, 600L);
    }

    private void writeVisualEvidenceBitmap(Bitmap bitmap, String reason) throws IOException {
        ContentValues values = new ContentValues();
        String stamp = new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(new Date());
        values.put(MediaStore.Downloads.DISPLAY_NAME, "home_center_app_" + reason + "_" + stamp + ".png");
        values.put(MediaStore.Downloads.MIME_TYPE, "image/png");
        values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/visual-red/");
        Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) {
            throw new IOException("MediaStore insert returned null");
        }
        try (OutputStream out = getContentResolver().openOutputStream(uri)) {
            if (out == null) {
                throw new IOException("MediaStore output stream returned null");
            }
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
        LocalLog.info("visual_evidence", "captured reason=" + reason + " uri=" + uri);
    }

    private GradientDrawable makeBubbleBackground(boolean user, boolean system) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setCornerRadius(dp(24));
        if (system) {
            drawable.setColor(COLOR_SURFACE);
            drawable.setStroke(dp(1), COLOR_CARD);
        } else if (user) {
            drawable.setColor(Color.parseColor("#254D35"));
            drawable.setStroke(dp(1), COLOR_ACCENT);
        } else {
            drawable.setColor(COLOR_CARD);
            drawable.setStroke(dp(1), Color.parseColor("#3A3A3A"));
        }
        return drawable;
    }

    private GradientDrawable makePanelBackground() {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setCornerRadius(dp(22));
        drawable.setColor(COLOR_SURFACE);
        drawable.setStroke(dp(1), COLOR_CARD);
        return drawable;
    }

    private void scrollChatToBottom() {
        if (chatScroll != null) {
            chatScroll.fullScroll(View.FOCUS_DOWN);
        }
    }

    private void trimChatTurns() {
        while (chatTurns.size() > MAX_RECORDED_TURNS) {
            chatTurns.remove(0);
        }
    }

    private void compactConversation() {
        if (busy) {
            appendStatus("Finish the current request first.");
            return;
        }
        if (chatTurns.isEmpty() && conversationSummary.isEmpty()) {
            showAssistantMessage("Nothing to compact yet.");
            return;
        }
        String apiKey = effectiveGeminiApiKey();
        if (apiKey.isEmpty() || geminiClient == null) {
            String fallback = summarizeLocally();
            applyConversationSummary(fallback);
            appendStatus("Conversation compacted locally.");
            return;
        }
        setBusy(true);
        setStatus("Compacting chat...");
        executor.execute(() -> {
            try {
                String summary = geminiClient.generateReply(buildCompactionPrompt());
                String finalSummary = clean(summary);
                if (finalSummary.isEmpty()) {
                    finalSummary = summarizeLocally();
                }
                String compactedSummary = finalSummary;
                main.post(() -> {
                    setBusy(false);
                    applyConversationSummary(compactedSummary);
                    appendStatus("Conversation compacted and saved.");
                });
            } catch (Exception ex) {
                String fallback = summarizeLocally();
                main.post(() -> {
                    setBusy(false);
                    applyConversationSummary(fallback);
                    appendStatus("Conversation compacted locally after Gemini failed: " + shortMessage(ex.getMessage()));
                });
            }
        });
    }

    private void recordTranscriptTurn(String role, String text) {
        if (role == null || text == null || text.trim().isEmpty() || ChatSystemShape.isStartupGreeting(text)) {
            return;
        }
        LocalLog.info("chat", role + ": " + text);
        persistChatHistory();
    }

    private void persistChatHistory() {
        SharedPreferences.Editor editor = getSharedPreferences(PREFS, MODE_PRIVATE).edit();
        editor.putString(KEY_CHAT_TRANSCRIPT, recentTranscriptSnapshot());
        if (conversationSummary == null || conversationSummary.trim().isEmpty()) {
            editor.remove(KEY_CHAT_SUMMARY);
        } else {
            editor.putString(KEY_CHAT_SUMMARY, conversationSummary.trim());
        }
        editor.apply();
    }

    private boolean restoreConversationHistory() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        conversationSummary = clean(prefs.getString(KEY_CHAT_SUMMARY, ""));
        String transcript = clean(prefs.getString(KEY_CHAT_TRANSCRIPT, ""));
        chatTurns.clear();
        if (chatLogContainer != null) {
            chatLogContainer.removeAllViews();
        }
        boolean restored = false;
        if (!conversationSummary.isEmpty()) {
            appendChatBubble("Summary", conversationSummary, false, true);
            restored = true;
        }
        if (!transcript.isEmpty()) {
            String[] lines = transcript.split("\n");
            boolean cleaned = false;
            for (String line : lines) {
                ChatTurn turn = chatTurnFromLine(line);
                if (turn == null) {
                    continue;
                }
                if (ChatSystemShape.isStartupGreeting(turn.text)) {
                    cleaned = true;
                    continue;
                }
                chatTurns.add(turn);
                appendChatBubble("assistant".equals(turn.role) ? "Home Center" : "You", turn.text, "user".equals(turn.role), false);
                restored = true;
            }
            if (cleaned) {
                persistChatHistory();
            }
        }
        if (restored) {
            appendStatus("Restored previous chat history.");
        }
        return restored;
    }

    private ChatTurn chatTurnFromLine(String line) {
        if (line == null) {
            return null;
        }
        String cleanLine = line.trim();
        if (cleanLine.startsWith("User: ")) {
            return new ChatTurn("user", cleanLine.substring(6).trim());
        }
        if (cleanLine.startsWith("Assistant: ")) {
            return new ChatTurn("assistant", cleanLine.substring(11).trim());
        }
        return null;
    }

    private void applyConversationSummary(String summary) {
        conversationSummary = clean(summary);
        chatTurns.clear();
        if (chatLogContainer != null) {
            chatLogContainer.removeAllViews();
        }
        if (!conversationSummary.isEmpty()) {
            appendChatBubble("Summary", conversationSummary, false, true);
            LocalLog.info("chat_compaction", conversationSummary);
        }
        persistChatHistory();
        showAssistantMessage("Conversation compacted and saved.");
    }

    private String buildCompactionPrompt() {
        StringBuilder prompt = new StringBuilder();
        prompt.append("Summarize this Home Center conversation for later restoration and debugging.\n");
        prompt.append("Capture the user's goals, ingredients, tools, constraints, meal ideas, and next best actions.\n");
        prompt.append("Return 4 to 8 terse bullet points. No filler. No preamble.\n");
        if (!conversationSummary.isEmpty()) {
            prompt.append("Existing summary to preserve:\n");
            prompt.append(conversationSummary).append('\n');
        }
        prompt.append("Conversation:\n");
        prompt.append(recentTranscriptSnapshot()).append('\n');
        return prompt.toString();
    }

    private String summarizeLocally() {
        String transcript = recentTranscriptSnapshot();
        if (transcript.isEmpty() && conversationSummary.isEmpty()) {
            return "";
        }
        StringBuilder summary = new StringBuilder();
        if (!conversationSummary.isEmpty()) {
            summary.append("- Existing summary: ").append(conversationSummary).append('\n');
        }
        if (!transcript.isEmpty()) {
            String[] lines = transcript.split("\\n");
            int count = 0;
            for (int i = Math.max(0, lines.length - 4); i < lines.length; i++) {
                String line = lines[i].trim();
                if (line.isEmpty()) {
                    continue;
                }
                summary.append("- ").append(line).append('\n');
                count++;
            }
            if (count == 0) {
                summary.append("- Recent conversation available in chat history.");
            }
        }
        return summary.toString().trim();
    }

    private String recentTranscriptSnapshot() {
        if (chatTurns.isEmpty()) {
            return "";
        }
        StringBuilder snapshot = new StringBuilder();
        int start = Math.max(0, chatTurns.size() - MAX_RECORDED_TURNS);
        for (int i = start; i < chatTurns.size(); i++) {
            ChatTurn turn = chatTurns.get(i);
            snapshot.append("assistant".equals(turn.role) ? "Assistant: " : "User: ");
            snapshot.append(turn.text).append('\n');
        }
        String text = snapshot.toString().trim();
        if (text.length() > 4000) {
            return text.substring(text.length() - 4000);
        }
        return text;
    }

    private String clean(String value) {
        return value == null ? "" : value.trim();
    }

    private static final class WalmartHandoffStatus {
        boolean packageVisible = false;
        boolean launchIntentAvailable = false;
        boolean directUrlResolvable = false;
        boolean unscopedUrlResolvable = false;
        String packageError = "";
        String launchError = "";
        String directError = "";
        String unscopedError = "";

        boolean canReachWalmartApp() {
            return packageVisible || launchIntentAvailable || directUrlResolvable;
        }

        String label() {
            if (canReachWalmartApp()) {
                return "Walmart app detected.";
            }
            if (unscopedUrlResolvable) {
                return "Walmart app not detected; links may open in browser.";
            }
            return "Walmart app/link route not detected.";
        }

        String summary() {
            return "packageVisible=" + packageVisible
                    + " launchIntent=" + launchIntentAvailable
                    + " directUrl=" + directUrlResolvable
                    + " unscopedUrl=" + unscopedUrlResolvable
                    + maybe(" packageError=", packageError)
                    + maybe(" launchError=", launchError)
                    + maybe(" directError=", directError)
                    + maybe(" unscopedError=", unscopedError);
        }

        private static String maybe(String label, String value) {
            return value == null || value.isEmpty() ? "" : label + value.replace(' ', '_');
        }
    }

    private static final class CartReviewItem {
        String key = "";
        String raw = "";
        String item = "";
        String quantityText = "1";
        String status = "needs_choice";
        String reason = "";
        String walmartSearchUrl = "";
        String walmartBuyAgainUrl = "";
        String sku = "";
        String productUrl = "";
        String productName = "";
        String brand = "";
        String size = "";
        String quantity = "";
        String source = "buy_again";
        String confidence = "confirmed";

        static CartReviewItem fromJson(JSONObject obj) {
            CartReviewItem item = new CartReviewItem();
            item.key = opt(obj, "key");
            item.raw = opt(obj, "raw");
            item.item = opt(obj, "item");
            item.quantityText = opt(obj, "quantity_text");
            if (item.quantityText.isEmpty()) {
                item.quantityText = opt(obj, "quantityText");
            }
            item.quantity = opt(obj, "quantity");
            JSONObject verified = obj.optJSONObject("verified");
            if (verified != null) {
                item.brand = opt(verified, "brand");
                item.size = opt(verified, "size");
                String verifiedQuantity = opt(verified, "quantity");
                if (!verifiedQuantity.isEmpty()) {
                    item.quantity = verifiedQuantity;
                    item.quantityText = verifiedQuantity;
                }
            }
            if (item.quantity.isEmpty() && !item.quantityText.equals("?") && !item.quantityText.equals("many")) {
                item.quantity = item.quantityText;
            }
            item.status = opt(obj, "status");
            item.reason = opt(obj, "reason");
            item.walmartSearchUrl = opt(obj, "walmart_search_url");
            if (item.walmartSearchUrl.isEmpty()) {
                item.walmartSearchUrl = opt(obj, "walmartSearchUrl");
            }
            item.walmartBuyAgainUrl = opt(obj, "walmart_buy_again_url");
            if (item.walmartBuyAgainUrl.isEmpty()) {
                item.walmartBuyAgainUrl = opt(obj, "walmartBuyAgainUrl");
            }
            item.sku = opt(obj, "sku");
            item.productUrl = opt(obj, "productUrl");
            item.productName = opt(obj, "productName");
            if (item.brand.isEmpty()) {
                item.brand = opt(obj, "brand");
            }
            if (item.size.isEmpty()) {
                item.size = opt(obj, "size");
            }
            item.source = opt(obj, "source");
            item.confidence = opt(obj, "confidence");
            JSONArray candidates = obj.optJSONArray("candidates");
            if (candidates != null && candidates.length() > 0) {
                JSONObject candidate = candidates.optJSONObject(0);
                if (candidate != null) {
                    item.sku = opt(candidate, "sku");
                    item.productUrl = opt(candidate, "productUrl");
                    item.productName = opt(candidate, "productName");
                    if (item.brand.isEmpty()) {
                        item.brand = opt(candidate, "brand");
                    }
                    if (item.size.isEmpty()) {
                        item.size = opt(candidate, "size");
                    }
                    String candidateQuantity = opt(candidate, "quantity");
                    if (!candidateQuantity.isEmpty()) {
                        item.quantity = candidateQuantity;
                    }
                    item.source = opt(candidate, "source");
                    item.confidence = opt(candidate, "confidence");
                }
            }
            if (item.status.isEmpty()) {
                item.status = "needs_choice";
            }
            if (item.source.isEmpty()) {
                item.source = "buy_again";
            }
            if (item.confidence.isEmpty()) {
                item.confidence = "confirmed";
            }
            return item;
        }

        String quantityValue() {
            if (quantity == null || quantity.trim().isEmpty() || quantity.equals("null")) {
                return "?".equals(quantityText) || "many".equals(quantityText) ? "" : quantityText;
            }
            return quantity;
        }

        boolean isVerified() {
            return "verified".equals(status) && !brand.isEmpty() && !size.isEmpty() && !quantityValue().isEmpty();
        }

        String verifiedProductUrl() {
            if (!productUrl.isEmpty()) {
                return productUrl;
            }
            if (!sku.isEmpty()) {
                return "https://www.walmart.com/ip/" + sku;
            }
            return "";
        }

        String verifiedSummary() {
            if (!isVerified()) {
                return "";
            }
            return "\nVerified: " + productName + " brand=" + brand + " size=" + size + " qty=" + quantityValue();
        }

        JSONObject toJson() {
            JSONObject obj = new JSONObject();
            try {
                obj.put("key", key);
                obj.put("raw", raw);
                obj.put("item", item);
                obj.put("quantity", quantityValue());
                obj.put("quantity_text", quantityText);
                obj.put("status", status);
                obj.put("reason", reason);
                obj.put("walmart_search_url", walmartSearchUrl);
                obj.put("walmart_buy_again_url", walmartBuyAgainUrl);
                obj.put("sku", sku);
                obj.put("productUrl", productUrl);
                obj.put("productName", productName);
                obj.put("brand", brand);
                obj.put("size", size);
                obj.put("source", source);
                obj.put("confidence", confidence);
                JSONObject verified = new JSONObject();
                verified.put("brand", brand);
                verified.put("size", size);
                verified.put("quantity", quantityValue());
                obj.put("verified", verified);
            } catch (Exception ignored) {
            }
            return obj;
        }

        private static String opt(JSONObject obj, String key) {
            Object value = obj.opt(key);
            if (value == null || value == JSONObject.NULL) {
                return "";
            }
            return String.valueOf(value).trim();
        }
    }

    private static final class GeminiConfig {
        final String apiKey;
        final String model;
        final String source;

        GeminiConfig(String apiKey, String model, String source) {
            this.apiKey = apiKey == null ? "" : apiKey.trim();
            this.model = model == null || model.trim().isEmpty() ? "gemini-2.0-flash" : model.trim();
            this.source = source == null ? "missing" : source;
        }
    }

    private String timeStamp() {
        return new SimpleDateFormat("h:mm a", Locale.US).format(new Date());
    }

    private static final class ChatTurn {
        final String role;
        final String text;

        ChatTurn(String role, String text) {
            this.role = role;
            this.text = text;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CART_REVIEW_IMPORT) {
            if (resultCode == RESULT_OK) {
                importCartReview(data);
            }
            return;
        }
        if (requestCode == REQUEST_GOOGLE_SIGN_IN) {
            try {
                GoogleSignInAccount account = GoogleSignIn.getSignedInAccountFromIntent(data).getResult(ApiException.class);
                signInFirebaseWithGoogle(account, true);
            } catch (Exception ex) {
                refreshAuthStatus();
                showAssistantMessage("Google sign in failed: " + shortMessage(ex.getMessage()));
            }
            return;
        }
        if (requestCode == REQUEST_GOOGLE_TOOL_PERMISSIONS) {
            refreshAuthStatus();
            GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
            if (!hasAllGoogleToolScopes(account)) {
                showAssistantMessage("Google permission approval did not finish. Please tap Sign in with Google and approve Drive, Docs, Sheets, Gmail, Calendar, and Contacts.");
                return;
            }
            exchangeGoogleServerAuthCode(account);
            String pending = pendingAgentTurnAfterGoogleReconnect;
            pendingAgentTurnAfterGoogleReconnect = "";
            if (pending != null && !pending.trim().isEmpty()) {
                appendStatus("Google tools approved. Continuing the pending request.");
                sendAgentTurn(pending);
            } else {
                speak("Google tools approved.");
            }
            return;
        }
        if (requestCode == REQUEST_DRIVE_AUTH) {
            if (resultCode == RESULT_OK) {
                checkGoogleDriveDiagnostic();
            } else {
                showAssistantMessage("Google Drive permission was not approved.");
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
            showAssistantMessage("Microphone permission is required for voice commands.");
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
        LocalLog.info("speech", "recognizer_error: " + error);
        setStatus("I did not catch that. Try again from the keyboard microphone.");
    }

    @Override
    public void onResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) {
            LocalLog.info("speech", "recognizer_empty_result");
            setStatus("I did not hear a command. Try again from the keyboard microphone.");
            return;
        }
        handlePhrase(matches.get(0));
    }

    @Override
    protected void onDestroy() {
        if (recognizer != null) {
            recognizer.destroy();
        }
        updateThinkingHaptics(false);
        stopCartesiaPlayback("activity_destroy");
        abandonSpeechFocus();
        if (deviceTextToSpeech != null) {
            deviceTextToSpeech.stop();
            deviceTextToSpeech.shutdown();
            deviceTextToSpeech = null;
            deviceTextToSpeechReady = false;
        }
        if (firebaseAuth != null && authStateListener != null) {
            firebaseAuth.removeAuthStateListener(authStateListener);
        }
        executor.shutdownNow();
        super.onDestroy();
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS && deviceTextToSpeech != null) {
            int language = deviceTextToSpeech.setLanguage(Locale.US);
            deviceTextToSpeechReady = language != TextToSpeech.LANG_MISSING_DATA && language != TextToSpeech.LANG_NOT_SUPPORTED;
            LocalLog.info("speech", "device_tts_ready=" + deviceTextToSpeechReady + " languageResult=" + language);
        } else {
            deviceTextToSpeechReady = false;
            LocalLog.warn("speech", "device_tts_init_failed status=" + status);
        }
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
