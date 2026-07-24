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
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.Cursor;
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
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.text.InputType;
import android.text.TextUtils;
import android.text.method.PasswordTransformationMethod;
import android.text.method.SingleLineTransformationMethod;
import android.view.KeyEvent;
import android.view.Window;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewConfiguration;
import android.view.inputmethod.EditorInfo;
import android.view.accessibility.AccessibilityManager;
import android.util.Base64;
import android.widget.Button;
import android.widget.EditText;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.SeekBar;
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
import java.io.FileInputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MainActivity extends Activity implements RecognitionListener, TextToSpeech.OnInitListener {
    private static final int REQUEST_RECORD_AUDIO = 1001;
    private static final int REQUEST_GOOGLE_SIGN_IN = 2001;
    private static final int REQUEST_GOOGLE_TOOL_PERMISSIONS = 2002;
    private static final int REQUEST_CART_REVIEW_IMPORT = 3001;
    private static final int REQUEST_DRIVE_AUTH = 4001;
    private static final int REQUEST_FILE_ATTACH = 5001;
    private static final long DRIVE_HANDOFF_REFRESH_DELAY_MS = 900L;
    private static final int MAX_AGENT_TOOL_STEPS = 8;
    private static final int MAX_ATTACHMENT_PREVIEW_CHARS = 20000;
    private static final int MAX_IMAGE_ATTACHMENT_BYTES = 8 * 1024 * 1024;
    private static final int DOC_READER_FIRST_CHUNK_CHARS = 520;
    private static final int DOC_READER_TARGET_CHARS = 2200;
    private static final int DOC_READER_MIN_CHARS = 900;
    private static final int DOC_READER_PREVIEW_CHARS = 700;
    private static final int DOC_READER_AUTOPLAY_MAX_CHUNKS = 3;
    private static final int DOC_READER_PLAYBACK_BUFFER_CHUNKS = 3;
    private static final long DOC_READER_PLAYBACK_RETRY_DELAY_MS = 2500L;
    private static final long DOC_READER_FALSE_PLAYING_RECHECK_MS = 350L;
    private static final long DOC_READER_FALSE_PLAYING_COOLDOWN_MS = 1500L;
    private static final long DRIVE_BROWSER_POLL_INTERVAL_MS = 30000L;
    private static final String WALMART_PACKAGE = "com.walmart.android";
    private static final String TERMUX_PACKAGE = "com.termux";
    private static final String SHIZUKU_PACKAGE = "moe.shizuku.privileged.api";
    private static final String TERMUX_FDROID_URL = "https://f-droid.org/packages/com.termux/";
    private static final String TERMUX_GITHUB_RELEASES_URL = "https://github.com/termux/termux-app/releases";
    private static final String SHIZUKU_DOWNLOAD_URL = "https://shizuku.rikka.app/download/";
    private static final String SHIZUKU_SETUP_URL = "https://shizuku.rikka.app/guide/setup/";
    private static final String RISH_SETUP_URL = "https://github.com/RikkaApps/Shizuku-API/tree/master/rish";
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
    private static final String KEY_CONVERSATIONS_JSON = "conversations_json";
    private static final String KEY_ACTIVE_CONVERSATION_ID = "active_conversation_id";
    private static final String KEY_NARRATION_MUTED = "narration_muted";
    private static final String KEY_LEGACY_CHAT_VISIBLE = "legacy_chat_visible";
    private static final String KEY_DRIVE_SPEECH_PROVIDER = "drive_speech_provider";
    private static final String KEY_DRIVE_SPEECH_MODEL = "drive_speech_model";
    private static final String KEY_DRIVE_SPEECH_NARRATOR_VOICE_NAME = "drive_speech_narrator_voice_name";
    private static final String KEY_DRIVE_SPEECH_NARRATOR_VOICE_ID = "drive_speech_narrator_voice_id";
    private static final String KEY_DRIVE_SPEECH_DIALOGUE_VOICE_NAME = "drive_speech_dialogue_voice_name";
    private static final String KEY_DRIVE_SPEECH_DIALOGUE_VOICE_ID = "drive_speech_dialogue_voice_id";
    private static final String KEY_DRIVE_SPEECH_NOTES_VOICE_NAME = "drive_speech_notes_voice_name";
    private static final String KEY_DRIVE_SPEECH_NOTES_VOICE_ID = "drive_speech_notes_voice_id";
    private static final String KEY_DRIVE_CHARACTER_REGISTRY_JSON = "drive_character_registry_json";
    private static final String KEY_DRIVE_CHARACTER_REGISTRY_DOC_ID = "drive_character_registry_doc_id";
    private static final String KEY_DRIVE_CHARACTER_REGISTRY_LOADED_AT = "drive_character_registry_loaded_at";
    private static final String KEY_DRIVE_VOICE_CATALOG_JSON = "drive_voice_catalog_json";
    private static final String DRIVE_CHARACTER_REGISTRY_TITLE = "Home Drive Character Voice Orientation Registry";
    private static final String DRIVE_VOICE_SPLIT_FOLDER_TITLE = "Home Center Voice Split Rendering";
    private static final String DRIVE_VOICE_SPLIT_README_TITLE = "Voice Split Rendering - Folder Contract";
    private static final String[] DRIVE_VOICE_SPLIT_SUBFOLDERS = new String[] {
            "01 Intake Documents",
            "02 Split Plans",
            "03 Rendered Chunks",
            "04 Final Mixes",
            "05 Voice Registry Snapshots",
            "99 Failed Runs"
    };
    private static final String DEFAULT_DRIVE_SPEECH_PROVIDER = "cartesia";
    private static final String DEFAULT_DRIVE_SPEECH_MODEL = "sonic-3.5";
    private static final String DEFAULT_DRIVE_NARRATOR_VOICE = "Katie - Friendly Fixer";
    private static final String DEFAULT_DRIVE_NARRATOR_VOICE_ID = "f786b574-daa5-4673-aa0c-cbe3e8534c02";
    private static final String LEGACY_DRIVE_NARRATOR_VOICE = "Skylar - Friendly Guide";
    private static final String LEGACY_DRIVE_NARRATOR_VOICE_ID = "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4";
    private static final int DRIVE_VOICE_RESOLVER_VERSION = 5;
    private static final String[] DRIVE_SPLIT_FALLBACK_DIALOGUE_VOICES = new String[] {
            "Clive - Measured Expert",
            "Daniel - Modern Assistant",
            "Ronald - Thinker"
    };
    private static final String EXTRA_SMOKE_PROMPT = "home_center_smoke_prompt";
    private static final Pattern CHAT_URL_PATTERN = Pattern.compile("https?://\\S+|www\\.\\S+");
    private static final String EXTRA_SMOKE_NEW_CONVERSATION = "home_center_smoke_new_conversation";
    private static final String EXTRA_SMOKE_MUTE_SPEECH = "home_center_smoke_mute_speech";
    private static final String EXTRA_TERMUX_PAIRING_ID = "home_center_termux_pairing_id";
    private static final String EXTRA_TERMUX_PAIRING_CODE = "home_center_termux_pairing_code";
    private static final String EXTRA_TERMUX_PAIRING_AUTO = "home_center_termux_pairing_auto";
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
    private HostedSpeechClient hostedSpeechClient;
    private GoogleDocAudioLibrary googleDocAudioLibrary;
    private AudioManager audioManager;
    private AudioFocusRequest speechFocusRequest;
    private MediaSession speechMediaSession;
    private boolean driveNarrationForegroundRunning = false;
    private String driveNarrationForegroundTitle = "";
    private boolean speechFocusHeld = false;
    private String activeSpeechUtteranceId = "";
    private volatile long speechSequence = 0L;
    private volatile boolean speechPlaying = false;
    private volatile AudioTrack activeHostedSpeechTrack;
    private volatile long smokeSpeechMutedUntilMillis = 0L;
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
    private Button attachFileButton;
    private Button stopSpeechButton;
    private Button narrationMuteButton;
    private Button conversationDrawerButton;
    private Button legacyChatToggleButton;
    private Button googleToolsButton;
    private Button termuxPairButton;
    private TextView conversationTitleView;
    private TextView workingIndicatorView;
    private LinearLayout bottomPanel;
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
    private LinearLayout loginShellPanel;
    private TextView loginShellTitleView;
    private TextView loginShellDetailView;
    private TextView loginShellEventView;
    private TextView driveBrowserPathView;
    private TextView driveBrowserStatusView;
    private LinearLayout driveReaderPlayerPanel;
    private TextView driveReaderPlayerPlayheadView;
    private SeekBar driveReaderPlayerSeekBar;
    private TextView driveReaderPlayerTimeView;
    private boolean driveReaderUserSeeking;
    private Button driveReaderPlayerPlayPauseButton;
    private Button driveReaderPlayerDownloadButton;
    private Button driveReaderPlayerRerenderButton;
    private Button driveReaderPlayerStopButton;
    private Button driveReaderPlayerCloseButton;
    private LinearLayout driveBrowserList;
    private Button driveRecentButton;
    private Button driveFoldersButton;
    private Button driveDocsButton;
    private Button driveParentButton;
    private Button driveSpeechSettingsButton;
    private LinearLayout composeRow;
    private GeminiClient geminiClient;
    private OpenAiAgentClient openAiAgentClient;
    private GoogleDriveClient googleDriveClient;
    private GoogleSheetsClient googleSheetsClient;
    private GoogleGmailClient googleGmailClient;
    private GoogleCalendarClient googleCalendarClient;
    private GoogleContactsClient googleContactsClient;
    private LocalKnowledgeClient localKnowledgeClient;

    private boolean tickTickTokenVisible = false;
    private boolean narrationMuted = false;
    private boolean legacyChatVisible = false;
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
    private String activeConversationId = "";
    private String activeConversationTitle = "";
    private JSONArray activeConversationTags = new JSONArray();
    private String pendingAgentTurnAfterGoogleReconnect = "";
    private String pendingTermuxPairingId = "";
    private String pendingTermuxPairingCode = "";
    private boolean pendingTermuxPairingApprovalRunning = false;
    private volatile JSONObject pendingToolConfirmation;
    private final Object workingMemoryLock = new Object();
    private final JSONObject workingMemory = new JSONObject();
    private final Object attachmentLock = new Object();
    private final JSONArray attachedFiles = new JSONArray();
    private final JSONArray activeFileIds = new JSONArray();
    private int nextSessionFileNumber = 1;
    private final Object toolTraceLock = new Object();
    private final JSONArray recentToolTrace = new JSONArray();
    private String lastVisibleStatus = "";
    private String lastDriveDocumentId = "";
    private String lastDriveDocumentName = "";
    private String activeDriveFolderId = "";
    private String activeDriveFolderName = "Narratable Docs";
    private String driveSearchQuery = "";
    private String driveSortMode = "modified_desc";
    private String driveFilterMode = "docs_all";
    private String currentDriveBrowserMode = "docs";
    private String currentDriveBrowserFolderId = "";
    private String currentDriveBrowserTitle = "Narratable Docs";
    private boolean driveBrowserRequestInFlight = false;
    private boolean pendingManualDriveRefresh = false;
    private boolean driveBrowserHasRenderedList = false;
    private long lastDriveHandoffAtMs = 0L;
    private boolean driveBrowserPollActive = false;
    private final List<DriveFolderCrumb> driveFolderStack = new ArrayList<>();
    private DocumentReaderState activeDocumentReader;
    private String driveSpeechProvider = DEFAULT_DRIVE_SPEECH_PROVIDER;
    private String driveSpeechModelId = DEFAULT_DRIVE_SPEECH_MODEL;
    private String driveNarratorVoiceName = DEFAULT_DRIVE_NARRATOR_VOICE;
    private String driveNarratorVoiceId = "";
    private String driveDialogueVoiceName = DEFAULT_DRIVE_NARRATOR_VOICE;
    private String driveDialogueVoiceId = "";
    private String driveNotesVoiceName = DEFAULT_DRIVE_NARRATOR_VOICE;
    private String driveNotesVoiceId = "";
    private CharacterVoiceRegistry driveCharacterRegistry = CharacterVoiceRegistry.defaults();
    private List<VoiceCatalogEntry> driveVoiceCatalog = new ArrayList<>();
    private String driveCharacterRegistryDocId = "";
    private long driveCharacterRegistryLoadedAt = 0L;
    private String startupGreeting = "Home Center is ready. Try pantry inventory, what can I make, recipe brainstorm, or rescue meal.";
    private final List<CartReviewItem> cartReviewItems = new ArrayList<>();
    private int cartReviewIndex = -1;

    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ExecutorService documentAudioExecutor = Executors.newSingleThreadExecutor();
    private final ExecutorService documentRenderExecutor = Executors.newSingleThreadExecutor();
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
    private final Runnable driveBrowserPollRunnable = new Runnable() {
        @Override
        public void run() {
            refreshCurrentDriveBrowserFromPoll();
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        super.onCreate(savedInstanceState);
        LocalLog.init(this);
        getWindow().setStatusBarColor(COLOR_BACKGROUND);
        getWindow().setNavigationBarColor(Color.BLACK);
        LocalLog.info("app", "start versionName=" + BuildConfig.VERSION_NAME + " versionCode=" + BuildConfig.VERSION_CODE);
        initFirebase();
        audioManager = (AudioManager) getSystemService(AUDIO_SERVICE);
        initSpeechMediaSession();
        hostedSpeechClient = new HostedSpeechClient(BuildConfig.AGENT_GATEWAY_BASE_URL);
        googleDocAudioLibrary = new GoogleDocAudioLibrary(this);
        documentAudioExecutor.execute(this::reconcileCachedRenderedDocuments);
        deviceTextToSpeech = new TextToSpeech(this, this);
        googleDriveClient = new GoogleDriveClient(this);
        googleSheetsClient = new GoogleSheetsClient(this);
        googleGmailClient = new GoogleGmailClient(this);
        googleCalendarClient = new GoogleCalendarClient(this);
        googleContactsClient = new GoogleContactsClient(this);
        localKnowledgeClient = new LocalKnowledgeClient(this);
        refreshGeminiClient();
        loadDriveSpeechSettings();
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
        handleTermuxPairingIntent(getIntent());
    }

    private void initSpeechMediaSession() {
        speechMediaSession = new MediaSession(this, "Home Center Narration");
        speechMediaSession.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
        speechMediaSession.setCallback(new MediaSession.Callback() {
            @Override
            public void onPlay() {
                main.post(() -> handleSpeechMediaPlay());
            }

            @Override
            public void onPause() {
                main.post(() -> handleSpeechMediaPause());
            }

            @Override
            public void onStop() {
                main.post(() -> handleSpeechMediaStop());
            }

            @Override
            public void onSkipToNext() {
                main.post(() -> handleSpeechMediaSkip(1));
            }

            @Override
            public void onSkipToPrevious() {
                main.post(() -> handleSpeechMediaSkip(-1));
            }

            @Override
            public boolean onMediaButtonEvent(Intent mediaButtonIntent) {
                KeyEvent event = mediaButtonIntent == null ? null : mediaButtonIntent.getParcelableExtra(Intent.EXTRA_KEY_EVENT);
                if (event == null || event.getAction() != KeyEvent.ACTION_UP) {
                    return true;
                }
                int keyCode = event.getKeyCode();
                if (keyCode == KeyEvent.KEYCODE_MEDIA_PLAY || keyCode == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE || keyCode == KeyEvent.KEYCODE_HEADSETHOOK) {
                    main.post(() -> handleSpeechMediaPlayPause());
                    return true;
                }
                if (keyCode == KeyEvent.KEYCODE_MEDIA_PAUSE) {
                    main.post(() -> handleSpeechMediaPause());
                    return true;
                }
                if (keyCode == KeyEvent.KEYCODE_MEDIA_NEXT) {
                    main.post(() -> handleSpeechMediaSkip(1));
                    return true;
                }
                if (keyCode == KeyEvent.KEYCODE_MEDIA_PREVIOUS) {
                    main.post(() -> handleSpeechMediaSkip(-1));
                    return true;
                }
                return super.onMediaButtonEvent(mediaButtonIntent);
            }
        });
        updateSpeechMediaSession(false);
    }


    private void handleSpeechMediaPlayPause() {
        if (activeDocumentReader != null) {
            if (activeDocumentReader.paused || !activeDocumentReader.playbackRequested) {
                resumeDocumentReader();
            } else if (!isDocumentAudioPlaybackLive(activeDocumentReader)) {
                reconcileDocumentPlaybackIfNeeded(activeDocumentReader, "media_button_false_playing");
            } else {
                pauseDocumentReader();
            }
            refreshDriveReaderPlayer();
            return;
        }
        if (speechPlaying) {
            stopSpeechPlayback();
        } else {
            updateSpeechMediaSession(false);
        }
    }

    private void handleSpeechMediaPlay() {
        if (activeDocumentReader != null) {
            resumeDocumentReader();
            refreshDriveReaderPlayer();
            return;
        }
        updateSpeechMediaSession(speechPlaying);
    }

    private void handleSpeechMediaPause() {
        if (activeDocumentReader != null && activeDocumentReader.playbackRequested && !activeDocumentReader.paused) {
            pauseDocumentReader();
            refreshDriveReaderPlayer();
            return;
        }
        stopSpeechPlayback();
    }

    private void handleSpeechMediaStop() {
        if (activeDocumentReader != null) {
            stopDocumentReader("stopped");
            return;
        }
        stopSpeechPlayback();
    }

    private void handleSpeechMediaSkip(int delta) {
        if (activeDocumentReader != null) {
            moveDocumentReader(delta);
            return;
        }
        updateSpeechMediaSession(speechPlaying);
    }

    @Override
    protected void onResume() {
        super.onResume();
        scheduleDriveBrowserPoll();
        if (lastDriveHandoffAtMs > 0L && SystemClock.elapsedRealtime() - lastDriveHandoffAtMs > 400L) {
            scheduleDriveRefreshAfterHandoff("resume_after_browser_handoff");
        }
    }

    @Override
    protected void onPause() {
        stopDriveBrowserPolling();
        super.onPause();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        runInstalledSmokePromptIfRequested(intent);
        handleTermuxPairingIntent(intent);
    }

    private void handleTermuxPairingIntent(Intent intent) {
        if (intent == null || !intent.getBooleanExtra(EXTRA_TERMUX_PAIRING_AUTO, false)) {
            return;
        }
        String pairingId = intent.getStringExtra(EXTRA_TERMUX_PAIRING_ID);
        String code = intent.getStringExtra(EXTRA_TERMUX_PAIRING_CODE);
        if (pairingId == null || pairingId.trim().isEmpty() || code == null || code.trim().isEmpty()) {
            return;
        }
        pendingTermuxPairingId = pairingId.trim();
        pendingTermuxPairingCode = code.trim();
        LocalLog.info("termux_pairing", "shizuku_intent_received pairingId=" + shortMessage(pendingTermuxPairingId));
        main.postDelayed(() -> continuePendingTermuxPairing("shizuku_intent"), 350L);
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
        boolean newConversation = intent.getBooleanExtra(EXTRA_SMOKE_NEW_CONVERSATION, false);
        boolean muteSpeech = intent.getBooleanExtra(EXTRA_SMOKE_MUTE_SPEECH, true);
        if (muteSpeech) {
            smokeSpeechMutedUntilMillis = SystemClock.elapsedRealtime() + 10L * 60L * 1000L;
        }
        LocalLog.info("installed_smoke", "prompt_requested: " + shortMessage(prompt) + " newConversation=" + newConversation + " muteSpeech=" + muteSpeech);
        if (newConversation) {
            createAndSwitchConversation("Smoke: " + shortMessage(prompt));
            clearAgentRuntimeStateForSmoke();
        }
        main.postDelayed(() -> {
            if (messageEdit == null) {
                LocalLog.warn("installed_smoke", "message composer unavailable");
                return;
            }
            messageEdit.setText(prompt.trim());
            submitTypedMessage();
        }, 1200L);
    }

    private void clearAgentRuntimeStateForSmoke() {
        pendingToolConfirmation = null;
        synchronized (workingMemoryLock) {
            JSONArray names = workingMemory.names();
            if (names != null) {
                for (int i = names.length() - 1; i >= 0; i--) {
                    workingMemory.remove(names.optString(i));
                }
            }
        }
        synchronized (toolTraceLock) {
            while (recentToolTrace.length() > 0) {
                recentToolTrace.remove(0);
            }
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
                    scheduleDriveRefreshAfterHandoff("google_sign_in_complete");
                    if (hasPendingTermuxPairing()) {
                        appendStatus("Google connected. Approving Termux Codex through Shizuku.");
                        continuePendingTermuxPairing("google_sign_in_complete");
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
        narrationMuted = prefs.getBoolean(KEY_NARRATION_MUTED, false);
        legacyChatVisible = false;
        prefs.edit().putBoolean(KEY_LEGACY_CHAT_VISIBLE, false).apply();
        initializePortableCommandFields(prefs);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(8), dp(6), dp(8), dp(8));
        root.setBackgroundColor(COLOR_BACKGROUND);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        conversationDrawerButton = new Button(this);
        conversationDrawerButton.setText("☰");
        conversationDrawerButton.setAllCaps(false);
        conversationDrawerButton.setTextSize(18);
        conversationDrawerButton.setTextColor(COLOR_TEXT);
        conversationDrawerButton.setBackgroundColor(COLOR_CARD);
        conversationDrawerButton.setContentDescription("Open conversations");
        LinearLayout.LayoutParams drawerParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        drawerParams.setMargins(0, 0, dp(8), 0);
        header.addView(conversationDrawerButton, drawerParams);

        conversationTitleView = new TextView(this);
        conversationTitleView.setText("Narratable Docs");
        conversationTitleView.setTextSize(18);
        conversationTitleView.setTypeface(Typeface.DEFAULT_BOLD);
        conversationTitleView.setTextColor(COLOR_TEXT);
        conversationTitleView.setSingleLine(true);
        conversationTitleView.setGravity(Gravity.CENTER_VERTICAL);
        conversationTitleView.setPadding(dp(2), dp(6), dp(8), dp(6));
        header.addView(conversationTitleView, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        authStatusView = new TextView(this);
        authStatusView.setTextSize(14);
        authStatusView.setTypeface(Typeface.DEFAULT_BOLD);
        authStatusView.setTextColor(COLOR_ACCENT);
        authStatusView.setGravity(Gravity.CENTER_VERTICAL);
        authStatusView.setPadding(dp(10), dp(6), dp(10), dp(6));
        header.addView(authStatusView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

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
        menuButton.setContentDescription("Open Home Center tools");
        LinearLayout.LayoutParams menuParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        menuParams.setMargins(dp(8), 0, 0, 0);
        header.addView(menuButton, menuParams);

        narrationMuteButton = new Button(this);
        narrationMuteButton.setAllCaps(false);
        narrationMuteButton.setTextSize(13);
        narrationMuteButton.setTextColor(COLOR_TEXT);
        LinearLayout.LayoutParams muteParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        muteParams.setMargins(dp(8), 0, 0, 0);
        header.addView(narrationMuteButton, muteParams);
        updateNarrationMuteButton();
        root.addView(header, matchWrap());

        statusView = new TextView(this);
        statusView.setTextSize(13);
        statusView.setTextColor(COLOR_SECONDARY);
        statusView.setGravity(Gravity.CENTER_HORIZONTAL);
        statusView.setPadding(0, dp(2), 0, dp(6));
        root.addView(statusView, matchWrap());
        statusView.setVisibility(View.GONE);
        updateBackendStatus();

        loginShellPanel = new LinearLayout(this);
        loginShellPanel.setOrientation(LinearLayout.VERTICAL);
        loginShellPanel.setPadding(dp(18), dp(18), dp(18), dp(18));
        loginShellPanel.setBackground(makePanelBackground());
        LinearLayout.LayoutParams shellParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f);
        shellParams.setMargins(0, dp(12), 0, dp(10));
        loginShellPanel.setLayoutParams(shellParams);

        loginShellTitleView = new TextView(this);
        loginShellTitleView.setText("Narratable Docs");
        loginShellTitleView.setTextSize(1);
        loginShellTitleView.setTypeface(Typeface.DEFAULT_BOLD);
        loginShellTitleView.setTextColor(COLOR_TEXT);
        loginShellTitleView.setGravity(Gravity.CENTER_HORIZONTAL);
        loginShellTitleView.setPadding(0, 0, 0, 0);
        loginShellTitleView.setVisibility(View.GONE);
        loginShellPanel.addView(loginShellTitleView, matchWrap());

        loginShellDetailView = new TextView(this);
        loginShellDetailView.setTextSize(13);
        loginShellDetailView.setTextColor(COLOR_SECONDARY);
        loginShellDetailView.setGravity(Gravity.CENTER_HORIZONTAL);
        loginShellDetailView.setPadding(0, 0, 0, 0);
        loginShellDetailView.setVisibility(View.GONE);
        loginShellPanel.addView(loginShellDetailView, matchWrap());

        loginShellEventView = new TextView(this);
        loginShellEventView.setTextSize(12);
        loginShellEventView.setTextColor(COLOR_ACCENT);
        loginShellEventView.setGravity(Gravity.CENTER_HORIZONTAL);
        loginShellEventView.setPadding(dp(2), 0, dp(2), dp(4));
        loginShellEventView.setVisibility(View.GONE);
        loginShellPanel.addView(loginShellEventView, matchWrap());

        googleToolsButton = button("Refresh Drive", 14, "Connect Google Drive so the file reader can list and read cloud files");
        googleToolsButton.setTextColor(COLOR_BACKGROUND);
        googleToolsButton.setBackgroundColor(COLOR_ACCENT);
        LinearLayout.LayoutParams toolsParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(44));
        toolsParams.setMargins(0, dp(4), 0, dp(6));
        loginShellPanel.addView(googleToolsButton, toolsParams);
        googleToolsButton.setVisibility(View.GONE);

        termuxPairButton = button("Pair Termux Codex", 14, "Approve a Termux Codex pairing code for Home Center tools");
        termuxPairButton.setTextColor(COLOR_TEXT);
        termuxPairButton.setBackgroundColor(COLOR_CARD);
        LinearLayout.LayoutParams pairParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(52));
        pairParams.setMargins(0, 0, 0, dp(12));
        loginShellPanel.addView(termuxPairButton, pairParams);
        termuxPairButton.setVisibility(View.GONE);

        driveBrowserPathView = new TextView(this);
        driveBrowserPathView.setText("My Drive / Google Docs");
        driveBrowserPathView.setTextSize(15);
        driveBrowserPathView.setTypeface(Typeface.DEFAULT_BOLD);
        driveBrowserPathView.setTextColor(COLOR_ACCENT);
        driveBrowserPathView.setPadding(0, 0, 0, dp(4));
        loginShellPanel.addView(driveBrowserPathView, matchWrap());

        LinearLayout driveModeRow = new LinearLayout(this);
        driveModeRow.setOrientation(LinearLayout.HORIZONTAL);
        driveModeRow.setPadding(0, 0, 0, dp(4));
        driveRecentButton = button("Search", 13, "Search narratable Google Docs");
        driveFoldersButton = button("Sort", 13, "Sort narratable Google Docs");
        driveDocsButton = button("Filter", 13, "Filter narratable Google Docs");
        driveParentButton = button("Refresh", 13, "Refresh narratable Google Docs");
        driveSpeechSettingsButton = button("Speech", 13, "Choose Drive Narrate speech model and role voices");
        driveModeRow.addView(driveRecentButton, weightedHeight(dp(40)));
        driveModeRow.addView(driveFoldersButton, weightedHeight(dp(40)));
        driveModeRow.addView(driveDocsButton, weightedHeight(dp(40)));
        driveModeRow.addView(driveParentButton, weightedHeight(dp(40)));
        driveModeRow.addView(driveSpeechSettingsButton, weightedHeight(dp(40)));
        loginShellPanel.addView(driveModeRow, matchWrap());

        driveBrowserStatusView = new TextView(this);
        driveBrowserStatusView.setText("Google Docs only. Tap a card to narrate with " + driveVoiceSummary() + ".");
        driveBrowserStatusView.setTextSize(13);
        driveBrowserStatusView.setTextColor(COLOR_SECONDARY);
        driveBrowserStatusView.setPadding(0, 0, 0, dp(4));
        loginShellPanel.addView(driveBrowserStatusView, matchWrap());

        driveReaderPlayerPanel = new LinearLayout(this);
        driveReaderPlayerPanel.setOrientation(LinearLayout.VERTICAL);
        driveReaderPlayerPanel.setPadding(dp(10), dp(10), dp(10), dp(10));
        driveReaderPlayerPanel.setBackground(makeActionCardBackground());
        LinearLayout.LayoutParams playerParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        playerParams.setMargins(0, dp(4), 0, dp(8));

        driveReaderPlayerPlayPauseButton = button("PLAY", 24, "Play or pause this Google Doc narration");
        driveReaderPlayerPlayPauseButton.setTextColor(COLOR_BACKGROUND);
        driveReaderPlayerPlayPauseButton.setBackgroundColor(COLOR_PRIMARY);
        driveReaderPlayerPlayPauseButton.setTypeface(Typeface.DEFAULT_BOLD);
        driveReaderPlayerPanel.addView(driveReaderPlayerPlayPauseButton, matchHeight(dp(70)));

        driveReaderPlayerDownloadButton = button("RENDER", 24, "Render the full Google Doc audio artifact");
        driveReaderPlayerDownloadButton.setTextColor(COLOR_BACKGROUND);
        driveReaderPlayerDownloadButton.setBackgroundColor(COLOR_ACCENT);
        driveReaderPlayerDownloadButton.setTypeface(Typeface.DEFAULT_BOLD);
        driveReaderPlayerPanel.addView(driveReaderPlayerDownloadButton, matchHeight(dp(82)));

        driveReaderPlayerRerenderButton = button("RERENDER", 18, "Discard cached sections and rerender this Google Doc with current voices");
        driveReaderPlayerRerenderButton.setTextColor(COLOR_TEXT);
        driveReaderPlayerRerenderButton.setBackgroundColor(COLOR_CARD);
        driveReaderPlayerRerenderButton.setTypeface(Typeface.DEFAULT_BOLD);
        driveReaderPlayerPanel.addView(driveReaderPlayerRerenderButton, matchHeight(dp(52)));


        driveReaderPlayerStopButton = button("STOP", 18, "Stop the current narration or render");
        driveReaderPlayerStopButton.setTextColor(COLOR_TEXT);
        driveReaderPlayerStopButton.setBackgroundColor(COLOR_DANGER);
        driveReaderPlayerStopButton.setTypeface(Typeface.DEFAULT_BOLD);
        driveReaderPlayerPanel.addView(driveReaderPlayerStopButton, matchHeight(dp(46)));

        driveReaderPlayerCloseButton = button("CLOSE", 18, "Close this Google Doc reader view without deleting saved audio");
        driveReaderPlayerCloseButton.setTextColor(COLOR_TEXT);
        driveReaderPlayerCloseButton.setBackgroundColor(COLOR_CARD);
        driveReaderPlayerCloseButton.setTypeface(Typeface.DEFAULT_BOLD);
        driveReaderPlayerPanel.addView(driveReaderPlayerCloseButton, matchHeight(dp(46)));

        driveReaderPlayerSeekBar = new SeekBar(this);
        driveReaderPlayerSeekBar.setMax(1000);
        driveReaderPlayerPanel.addView(driveReaderPlayerSeekBar, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(48)));

        driveReaderPlayerTimeView = new TextView(this);
        driveReaderPlayerTimeView.setTextSize(12);
        driveReaderPlayerTimeView.setTextColor(COLOR_SECONDARY);
        driveReaderPlayerTimeView.setGravity(Gravity.CENTER_HORIZONTAL);
        driveReaderPlayerPanel.addView(driveReaderPlayerTimeView, matchWrap());

        driveReaderPlayerPlayheadView = new TextView(this);
        driveReaderPlayerPlayheadView.setTextSize(12);
        driveReaderPlayerPlayheadView.setTypeface(Typeface.DEFAULT_BOLD);
        driveReaderPlayerPlayheadView.setTextColor(COLOR_ACCENT);
        driveReaderPlayerPlayheadView.setGravity(Gravity.CENTER_HORIZONTAL);
        driveReaderPlayerPlayheadView.setPadding(0, dp(4), 0, 0);
        driveReaderPlayerPanel.addView(driveReaderPlayerPlayheadView, matchWrap());
        loginShellPanel.addView(driveReaderPlayerPanel, playerParams);

        ScrollView driveBrowserScroll = new ScrollView(this);
        driveBrowserScroll.setFillViewport(false);
        driveBrowserList = new LinearLayout(this);
        driveBrowserList.setOrientation(LinearLayout.VERTICAL);
        driveBrowserList.setPadding(0, 0, 0, dp(8));
        driveBrowserScroll.addView(driveBrowserList, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));
        loginShellPanel.addView(driveBrowserScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f));

        legacyChatToggleButton = button("Open chat", 12, "Open the secondary Home Center chat interface");
        loginShellPanel.addView(legacyChatToggleButton, matchHeight(dp(40)));
        root.addView(loginShellPanel);

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

        bottomPanel = new LinearLayout(this);
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

        composeRow = new LinearLayout(this);
        composeRow.setOrientation(LinearLayout.HORIZONTAL);
        composeRow.setGravity(Gravity.CENTER_VERTICAL);

        attachFileButton = new Button(this);
        attachFileButton.setText("📎");
        attachFileButton.setAllCaps(false);
        attachFileButton.setTextSize(18);
        attachFileButton.setTextColor(COLOR_TEXT);
        attachFileButton.setBackgroundColor(COLOR_CARD);
        attachFileButton.setContentDescription("Attach file");
        LinearLayout.LayoutParams attachParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        attachParams.setMargins(0, 0, dp(8), 0);
        attachFileButton.setLayoutParams(attachParams);
        composeRow.addView(attachFileButton);

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

        attachFileButton.setOnClickListener(v -> startFileAttach());
        conversationDrawerButton.setOnClickListener(v -> showConversationPanel());
        submitButton.setOnClickListener(v -> submitTypedMessage());
        stopSpeechButton.setOnClickListener(v -> stopSpeechPlayback());
        narrationMuteButton.setOnClickListener(v -> toggleNarrationMute());
        googleSignInButton.setOnClickListener(v -> startGoogleSignIn());
        googleToolsButton.setOnClickListener(v -> connectGoogleToolsFromShell());
        termuxPairButton.setOnClickListener(v -> showTermuxPairingDialog());
        legacyChatToggleButton.setOnClickListener(v -> toggleLegacyChatVisible());
        driveRecentButton.setOnClickListener(v -> showDriveSearchDialog());
        driveFoldersButton.setOnClickListener(v -> cycleDriveSortMode());
        driveDocsButton.setOnClickListener(v -> cycleDriveFilterMode());
        driveParentButton.setOnClickListener(v -> manualRefreshDriveBrowser("button"));
        driveSpeechSettingsButton.setOnClickListener(v -> showDriveNarrationSpeechSettingsDialog());
        driveReaderPlayerPlayPauseButton.setOnClickListener(v -> toggleDriveReaderPlayback());
        driveReaderPlayerDownloadButton.setOnClickListener(v -> renderDocumentAudio());
        driveReaderPlayerRerenderButton.setOnClickListener(v -> rerenderDocumentAudio());
        driveReaderPlayerStopButton.setOnClickListener(v -> stopDocumentReader("stopped"));
        driveReaderPlayerCloseButton.setOnClickListener(v -> closeDocumentReaderView("closed"));
        driveReaderPlayerSeekBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                if (fromUser) updateDriveReaderSeekPreview(progress);
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {
                driveReaderUserSeeking = true;
            }

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {
                driveReaderUserSeeking = false;
                scrubDriveReaderTo(seekBar == null ? 0 : seekBar.getProgress());
            }
        });
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
        refreshDriveReaderPlayer();
        refreshAuthStatus();
        main.postDelayed(this::loadDriveRecentFiles, 450L);
        scheduleDriveBrowserPoll();
        setSpeechPlaying(false);
    }

    private void loadDriveRecentFiles() {
        loadDriveBrowser("docs", activeDriveFolderId, "Narratable Docs");
    }

    private void loadDriveFolders() {
        loadDriveBrowser("docs", activeDriveFolderId, "Narratable Docs");
    }

    private void loadDriveDocs() {
        loadDriveBrowser("docs", activeDriveFolderId, "Narratable Docs");
    }

    private void showDriveSearchDialog() {
        EditText input = singleLineEdit("Search narratable docs", driveSearchQuery);
        new AlertDialog.Builder(this)
                .setTitle("Search Docs")
                .setView(input)
                .setPositiveButton("Search", (dialog, which) -> {
                    driveSearchQuery = input.getText().toString().trim();
                    loadDriveRecentFiles();
                })
                .setNegativeButton("Clear", (dialog, which) -> {
                    driveSearchQuery = "";
                    loadDriveRecentFiles();
                })
                .show();
    }

    private void cycleDriveSortMode() {
        if ("modified_desc".equals(driveSortMode)) {
            driveSortMode = "name_asc";
            setDriveBrowserStatus("Sorted A to Z.", false);
        } else {
            driveSortMode = "modified_desc";
            setDriveBrowserStatus("Sorted by date modified.", false);
        }
        loadDriveRecentFiles();
    }

    private void cycleDriveFilterMode() {
        if ("docs_all".equals(driveFilterMode)) {
            driveFilterMode = "voice_cached";
            setDriveBrowserStatus("Filter: voice cached docs.", false);
        } else {
            driveFilterMode = "docs_all";
            setDriveBrowserStatus("Filter: all narratable Google Docs.", false);
        }
        loadDriveRecentFiles();
    }

    private void navigateDriveParent() {
        if (driveFolderStack.isEmpty()) {
            activeDriveFolderId = "";
            activeDriveFolderName = "Narratable Docs";
            loadDriveRecentFiles();
            return;
        }
        DriveFolderCrumb parent = driveFolderStack.remove(driveFolderStack.size() - 1);
        activeDriveFolderId = parent.id;
        activeDriveFolderName = parent.name;
        if (activeDriveFolderId.isEmpty()) {
            loadDriveRecentFiles();
        } else {
            loadDriveFolder(activeDriveFolderId, activeDriveFolderName, false);
        }
    }

    private void loadDriveFolder(String folderId, String folderName, boolean pushCurrent) {
        if (pushCurrent) {
            driveFolderStack.add(new DriveFolderCrumb(activeDriveFolderId, activeDriveFolderName));
        }
        activeDriveFolderId = folderId == null ? "" : folderId;
        activeDriveFolderName = folderName == null || folderName.trim().isEmpty() ? "Folder" : folderName.trim();
        loadDriveBrowser("docs", activeDriveFolderId, activeDriveFolderName);
    }

    private void loadDriveBrowser(String mode, String folderId, String title) {
        loadDriveBrowser(mode, folderId, title, false);
    }

    private void loadDriveBrowser(String mode, String folderId, String title, boolean fromPoll) {
        loadDriveBrowser(mode, folderId, title, fromPoll, false);
    }

    private void loadDriveBrowser(String mode, String folderId, String title, boolean fromPoll, boolean preserveCurrentList) {
        String normalizedMode = mode == null || mode.trim().isEmpty() ? "docs" : mode.trim();
        String normalizedFolderId = folderId == null ? "" : folderId.trim();
        String normalizedTitle = title == null || title.trim().isEmpty() ? "Narratable Docs" : title.trim();
        currentDriveBrowserMode = normalizedMode;
        currentDriveBrowserFolderId = normalizedFolderId;
        currentDriveBrowserTitle = normalizedTitle;
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (!firebaseConfigured) {
            stopDriveBrowserPolling();
            renderDriveBrowserMessage("Drive Reader needs Google configuration in this build.", true);
            return;
        }
        if (account == null || !hasAllGoogleToolScopes(account)) {
            stopDriveBrowserPolling();
            renderDriveBrowserMessage("Connect Google Drive to browse recent files and folders.", false);
            return;
        }
        if (busy) {
            if (!fromPoll) setDriveBrowserStatus("Working. Drive refresh will be available when the current request finishes.", false);
            scheduleDriveBrowserPoll();
            return;
        }
        if (driveBrowserRequestInFlight) {
            if (!fromPoll) setDriveBrowserStatus("Drive refresh is already running.", false);
            scheduleDriveBrowserPoll();
            return;
        }
        driveBrowserRequestInFlight = true;
        if (fromPoll) {
            setDriveBrowserStatus("Checking Drive for new docs...", false);
        } else {
            setDriveBrowserStatus((preserveCurrentList ? "Refreshing " : "Loading ") + normalizedTitle + "...", false);
            if (driveBrowserList != null && !(preserveCurrentList && driveBrowserHasRenderedList)) {
                driveBrowserList.removeAllViews();
                driveBrowserList.addView(driveLoadingRow("Loading " + normalizedTitle + "..."), matchWrap());
            }
        }
        executor.execute(() -> {
            GoogleDriveClient.DriveResult result;
            try {
                result = googleDriveClient.listNarratableDocs(account, normalizedFolderId, driveSearchQuery, driveSortMode, 40);
            } catch (Exception ex) {
                result = GoogleDriveClient.DriveResult.error("drive_request_exception", "Drive request failed: " + shortMessage(ex.getMessage()));
            }
            GoogleDriveClient.DriveResult finalResult = result;
            main.post(() -> renderDriveBrowserResult(normalizedMode, normalizedTitle, finalResult, fromPoll));
        });
    }

    private void scheduleDriveBrowserPoll() {
        driveBrowserPollActive = true;
        main.removeCallbacks(driveBrowserPollRunnable);
        main.postDelayed(driveBrowserPollRunnable, DRIVE_BROWSER_POLL_INTERVAL_MS);
    }

    private void stopDriveBrowserPolling() {
        driveBrowserPollActive = false;
        main.removeCallbacks(driveBrowserPollRunnable);
    }

    private void refreshCurrentDriveBrowserFromPoll() {
        if (!driveBrowserPollActive) return;
        if (driveBrowserList == null) {
            scheduleDriveBrowserPoll();
            return;
        }
        loadDriveBrowser(currentDriveBrowserMode, currentDriveBrowserFolderId, currentDriveBrowserTitle, true);
    }

    private void manualRefreshDriveBrowser(String reason) {
        if (busy || driveBrowserRequestInFlight) {
            pendingManualDriveRefresh = true;
            setDriveBrowserStatus("Refresh queued. Waiting for current Drive request...", false);
            scheduleDriveBrowserPoll();
            return;
        }
        pendingManualDriveRefresh = false;
        setDriveBrowserStatus("Refreshing Drive...", false);
        loadDriveBrowser(currentDriveBrowserMode, currentDriveBrowserFolderId, currentDriveBrowserTitle, false, true);
    }

    private void runQueuedDriveRefreshIfNeeded() {
        if (!pendingManualDriveRefresh) return;
        pendingManualDriveRefresh = false;
        main.postDelayed(() -> manualRefreshDriveBrowser("queued"), 250L);
    }

    private void scheduleDriveRefreshAfterHandoff(String reason) {
        lastDriveHandoffAtMs = 0L;
        pendingManualDriveRefresh = true;
        setDriveBrowserStatus("Returning from Google approval. Refreshing Drive...", false);
        main.removeCallbacks(driveBrowserPollRunnable);
        main.postDelayed(() -> manualRefreshDriveBrowser(reason), DRIVE_HANDOFF_REFRESH_DELAY_MS);
    }

    private TextView driveLoadingRow(String text) {
        TextView row = new TextView(this);
        row.setText(text);
        row.setTextSize(15);
        row.setTextColor(COLOR_SECONDARY);
        row.setPadding(dp(12), dp(14), dp(12), dp(14));
        row.setBackgroundColor(COLOR_SURFACE);
        return row;
    }

    private void renderDriveBrowserMessage(String message, boolean danger) {
        setDriveBrowserStatus(message, danger);
        if (driveBrowserList == null) return;
        if (driveBrowserHasRenderedList && danger) return;
        driveBrowserList.removeAllViews();
        driveBrowserList.addView(driveLoadingRow(message), matchWrap());
    }

    private void renderDriveBrowserResult(String mode, String title, GoogleDriveClient.DriveResult result, boolean fromPoll) {
        driveBrowserRequestInFlight = false;
        if (result == null) {
            renderDriveBrowserMessage("Drive request returned no result. Tap Refresh to retry.", true);
            scheduleDriveBrowserPoll();
            runQueuedDriveRefreshIfNeeded();
            return;
        }
        if (!result.ok) {
            if (result.recoverableAuthException != null) {
                stopDriveBrowserPolling();
                setDriveBrowserStatus("Drive permission needs approval. Approve Drive, then tap Refresh.", true);
                try {
                    lastDriveHandoffAtMs = SystemClock.elapsedRealtime();
                    startActivityForResult(result.recoverableAuthException.getIntent(), REQUEST_DRIVE_AUTH);
                } catch (Exception ex) {
                    renderDriveBrowserMessage("Drive permission approval failed to open: " + shortMessage(ex.getMessage()), true);
                }
                return;
            }
            renderDriveBrowserMessage("Drive failed [" + result.error + "]: " + result.detail + ". Tap Refresh to retry.", true);
            scheduleDriveBrowserPoll();
            runQueuedDriveRefreshIfNeeded();
            return;
        }
        if (driveBrowserPathView != null) {
            driveBrowserPathView.setText(drivePathLabel(mode, title));
        }
        driveBrowserHasRenderedList = true;
        if (driveBrowserList != null) {
            driveBrowserList.removeAllViews();
            if (result.files.isEmpty()) {
                driveBrowserList.addView(driveLoadingRow("No files found."), matchWrap());
            } else {
                addDriveGridCards(result.files);
            }
        }
        setDriveBrowserStatus(driveBrowserSummary(result.files.size()) + " | auto-refresh 30s | manual refresh ready", false);
        scheduleDriveBrowserPoll();
        runQueuedDriveRefreshIfNeeded();
    }

    private String drivePathLabel(String mode, String title) {
        String base = driveSearchQuery == null || driveSearchQuery.trim().isEmpty()
                ? "My Drive / Google Docs"
                : "Search: " + driveSearchQuery.trim();
        if ("voice_cached".equals(driveFilterMode)) base += " / Voice cached";
        return base;
    }

    private String driveBrowserSummary(int count) {
        String sort = "name_asc".equals(driveSortMode) ? "A to Z" : "date modified";
        String filter = "voice_cached".equals(driveFilterMode) ? "voice cached" : "Google Docs";
        return count + " narratable docs | " + filter + " | " + sort + " | " + driveVoiceSummary();
    }

    private void refreshDriveReaderPlayer() {
        DocumentReaderState reader = activeDocumentReader;
        updateDriveNarrationForegroundService();
        if (driveReaderPlayerPanel == null) return;
        if (reader == null) {
            driveReaderPlayerPanel.setVisibility(View.GONE);
            setDriveRenderInteractionEnabled(true);
            return;
        }
        ensureGoogleDocAudioEntry(reader);
        driveReaderPlayerPanel.setVisibility(View.VISIBLE);
        reader.downloadedSections = countDownloadedSections(reader);
        int total = Math.max(1, reader.chunkCount());
        long pcmBytes = visiblePlayheadPcmBytes(reader);
        long offset = Math.max(0L, Math.min(pcmBytes, visiblePlayheadOffsetBytes(reader, pcmBytes)));
        int seekProgress = pcmBytes <= 0L ? 0 : Math.round((offset * 1000f) / pcmBytes);
        if (driveReaderPlayerSeekBar != null && !driveReaderUserSeeking) driveReaderPlayerSeekBar.setProgress(Math.max(0, Math.min(1000, seekProgress)));
        if (driveReaderPlayerTimeView != null) driveReaderPlayerTimeView.setText(playbackTimeLabel(offset, pcmBytes, activeTargetSampleRate(reader)));
        if (driveReaderPlayerPlayheadView != null) {
            String state = reader.paused ? "Paused" : (reader.playbackRequested ? "Playing" : "Ready");
            driveReaderPlayerPlayheadView.setText(safeDisplayName(reader.name) + " | " + state + " | " + activeTargetLabel(reader) + " | " + reader.downloadedSections + "/" + total);
        }
        if (driveReaderPlayerPlayPauseButton != null) {
            boolean playable = reader.downloadedSections > 0 || reader.playbackRequested;
            driveReaderPlayerPlayPauseButton.setVisibility(playable ? View.VISIBLE : View.GONE);
            driveReaderPlayerPlayPauseButton.setText(!reader.paused && reader.playbackRequested ? "PAUSE" : "PLAY");
            driveReaderPlayerPlayPauseButton.setEnabled(playable);
        }
        if (driveReaderPlayerDownloadButton != null) {
            driveReaderPlayerDownloadButton.setText(reader.downloadedSections >= total ? "RENDERED" : (reader.renderRequested ? "RENDERING" : "RENDER"));
            driveReaderPlayerDownloadButton.setEnabled(reader.downloadedSections < total && !reader.renderRequested);
        }
        if (driveReaderPlayerRerenderButton != null) {
            driveReaderPlayerRerenderButton.setVisibility(reader.downloadedSections > 0 ? View.VISIBLE : View.GONE);
            driveReaderPlayerRerenderButton.setEnabled(!reader.renderRequested);
            driveReaderPlayerRerenderButton.setText(reader.renderRequested ? "RERENDERING" : "RERENDER");
        }
        if (driveReaderPlayerStopButton != null) {
            boolean active = reader.renderRequested || reader.downloadRequested || reader.playbackRequested || speechPlaying;
            driveReaderPlayerStopButton.setVisibility(active ? View.VISIBLE : View.GONE);
        }
        if (driveReaderPlayerCloseButton != null) {
            driveReaderPlayerCloseButton.setVisibility(View.VISIBLE);
            driveReaderPlayerCloseButton.setEnabled(true);
        }
        setDriveRenderInteractionEnabled(!reader.renderRequested);
        reconcileDocumentPlaybackIfNeeded(reader, "player_refresh");
    }

    private void setDriveRenderInteractionEnabled(boolean enabled) {
        if (driveRecentButton != null) driveRecentButton.setEnabled(enabled);
        if (driveFoldersButton != null) driveFoldersButton.setEnabled(enabled);
        if (driveDocsButton != null) driveDocsButton.setEnabled(enabled);
        if (driveParentButton != null) driveParentButton.setEnabled(true);
        if (driveSpeechSettingsButton != null) driveSpeechSettingsButton.setEnabled(enabled);
        if (driveBrowserList != null) {
            setViewTreeEnabled(driveBrowserList, enabled);
            driveBrowserList.setAlpha(enabled ? 1f : 0.55f);
        }
    }

    private void setViewTreeEnabled(View view, boolean enabled) {
        if (view == null) return;
        view.setEnabled(enabled);
        if (!(view instanceof ViewGroup)) return;
        ViewGroup group = (ViewGroup) view;
        for (int i = 0; i < group.getChildCount(); i++) {
            setViewTreeEnabled(group.getChildAt(i), enabled);
        }
    }

    private void scrubDriveReaderTo(int progress) {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null) return;
        long pcmBytes = visiblePlayheadPcmBytes(reader);
        long offset = pcmBytes <= 0L ? 0L : Math.max(0L, Math.min(pcmBytes, Math.round((progress / 1000.0) * pcmBytes)));
        offset -= (offset & 1L);
        if (pcmBytes <= 0L) {
            reader.playbackOffsetBytes = 0L;
            reader.status = "nothing rendered yet";
            refreshDriveReaderPlayer();
            return;
        }
        stopHostedSpeechPlayback("reader_scrub");
        playDocumentAudioAtVisibleOffset(reader, offset);
    }

    private void updateDriveReaderSeekPreview(int progress) {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null || driveReaderPlayerTimeView == null) return;
        long pcmBytes = visiblePlayheadPcmBytes(reader);
        long offset = pcmBytes <= 0L ? 0L : Math.max(0L, Math.min(pcmBytes, Math.round((progress / 1000.0) * pcmBytes)));
        driveReaderPlayerTimeView.setText(playbackTimeLabel(offset, pcmBytes, activeTargetSampleRate(reader)));
    }

    private File activeTargetFile(DocumentReaderState reader) {
        if (reader == null || reader.audioEntry == null) return null;
        return reader.audioEntry.sectionFile(Math.max(0, Math.min(reader.chunkCount() - 1, reader.playbackTargetIndex)));
    }

    private long activeTargetPcmBytes(DocumentReaderState reader) {
        File file = activeTargetFile(reader);
        return file != null && file.exists() ? Math.max(0L, file.length() - 44L) : 0L;
    }

    private long visiblePlayheadPcmBytes(DocumentReaderState reader) {
        if (reader == null || reader.audioEntry == null) return 0L;
        long total = 0L;
        for (int i = 0; i < reader.chunkCount(); i++) {
            File file = reader.audioEntry.sectionFile(i);
            if (file != null && file.exists()) total += Math.max(0L, file.length() - 44L);
        }
        return total > 0L ? total : activeTargetPcmBytes(reader);
    }

    private long visiblePlayheadOffsetBytes(DocumentReaderState reader, long totalPcmBytes) {
        if (reader == null || reader.audioEntry == null) return 0L;
        long prior = renderedPcmBeforeSection(reader, reader.playbackTargetIndex);
        long current = Math.max(0L, Math.min(reader.activePlaybackPcmBytes, reader.playbackOffsetBytes));
        return Math.max(0L, Math.min(totalPcmBytes, prior + current));
    }

    private long renderedPcmBeforeSection(DocumentReaderState reader, int sectionIndex) {
        if (reader == null || reader.audioEntry == null) return 0L;
        long total = 0L;
        int limit = Math.max(0, Math.min(reader.chunkCount(), sectionIndex));
        for (int i = 0; i < limit; i++) {
            File file = reader.audioEntry.sectionFile(i);
            if (file != null && file.exists()) total += Math.max(0L, file.length() - 44L);
        }
        return total;
    }

    private void playDocumentAudioAtVisibleOffset(DocumentReaderState reader, long visibleOffsetBytes) {
        if (reader == null || reader.audioEntry == null) return;
        long remaining = Math.max(0L, visibleOffsetBytes);
        for (int i = 0; i < reader.chunkCount(); i++) {
            File file = reader.audioEntry.sectionFile(i);
            long length = file != null && file.exists() ? Math.max(0L, file.length() - 44L) : 0L;
            if (length <= 0L) continue;
            if (remaining <= length || i == reader.chunkCount() - 1) {
                reader.currentIndex = i;
                reader.playbackTargetKind = "section";
                reader.playbackTargetIndex = i;
                reader.playbackOffsetBytes = Math.max(0L, Math.min(length, remaining));
                reader.status = "scrubbed to " + activeTargetLabel(reader) + " " + playbackClock(reader.playbackOffsetBytes, activeTargetSampleRate(reader));
                persistDocumentPlaybackPosition(reader, reader.status);
                playDocumentAudioTarget(reader, "section", i, reader.playbackOffsetBytes);
                return;
            }
            remaining -= length;
        }
        reader.status = "nothing rendered at that position";
        refreshDriveReaderPlayer();
    }

    private int activeTargetSampleRate(DocumentReaderState reader) {
        return GoogleDocAudioLibrary.DEFAULT_SAMPLE_RATE;
    }

    private String activeTargetLabel(DocumentReaderState reader) {
        if (reader == null) return "Section 1";
        return "Section " + (Math.max(0, reader.playbackTargetIndex) + 1) + " of " + reader.chunkCount();
    }

    private String playbackTimeLabel(long offsetBytes, long pcmBytes, int sampleRate) {
        return playbackClock(offsetBytes, sampleRate) + " / " + playbackClock(pcmBytes, sampleRate);
    }

    private String playbackClock(long pcmBytes, int sampleRate) {
        long seconds = Math.max(0L, pcmBytes / 2L) / Math.max(1, sampleRate);
        return String.format(Locale.US, "%d:%02d", seconds / 60L, seconds % 60L);
    }

    private void toggleDriveReaderPlayback() {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null) {
            showAssistantMessage("No Google Doc is indexed yet.");
            return;
        }
        if (!reader.paused && reader.playbackRequested) {
            if (!isDocumentAudioPlaybackLive(reader)) {
                reconcileDocumentPlaybackIfNeeded(reader, "play_button_false_playing");
            } else {
                pauseDocumentReader();
            }
        } else {
            resumeDocumentReader();
        }
        refreshDriveReaderPlayer();
    }

    private void setDriveBrowserStatus(String message, boolean danger) {
        if (driveBrowserStatusView != null) {
            driveBrowserStatusView.setText(message == null ? "" : message);
            driveBrowserStatusView.setTextColor(danger ? COLOR_DANGER : COLOR_SECONDARY);
        }
    }

    private void addDriveGridCards(List<GoogleDriveClient.DriveFile> files) {
        if (driveBrowserList == null || files == null) return;
        for (int i = 0; i < files.size(); i += 2) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, 0, 0, dp(8));
            row.addView(driveFileRow(files.get(i)), weightedHeight(dp(168)));
            if (i + 1 < files.size()) {
                row.addView(driveFileRow(files.get(i + 1)), weightedHeight(dp(168)));
            } else {
                TextView spacer = new TextView(this);
                row.addView(spacer, weightedHeight(dp(168)));
            }
            driveBrowserList.addView(row, matchWrap());
        }
    }

    private View driveFileRow(GoogleDriveClient.DriveFile file) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(dp(10), dp(10), dp(10), dp(10));
        row.setBackground(makeDriveFileBackground(file));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(dp(4), 0, dp(4), 0);
        row.setLayoutParams(params);

        TextView name = new TextView(this);
        name.setText(driveFileIcon(file) + " " + safeDisplayName(file.name));
        name.setTextSize(14);
        name.setTypeface(Typeface.DEFAULT_BOLD);
        name.setTextColor(COLOR_TEXT);
        name.setSingleLine(true);
        name.setEllipsize(TextUtils.TruncateAt.END);
        row.addView(name, matchWrap());

        TextView meta = new TextView(this);
        meta.setText(driveKindLabel(file) + " | " + modifiedLabel(file.modifiedTime));
        meta.setTextSize(11);
        meta.setTextColor(COLOR_SECONDARY);
        meta.setPadding(0, dp(2), 0, 0);
        row.addView(meta, matchWrap());

        Button narrate = button("Narrate", 12, "Narrate " + safeDisplayName(file.name) + " with " + driveVoiceSummary());
        narrate.setTextColor(COLOR_BACKGROUND);
        narrate.setBackgroundColor(COLOR_ACCENT);
        LinearLayout.LayoutParams narrateParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(40));
        narrateParams.setMargins(0, dp(8), 0, 0);
        row.addView(narrate, narrateParams);
        narrate.setOnClickListener(v -> openDriveBrowserFile(file));

        row.setContentDescription(driveKindLabel(file) + ": " + safeDisplayName(file.name));
        row.setOnClickListener(v -> openDriveBrowserFile(file));
        return row;
    }

    private GradientDrawable makeDriveFileBackground(GoogleDriveClient.DriveFile file) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setCornerRadius(dp(8));
        drawable.setColor(COLOR_CARD);
        int stroke = isDriveFolder(file) ? COLOR_ACCENT : (isDriveGoogleDoc(file) ? COLOR_PRIMARY : COLOR_SURFACE);
        drawable.setStroke(dp(1), stroke);
        return drawable;
    }

    private void openDriveBrowserFile(GoogleDriveClient.DriveFile file) {
        if (file == null) return;
        if (isDriveFolder(file)) {
            loadDriveFolder(file.id, file.name, true);
            return;
        }
        if (isDriveGoogleDoc(file)) {
            replaceActiveDocumentReader("switching documents");
            readDocumentById(file.id, file.name, "Drive Reader", true);
            return;
        }
        if (file.webViewLink != null && !file.webViewLink.trim().isEmpty()) {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(file.webViewLink)));
            } catch (ActivityNotFoundException ex) {
                setDriveBrowserStatus("No app can open that Drive link.", true);
            }
            return;
        }
        setDriveBrowserStatus("This file type can be indexed later: " + driveKindLabel(file), false);
    }

    private boolean isDriveFolder(GoogleDriveClient.DriveFile file) {
        return file != null && "application/vnd.google-apps.folder".equals(file.mimeType);
    }

    private boolean isDriveGoogleDoc(GoogleDriveClient.DriveFile file) {
        return file != null && "application/vnd.google-apps.document".equals(file.mimeType);
    }

    private String driveFileIcon(GoogleDriveClient.DriveFile file) {
        if (isDriveFolder(file)) return "[Folder]";
        if (isDriveGoogleDoc(file)) return "[Doc]";
        String mime = file == null || file.mimeType == null ? "" : file.mimeType;
        if (mime.startsWith("image/")) return "[Image]";
        if (mime.startsWith("audio/")) return "[Audio]";
        if (mime.startsWith("video/")) return "[Video]";
        return "[File]";
    }

    private String driveKindLabel(GoogleDriveClient.DriveFile file) {
        if (isDriveFolder(file)) return "Folder";
        if (isDriveGoogleDoc(file)) return "Google Doc";
        String mime = file == null || file.mimeType == null || file.mimeType.trim().isEmpty() ? "file" : file.mimeType.trim();
        return mime;
    }

    private String safeDisplayName(String value) {
        String clean = value == null ? "" : value.replaceAll("\\s+", " ").trim();
        return clean.isEmpty() ? "Untitled" : clean;
    }

    private String modifiedLabel(String modifiedTime) {
        String clean = modifiedTime == null ? "" : modifiedTime.trim();
        if (clean.length() >= 10) return "Modified " + clean.substring(0, 10);
        return "Modified time unknown";
    }


    private void loadDriveSpeechSettings() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        driveSpeechProvider = normalizeDriveSpeechProvider(prefs.getString(KEY_DRIVE_SPEECH_PROVIDER, DEFAULT_DRIVE_SPEECH_PROVIDER));
        driveSpeechModelId = firstNonEmpty(prefs.getString(KEY_DRIVE_SPEECH_MODEL, DEFAULT_DRIVE_SPEECH_MODEL), DEFAULT_DRIVE_SPEECH_MODEL);

        String savedNarratorVoiceName = prefs.getString(KEY_DRIVE_SPEECH_NARRATOR_VOICE_NAME, DEFAULT_DRIVE_NARRATOR_VOICE);
        String savedNarratorVoiceId = prefs.getString(KEY_DRIVE_SPEECH_NARRATOR_VOICE_ID, "");
        String savedDialogueVoiceName = prefs.getString(KEY_DRIVE_SPEECH_DIALOGUE_VOICE_NAME, driveNarratorVoiceName);
        String savedDialogueVoiceId = prefs.getString(KEY_DRIVE_SPEECH_DIALOGUE_VOICE_ID, "");
        String savedNotesVoiceName = prefs.getString(KEY_DRIVE_SPEECH_NOTES_VOICE_NAME, driveNarratorVoiceName);
        String savedNotesVoiceId = prefs.getString(KEY_DRIVE_SPEECH_NOTES_VOICE_ID, "");

        driveNarratorVoiceName = migrateDriveRoleVoiceName(savedNarratorVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
        driveNarratorVoiceId = migrateDriveRoleVoiceId(driveNarratorVoiceName, savedNarratorVoiceId);
        driveDialogueVoiceName = migrateDriveRoleVoiceName(savedDialogueVoiceName, driveNarratorVoiceName);
        driveDialogueVoiceId = migrateDriveRoleVoiceId(driveDialogueVoiceName, savedDialogueVoiceId);
        driveNotesVoiceName = migrateDriveRoleVoiceName(savedNotesVoiceName, driveNarratorVoiceName);
        driveNotesVoiceId = migrateDriveRoleVoiceId(driveNotesVoiceName, savedNotesVoiceId);

        if (!TextUtils.equals(firstNonEmpty(savedNarratorVoiceName, ""), driveNarratorVoiceName)
                || !TextUtils.equals(firstNonEmpty(savedDialogueVoiceName, ""), driveDialogueVoiceName)
                || !TextUtils.equals(firstNonEmpty(savedNotesVoiceName, ""), driveNotesVoiceName)
                || !TextUtils.equals(firstNonEmpty(savedNarratorVoiceId, ""), driveNarratorVoiceId)
                || !TextUtils.equals(firstNonEmpty(savedDialogueVoiceId, ""), driveDialogueVoiceId)
                || !TextUtils.equals(firstNonEmpty(savedNotesVoiceId, ""), driveNotesVoiceId)) {
            prefs.edit()
                    .putString(KEY_DRIVE_SPEECH_NARRATOR_VOICE_NAME, driveNarratorVoiceName)
                    .putString(KEY_DRIVE_SPEECH_NARRATOR_VOICE_ID, driveNarratorVoiceId)
                    .putString(KEY_DRIVE_SPEECH_DIALOGUE_VOICE_NAME, driveDialogueVoiceName)
                    .putString(KEY_DRIVE_SPEECH_DIALOGUE_VOICE_ID, driveDialogueVoiceId)
                    .putString(KEY_DRIVE_SPEECH_NOTES_VOICE_NAME, driveNotesVoiceName)
                    .putString(KEY_DRIVE_SPEECH_NOTES_VOICE_ID, driveNotesVoiceId)
                    .apply();
            LocalLog.info("doc_audio", "drive_speech_legacy_skylar_migrated roles=" + driveVoiceSummary());
        }

        driveCharacterRegistryDocId = prefs.getString(KEY_DRIVE_CHARACTER_REGISTRY_DOC_ID, "");
        driveCharacterRegistryLoadedAt = prefs.getLong(KEY_DRIVE_CHARACTER_REGISTRY_LOADED_AT, 0L);
        String cachedRegistry = prefs.getString(KEY_DRIVE_CHARACTER_REGISTRY_JSON, "");
        CharacterVoiceRegistry assetRegistry = CharacterVoiceRegistry.fromAsset(this);
        driveCharacterRegistry = cachedRegistry == null || cachedRegistry.trim().isEmpty()
                ? assetRegistry
                : CharacterVoiceRegistry.fromCacheMergedWithAsset(cachedRegistry, assetRegistry);
        try {
            prefs.edit().putString(KEY_DRIVE_CHARACTER_REGISTRY_JSON, driveCharacterRegistry.toJson().toString()).apply();
        } catch (Exception ex) {
            LocalLog.warn("doc_audio", "drive_character_registry_cache_refresh_failed " + shortMessage(ex.getMessage()));
        }
        driveVoiceCatalog = VoiceCatalogEntry.fromCache(prefs.getString(KEY_DRIVE_VOICE_CATALOG_JSON, ""));
    }

    private void saveDriveSpeechSettings() {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(KEY_DRIVE_SPEECH_PROVIDER, driveSpeechProvider)
                .putString(KEY_DRIVE_SPEECH_MODEL, driveSpeechModelId)
                .putString(KEY_DRIVE_SPEECH_NARRATOR_VOICE_NAME, driveNarratorVoiceName)
                .putString(KEY_DRIVE_SPEECH_NARRATOR_VOICE_ID, driveNarratorVoiceId)
                .putString(KEY_DRIVE_SPEECH_DIALOGUE_VOICE_NAME, driveDialogueVoiceName)
                .putString(KEY_DRIVE_SPEECH_DIALOGUE_VOICE_ID, driveDialogueVoiceId)
                .putString(KEY_DRIVE_SPEECH_NOTES_VOICE_NAME, driveNotesVoiceName)
                .putString(KEY_DRIVE_SPEECH_NOTES_VOICE_ID, driveNotesVoiceId)
                .apply();
        if (activeDocumentReader != null) {
            configureReaderSpeechProfile(activeDocumentReader, true);
            materializeVoiceSplitPlan(activeDocumentReader);
            activeDocumentReader.withClearedAudioEntry();
        }
        refreshDriveReaderPlayer();
        setDriveBrowserStatus("Drive Narrate speech: " + driveSpeechProviderLabel() + " | " + driveVoiceSummary() + " | model " + driveSpeechModelId, false);
    }

    private String normalizeDriveSpeechProvider(String provider) {
        return normalizeDriveSpeechProviderStatic(provider);
    }

    private String driveSpeechProviderLabel() {
        return "elevenlabs".equals(driveSpeechProvider) ? "ElevenLabs render-only" : "Cartesia";
    }

    private String migrateDriveRoleVoiceName(String savedVoiceName, String fallbackVoiceName) {
        String clean = firstNonEmpty(savedVoiceName, fallbackVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
        if (LEGACY_DRIVE_NARRATOR_VOICE.equalsIgnoreCase(clean)) {
            return firstNonEmpty(fallbackVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
        }
        return clean;
    }

    private String migrateDriveRoleVoiceId(String voiceName, String savedVoiceId) {
        String saved = savedVoiceId == null ? "" : savedVoiceId.trim();
        if (LEGACY_DRIVE_NARRATOR_VOICE_ID.equalsIgnoreCase(saved)) {
            saved = "";
        }
        return defaultNarratorVoiceIdFor(voiceName, saved);
    }

    private String defaultNarratorVoiceIdFor(String voiceName, String savedVoiceId) {
        String saved = savedVoiceId == null ? "" : savedVoiceId.trim();
        if (!saved.isEmpty()) return saved;
        return cartesiaVoiceIdForName(voiceName);
    }

    private String cartesiaVoiceIdForName(String voiceName) {
        String clean = voiceName == null ? "" : voiceName.trim();
        if (DEFAULT_DRIVE_NARRATOR_VOICE.equalsIgnoreCase(clean)) return DEFAULT_DRIVE_NARRATOR_VOICE_ID;
        if ("Corey - Supportive Buddy".equalsIgnoreCase(clean)) return "630ed21c-2c5c-41cf-9d82-10a7fd668370";
        if ("Gemma - Decisive Agent".equalsIgnoreCase(clean)) return "62ae83ad-4f6a-430b-af41-a9bede9286ca";
        if ("Archie - Approachable Mate".equalsIgnoreCase(clean)) return "ef191366-f52f-447a-a398-ed8c0f2943a1";
        if ("Daniel - Modern Assistant".equalsIgnoreCase(clean)) return "47c38ca4-5f35-497b-b1a3-415245fb35e1";
        if ("Jacqueline - Reassuring Agent".equalsIgnoreCase(clean)) return "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc";
        if ("Ronald - Thinker".equalsIgnoreCase(clean)) return "5ee9feff-1265-424a-9d7f-8e4d431a12c7";
        if ("Clive - Measured Expert".equalsIgnoreCase(clean)) return "b24f41fd-00a3-4cd8-992a-a0c9f13f3ef1";
        if ("Ella - Caring Scout".equalsIgnoreCase(clean)) return "2a12b36c-7f9b-4c3a-9f7a-72731b15323a";
        return "";
    }

    private String driveVoiceSummary() {
        return "Narrator " + driveNarratorVoiceName + ", Dialogue default " + driveDialogueVoiceName + ", Notes default " + driveNotesVoiceName;
    }

    private String driveSpeechProfileKey() {
        return driveSpeechProfileKey(true);
    }

    private String driveSpeechProfileKey(boolean voiceSplitRendering) {
        String raw = driveSpeechProvider + "|" + driveSpeechModelId + "|n=" + driveNarratorVoiceName + ":" + driveNarratorVoiceId
                + "|d=" + driveDialogueVoiceName + ":" + driveDialogueVoiceId
                + "|notes=" + driveNotesVoiceName + ":" + driveNotesVoiceId
                + "|registry=" + driveCharacterRegistryFingerprint()
                + "|compiler=" + MarkdownNarrationDocument.COMPILER_ID
                + "|voiceResolver=v" + DRIVE_VOICE_RESOLVER_VERSION
                + "|workflow=" + (voiceSplitRendering ? "voice_split_character_render" : "drive_narrate_role_defaults");
        return Integer.toHexString(raw.hashCode()) + "-" + raw.replaceAll("[^A-Za-z0-9_.-]", "_");
    }

    private String driveCharacterRegistryFingerprint() {
        try {
            return driveCharacterRegistry == null ? "no-registry" : Integer.toHexString(driveCharacterRegistry.toJson().toString().hashCode());
        } catch (Exception ex) {
            return "registry-error";
        }
    }

    private String driveSpeechProfileJson() {
        return driveSpeechProfileJson(true);
    }

    private String driveSpeechProfileJson(boolean voiceSplitRendering) {
        try {
            return new JSONObject()
                    .put("provider", driveSpeechProvider)
                    .put("modelId", driveSpeechModelId)
                    .put("workflow", voiceSplitRendering ? "voice_split_character_render" : "drive_narrate_role_defaults")
                    .put("voiceSplitRendering", voiceSplitRendering)
                    .put("voiceResolverVersion", DRIVE_VOICE_RESOLVER_VERSION)
                    .put("roles", new JSONObject()
                            .put("narrator", roleVoiceJson(driveNarratorVoiceName, driveNarratorVoiceId))
                            .put("dialogue", roleVoiceJson(driveDialogueVoiceName, driveDialogueVoiceId))
                            .put("notes", roleVoiceJson(driveNotesVoiceName, driveNotesVoiceId)))
                    .put("characterRegistry", driveCharacterRegistry.toJson())
                    .put("registryDocumentId", driveCharacterRegistryDocId)
                    .toString();
        } catch (Exception ex) {
            return "{}";
        }
    }

    private JSONObject roleVoiceJson(String voiceName, String voiceId) throws Exception {
        return new JSONObject().put("voiceName", firstNonEmpty(voiceName, DEFAULT_DRIVE_NARRATOR_VOICE)).put("voiceId", voiceId == null ? "" : voiceId);
    }

    private void showDriveNarrationSpeechSettingsDialog() {
        loadDriveSpeechSettings();
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(16), dp(8), dp(16), dp(4));
        TextView summary = new TextView(this);
        summary.setText("Drive Narrate uses Cartesia by default. ElevenLabs is explicit render-only for special cases; it is never an operational fallback. Voice audition means metadata review, short previews, then explicit profile approval.");
        summary.setTextColor(COLOR_TEXT);
        summary.setTextSize(14);
        panel.addView(summary, matchWrap());
        EditText providerEdit = singleLineEdit("Provider: cartesia or elevenlabs", driveSpeechProvider);
        EditText modelEdit = singleLineEdit("Speech model", driveSpeechModelId);
        EditText narratorEdit = singleLineEdit("Narrator voice name or id", driveNarratorVoiceName);
        EditText dialogueEdit = singleLineEdit("Dialogue voice name or id", driveDialogueVoiceName);
        EditText notesEdit = singleLineEdit("Notes voice name or id", driveNotesVoiceName);
        EditText searchEdit = singleLineEdit("Search hosted voices", "");
        TextView results = new TextView(this);
        results.setText(voiceCatalogSummary());
        results.setTextColor(COLOR_SECONDARY);
        results.setTextSize(12);
        results.setPadding(0, dp(8), 0, dp(8));
        TextView speakerNotice = new TextView(this);
        speakerNotice.setText("Speaker profiles are metadata only here. Drive Narrate uses the selected narrator, dialogue default, notes default, and registry-resolved character voices during render.");
        speakerNotice.setTextColor(COLOR_SECONDARY);
        speakerNotice.setTextSize(12);
        speakerNotice.setPadding(0, dp(8), 0, dp(4));
        panel.addView(providerEdit, matchHeight(dp(58)));
        panel.addView(modelEdit, matchHeight(dp(58)));
        panel.addView(narratorEdit, matchHeight(dp(58)));
        panel.addView(dialogueEdit, matchHeight(dp(58)));
        panel.addView(notesEdit, matchHeight(dp(58)));
        panel.addView(searchEdit, matchHeight(dp(58)));
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        Button search = button("Inspect", 12, "Inspect and categorize the selected hosted voice library metadata");
        Button preview = button("Preview", 12, "Optionally play the narrator voice with the selected model");
        actions.addView(search, weightedHeight(dp(46)));
        actions.addView(preview, weightedHeight(dp(46)));
        panel.addView(actions, matchWrap());
        Button voiceSplitFolder = button("Narration Workspace", 12, "Create the Drive workspace used for saved narration plans and rendered chunks");
        panel.addView(voiceSplitFolder, matchHeight(dp(46)));
        panel.addView(results, matchWrap());
        panel.addView(speakerNotice, matchWrap());
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Drive Narrate speech")
                .setView(panel)
                .setPositiveButton("Save", (d, which) -> {
                    driveSpeechProvider = normalizeDriveSpeechProvider(providerEdit.getText().toString());
                    driveSpeechModelId = firstNonEmpty(modelEdit.getText().toString(), DEFAULT_DRIVE_SPEECH_MODEL);
                    assignVoiceInput("narrator", narratorEdit.getText().toString());
                    assignVoiceInput("dialogue", dialogueEdit.getText().toString());
                    assignVoiceInput("notes", notesEdit.getText().toString());
                    saveDriveSpeechSettings();
                })
                .setNegativeButton("Cancel", null)
                .show();
        search.setOnClickListener(v -> searchSpeechVoicesForDialog(providerEdit.getText().toString(), searchEdit.getText().toString(), results, narratorEdit, dialogueEdit, notesEdit));
        preview.setOnClickListener(v -> previewSpeechVoice(providerEdit.getText().toString(), modelEdit.getText().toString(), narratorEdit.getText().toString(), "narrator"));
        voiceSplitFolder.setOnClickListener(v -> createDriveVoiceSplitFolderStructure());
    }

    private void searchSpeechVoicesForDialog(String providerInput, String query, TextView results, EditText narratorEdit, EditText dialogueEdit, EditText notesEdit) {
        if (hostedSpeechClient == null || !hostedSpeechClient.isConfigured()) {
            results.setText("Hosted speech is not configured in this build.");
            return;
        }
        results.setText("Searching voices...");
        executor.execute(() -> {
            try {
                JSONArray voices = hostedSpeechClient.searchVoices(normalizeDriveSpeechProvider(providerInput), query, 160);
                List<VoiceCatalogEntry> catalog = VoiceCatalogEntry.fromArray(voices);
                StringBuilder label = new StringBuilder();
                label.append("Metadata voices inspected: ").append(catalog.size()).append("\n");
                label.append(VoiceCatalogEntry.categorySummary(catalog));
                int limit = Math.min(catalog.size(), 18);
                for (int i = 0; i < limit; i++) {
                    VoiceCatalogEntry voice = catalog.get(i);
                    if (label.length() > 0) label.append('\n');
                    label.append(i + 1).append(". ").append(voice.displayLine());
                }
                if (catalog.isEmpty()) label.append("No voices matched. Try a broader search term.");
                main.post(() -> {
                    driveVoiceCatalog = catalog;
                    cacheVoiceCatalog(catalog);
                    results.setText(label.toString());
                    if (!catalog.isEmpty() && narratorEdit.getText().toString().trim().isEmpty()) narratorEdit.setText(catalog.get(0).voiceInput());
                });
            } catch (Exception ex) {
                main.post(() -> results.setText("Voice search failed: " + shortMessage(ex.getMessage())));
            }
        });
    }

    private String voiceCatalogSummary() {
        if (driveVoiceCatalog == null || driveVoiceCatalog.isEmpty()) return "Voice metadata catalog has not been inspected yet. Tap Inspect to categorize available voices; Cartesia remains the default narrator.";
        return "Cached voice metadata: " + driveVoiceCatalog.size() + " voices. " + VoiceCatalogEntry.categorySummary(driveVoiceCatalog);
    }

    private void cacheVoiceCatalog(List<VoiceCatalogEntry> catalog) {
        try {
            JSONArray array = new JSONArray();
            if (catalog != null) for (VoiceCatalogEntry entry : catalog) array.put(entry.toJson());
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_DRIVE_VOICE_CATALOG_JSON, array.toString()).apply();
        } catch (Exception ignored) { }
    }

    private void previewSpeechVoice(String providerInput, String modelId, String voiceInput, String role) {
        String cleanModel = firstNonEmpty(modelId, DEFAULT_DRIVE_SPEECH_MODEL);
        String cleanVoice = firstNonEmpty(voiceInput, DEFAULT_DRIVE_NARRATOR_VOICE);
        String voiceName = cleanVoice;
        String voiceId = "";
        if (cleanVoice.startsWith("voice_id:")) {
            voiceName = "";
            voiceId = cleanVoice.substring("voice_id:".length()).trim();
        }
        playSpeechPreview(normalizeDriveSpeechProvider(providerInput), cleanModel, voiceName, voiceId, role);
    }

    private void playSpeechPreview(String provider, String modelId, String voiceName, String voiceId, String role) {
        if (hostedSpeechClient == null || !hostedSpeechClient.isConfigured()) {
            showAssistantMessage("Hosted speech is not configured in this build.");
            return;
        }
        String utteranceId = "home_center_voice_preview_" + System.currentTimeMillis();
        activeSpeechUtteranceId = utteranceId;
        long sequence = beginSpeechSequence("new_drive_voice_preview");
        setSpeechPlaying(true);
        setDriveBrowserStatus("Previewing " + firstNonEmpty(voiceName, voiceId, DEFAULT_DRIVE_NARRATOR_VOICE) + " with " + modelId + ".", false);
        documentAudioExecutor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                connection = hostedSpeechClient.openSpeechStream("Drive Narrate preview. This voice will be used for the " + role + " role.", provider, modelId, voiceName, voiceId, role);
                int sampleRate = hostedSpeechSampleRate(connection);
                AudioTrack track = createHostedSpeechTrack(sampleRate);
                synchronized (this) {
                    if (!isCurrentSpeechSequence(sequence)) {
                        track.release();
                        return;
                    }
                    activeHostedSpeechTrack = track;
                    track.play();
                }
                byte[] pcm = readSpeechPcm(connection.getInputStream(), sequence);
                long written = writePcmToTrack(track, pcm, sequence);
                waitForHostedSpeechPlaybackDrain(track, written, sampleRate, sequence);
                main.post(() -> finishSpeechPlaybackFor(utteranceId, "stream_complete"));
                releaseHostedTrackIfActive(track);
            } catch (Exception ex) {
                main.post(() -> {
                    setDriveBrowserStatus("Voice preview failed: " + shortMessage(ex.getMessage()), true);
                    finishSpeechPlaybackFor(utteranceId, "hosted_speech_error");
                });
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private void assignVoiceInput(String role, String input) {
        String clean = firstNonEmpty(input, DEFAULT_DRIVE_NARRATOR_VOICE);
        String name = clean;
        String id = "";
        if (clean.startsWith("voice_id:")) {
            name = DEFAULT_DRIVE_NARRATOR_VOICE;
            id = clean.substring("voice_id:".length()).trim();
        }
        if ("dialogue".equals(role)) {
            driveDialogueVoiceName = name;
            driveDialogueVoiceId = id;
        } else if ("notes".equals(role)) {
            driveNotesVoiceName = name;
            driveNotesVoiceId = id;
        } else {
            driveNarratorVoiceName = name;
            driveNarratorVoiceId = id;
        }
    }

    private String speechRoleForSection(DocumentReaderState reader, int sectionIndex) {
        CharacterVoiceRule rule = characterRuleForSection(reader, sectionIndex);
        if (reader != null && reader.voiceSplitRenderingMode) return splitSpeechRole(reader, sectionIndex, rule);
        return firstNonEmpty(rule.narrationRole, "narrator").toLowerCase(Locale.US);
    }

    private String activeSpeechVoiceName(DocumentReaderState reader, int sectionIndex) {
        CharacterVoiceRule splitRule = characterRuleForSection(reader, sectionIndex);
        if (reader != null && reader.voiceSplitRenderingMode) {
            return splitProviderVoiceName(reader, sectionIndex, splitRule);
        }
        String role = speechRoleForSection(reader, sectionIndex);
        if ("dialogue".equals(role)) return firstNonEmpty(driveDialogueVoiceName, driveNarratorVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
        if ("notes".equals(role)) return firstNonEmpty(driveNotesVoiceName, driveNarratorVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
        return firstNonEmpty(driveNarratorVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
    }

    private String splitFallbackVoiceName(DocumentReaderState reader, int sectionIndex, CharacterVoiceRule rule) {
        String role = rule == null ? "" : firstNonEmpty(rule.narrationRole, "narrator").toLowerCase(Locale.US);
        String characterId = rule == null ? "" : CharacterVoiceRule.normalizeId(rule.characterId);
        if (VoiceScriptPlanner.DEFAULT_DIALOGUE_SPEAKER.equals(characterId)) {
            return firstNonEmpty(driveDialogueVoiceName, driveNarratorVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
        }
        if (("dialogue".equals(role) || "notes".equals(role)) && !"she-raw".equals(characterId)) {
            int ordinal = driveCharacterRegistry == null ? sectionIndex : driveCharacterRegistry.dialogueOrdinal(characterId);
            return DRIVE_SPLIT_FALLBACK_DIALOGUE_VOICES[Math.floorMod(ordinal, DRIVE_SPLIT_FALLBACK_DIALOGUE_VOICES.length)];
        }
        return firstNonEmpty(driveNarratorVoiceName, DEFAULT_DRIVE_NARRATOR_VOICE);
    }

    private String activeSpeechVoiceLabel(DocumentReaderState reader, int sectionIndex) {
        String name = activeSpeechVoiceName(reader, sectionIndex);
        String id = activeSpeechVoiceId(reader, sectionIndex);
        return firstNonEmpty(name, id, DEFAULT_DRIVE_NARRATOR_VOICE);
    }

    private String resolvedProviderVoiceAlias(CharacterVoiceRule rule) {
        if (rule == null || rule.voiceAlias == null) return "";
        String alias = rule.voiceAlias.trim();
        if (alias.isEmpty()) return "";
        String normalizedAlias = CharacterVoiceRule.normalizeId(alias);
        if (normalizedAlias.isEmpty()) return "";
        if (normalizedAlias.contains("voice-actor") || normalizedAlias.contains("voice_actor")) return "";
        return alias;
    }

    private boolean isVoiceIdAlias(String alias) {
        return alias != null && alias.trim().toLowerCase(Locale.US).startsWith("voice_id:");
    }

    private String voiceIdFromAlias(String alias) {
        if (!isVoiceIdAlias(alias)) return "";
        return alias.trim().substring("voice_id:".length()).trim();
    }

    private boolean voiceCatalogContainsProviderName(String alias) {
        if (alias == null || alias.trim().isEmpty() || driveVoiceCatalog == null) return false;
        String clean = alias.trim();
        for (VoiceCatalogEntry entry : driveVoiceCatalog) {
            if (entry != null && clean.equalsIgnoreCase(entry.name)) return true;
        }
        return false;
    }

    private VoiceCatalogEntry catalogVoiceForRule(CharacterVoiceRule rule) {
        return null;
    }

    private String activeSpeechVoiceId(DocumentReaderState reader, int sectionIndex) {
        if (reader != null && reader.voiceSplitRenderingMode) {
            CharacterVoiceRule rule = characterRuleForSection(reader, sectionIndex);
            return splitProviderVoiceId(reader, sectionIndex, rule);
        }
        String role = speechRoleForSection(reader, sectionIndex);
        if ("dialogue".equals(role)) return driveDialogueVoiceId == null ? "" : driveDialogueVoiceId;
        if ("notes".equals(role)) return driveNotesVoiceId == null ? "" : driveNotesVoiceId;
        return driveNarratorVoiceId == null ? "" : driveNarratorVoiceId;
    }


    private void refreshDriveCharacterRegistryForAccount(GoogleSignInAccount account) {
        if (account == null || googleDriveClient == null) return;
        try {
            JSONObject searchArgs = new JSONObject()
                    .put("query", DRIVE_CHARACTER_REGISTRY_TITLE)
                    .put("pageSize", 5);
            JSONObject search = googleDriveClient.runTool("docs.search", searchArgs, account);
            if (!search.optBoolean("ok", false)) {
                LocalLog.warn("doc_audio", "character_registry_search_failed error=" + shortMessage(search.optString("error", "")) + " detail=" + shortMessage(search.optString("detail", "")));
                return;
            }
            JSONArray files = search.optJSONArray("files");
            JSONObject registryFile = selectCharacterRegistryFile(files);
            if (registryFile == null) {
                LocalLog.info("doc_audio", "character_registry_not_found title=" + DRIVE_CHARACTER_REGISTRY_TITLE);
                return;
            }
            JSONObject readArgs = new JSONObject()
                    .put("fileId", registryFile.optString("id", ""))
                    .put("name", registryFile.optString("name", DRIVE_CHARACTER_REGISTRY_TITLE));
            JSONObject read = googleDriveClient.runTool("docs.read", readArgs, account);
            if (!read.optBoolean("ok", false)) {
                LocalLog.warn("doc_audio", "character_registry_read_failed fileId=" + shortMessage(registryFile.optString("id", "")) + " error=" + shortMessage(read.optString("error", "")));
                return;
            }
            CharacterVoiceRegistry parsed = CharacterVoiceRegistry.parse(read.optString("content", ""));
            if (!parsed.hasEntries()) {
                LocalLog.warn("doc_audio", "character_registry_empty fileId=" + shortMessage(registryFile.optString("id", "")));
                return;
            }
            driveCharacterRegistry = parsed;
            driveCharacterRegistryDocId = registryFile.optString("id", "");
            driveCharacterRegistryLoadedAt = System.currentTimeMillis();
            getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putString(KEY_DRIVE_CHARACTER_REGISTRY_JSON, parsed.toJson().toString())
                    .putString(KEY_DRIVE_CHARACTER_REGISTRY_DOC_ID, driveCharacterRegistryDocId)
                    .putLong(KEY_DRIVE_CHARACTER_REGISTRY_LOADED_AT, driveCharacterRegistryLoadedAt)
                    .apply();
            refreshActiveReaderSpeechProfileForRegistryChange("character_registry_loaded");
            LocalLog.info("doc_audio", "character_registry_loaded fileId=" + shortMessage(driveCharacterRegistryDocId) + " entries=" + parsed.size());
        } catch (Exception ex) {
            LocalLog.warn("doc_audio", "character_registry_refresh_failed " + shortMessage(ex.getMessage()));
        }
    }

    private JSONObject selectCharacterRegistryFile(JSONArray files) {
        if (files == null) return null;
        JSONObject fallback = null;
        for (int i = 0; i < files.length(); i++) {
            JSONObject file = files.optJSONObject(i);
            if (file == null) continue;
            String name = file.optString("name", "").trim();
            if (DRIVE_CHARACTER_REGISTRY_TITLE.equalsIgnoreCase(name)) return file;
            if (fallback == null && name.toLowerCase(Locale.US).contains("character voice orientation registry")) fallback = file;
        }
        return fallback;
    }

    private CharacterVoiceRule characterRuleForSection(DocumentReaderState reader, int sectionIndex) {
        if (reader != null && reader.voiceSplitRenderingMode) {
            SectionVoiceAssignment assignment = reader.voiceSplitAssignmentAt(sectionIndex);
            if (assignment != null && assignment.rule != null) return assignment.rule;
        }
        if (reader == null || reader.chunks == null || sectionIndex < 0 || sectionIndex >= reader.chunks.size()) {
            return driveCharacterRegistry.defaultNarrator();
        }
        return driveCharacterRegistry.match(reader.chunks.get(sectionIndex));
    }

    private void materializeVoiceSplitPlan(DocumentReaderState reader) {
        if (reader == null) return;
        reader.voiceSplitAssignments.clear();
        for (int i = 0; i < reader.chunkCount(); i++) {
            String chunk = reader.chunks.get(i);
            CharacterVoiceRule matched = driveCharacterRegistry.match(chunk);
            boolean explicitCast = driveCharacterRegistry.hasExplicitCastSignal(chunk, matched);
            CharacterVoiceRule rule = matched;
            String providerAlias = activeSpeechVoiceName(reader, i);
            String voiceName = providerAlias.isEmpty() || isVoiceIdAlias(providerAlias) ? splitFallbackVoiceName(reader, i, rule) : providerAlias;
            String voiceId = VoiceScriptPlanner.DEFAULT_DIALOGUE_SPEAKER.equals(rule.characterId) && driveDialogueVoiceId != null && !driveDialogueVoiceId.trim().isEmpty()
                    ? driveDialogueVoiceId.trim()
                    : isVoiceIdAlias(providerAlias) ? voiceIdFromAlias(providerAlias) : cartesiaVoiceIdForName(voiceName);
            reader.voiceSplitAssignments.add(new SectionVoiceAssignment(rule, voiceName, voiceId, firstNonEmpty(rule.narrationRole, "narrator"), explicitCast));
        }
        LocalLog.info("doc_audio", "voice_split_plan_materialized fileId=" + shortMessage(reader.fileId) + " sections=" + reader.voiceSplitAssignments.size() + " speakers=" + reader.voiceSplitSpeakerSummary());
    }

    private String splitProviderVoiceName(DocumentReaderState reader, int sectionIndex, CharacterVoiceRule rule) {
        SectionVoiceAssignment assignment = reader == null ? null : reader.voiceSplitAssignmentAt(sectionIndex);
        if (assignment != null && !assignment.voiceName.isEmpty()) return assignment.voiceName;
        String alias = resolvedProviderVoiceAlias(rule);
        if (isVoiceIdAlias(alias)) return "";
        if (!alias.isEmpty()) return alias;
        return splitFallbackVoiceName(reader, sectionIndex, rule);
    }

    private String splitProviderVoiceId(DocumentReaderState reader, int sectionIndex, CharacterVoiceRule rule) {
        SectionVoiceAssignment assignment = reader == null ? null : reader.voiceSplitAssignmentAt(sectionIndex);
        if (assignment != null && !assignment.voiceId.isEmpty()) return assignment.voiceId;
        String alias = resolvedProviderVoiceAlias(rule);
        if (isVoiceIdAlias(alias)) return voiceIdFromAlias(alias);
        String voiceName = splitProviderVoiceName(reader, sectionIndex, rule);
        return cartesiaVoiceIdForName(voiceName);
    }

    private String splitSpeechRole(DocumentReaderState reader, int sectionIndex, CharacterVoiceRule rule) {
        SectionVoiceAssignment assignment = reader == null ? null : reader.voiceSplitAssignmentAt(sectionIndex);
        if (assignment != null && !assignment.role.isEmpty()) return assignment.role;
        return firstNonEmpty(rule == null ? "" : rule.narrationRole, "narrator").toLowerCase(Locale.US);
    }

    private String stripVoiceTags(String text) {
        return stripSpeakerCueForSpeech(text == null ? "" : text.replaceAll("(?i)\\[(voice|speaker):[^\\]]+\\]", ""));
    }

    private String stripSpeakerCueForSpeech(String text) {
        if (text == null) return "";
        return text.replaceFirst("^\\s*[A-Za-z][A-Za-z0-9 .\\'\\-]{1,48}\\s*:\\s+", "").replaceAll("\\s+", " ").trim();
    }

    private void showTermuxPairingDialog() {
        if (!hasSignedInHomeUser()) {
            pendingAgentTurnAfterGoogleReconnect = "";
            showAssistantMessage("Sign in with Google first, then approve the Termux Codex pairing code.");
            startGoogleSignIn();
            return;
        }
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (!hasAllGoogleToolScopes(account)) {
            showAssistantMessage("Approve Google tools first, then pair Termux Codex.");
            requestGoogleToolPermissions(account);
            return;
        }
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(16), dp(8), dp(16), dp(4));
        TextView detail = new TextView(this);
        detail.setText("Enter the six digit code shown in Termux. This grants Drive, Docs, and safe GitHub tools through Home Center. Provider tokens stay on the Home Center backend.");
        detail.setTextColor(COLOR_TEXT);
        detail.setTextSize(15);
        panel.addView(detail, matchWrap());
        EditText pairingIdEdit = singleLineEdit("Pairing ID", "");
        EditText codeEdit = singleLineEdit("Six digit code", "");
        codeEdit.setInputType(InputType.TYPE_CLASS_NUMBER);
        panel.addView(pairingIdEdit, matchWrap());
        panel.addView(codeEdit, matchWrap());
        new AlertDialog.Builder(this)
                .setTitle("Pair Termux Codex")
                .setView(panel)
                .setPositiveButton("Approve", (dialog, which) -> approveTermuxPairing(pairingIdEdit.getText().toString(), codeEdit.getText().toString()))
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void approveTermuxPairing(String pairingId, String code) {
        approveTermuxPairing(pairingId, code, "manual_dialog");
    }

    private boolean hasPendingTermuxPairing() {
        return pendingTermuxPairingId != null && !pendingTermuxPairingId.trim().isEmpty()
                && pendingTermuxPairingCode != null && !pendingTermuxPairingCode.trim().isEmpty();
    }

    private void continuePendingTermuxPairing(String reason) {
        if (!hasPendingTermuxPairing() || pendingTermuxPairingApprovalRunning) {
            return;
        }
        if (!hasSignedInHomeUser()) {
            showAssistantMessage("Google sign-in is the only remaining approval for Shizuku-driven Termux Codex pairing.");
            startGoogleSignIn();
            return;
        }
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (!hasAllGoogleToolScopes(account)) {
            showAssistantMessage("Google tool permission is the only remaining approval for Shizuku-driven Termux Codex pairing.");
            requestGoogleToolPermissions(account);
            return;
        }
        approveTermuxPairing(pendingTermuxPairingId, pendingTermuxPairingCode, reason);
    }

    private void clearPendingTermuxPairing() {
        pendingTermuxPairingId = "";
        pendingTermuxPairingCode = "";
        pendingTermuxPairingApprovalRunning = false;
    }

    private void approveTermuxPairing(String pairingId, String code, String source) {
        if (openAiAgentClient == null || !openAiAgentClient.isConfigured()) {
            showAssistantMessage("Home Center gateway is not configured in this build.");
            return;
        }
        FirebaseUser user = firebaseAuth == null ? null : firebaseAuth.getCurrentUser();
        if (user == null) {
            showAssistantMessage("Sign in with Google first.");
            return;
        }
        pendingTermuxPairingApprovalRunning = true;
        setBusy(true);
        appendStatus("Approving Termux Codex pairing...");
        LocalLog.info("termux_pairing", "approve_start source=" + shortMessage(source));
        user.getIdToken(false)
                .addOnSuccessListener(token -> executor.execute(() -> {
                    try {
                        JSONObject response = openAiAgentClient.approveTermuxPairing(token.getToken(), pairingId, code);
                        main.post(() -> {
                            setBusy(false);
                            clearPendingTermuxPairing();
                            String email = response.optString("email", "this account");
                            showAssistantMessage("Termux Codex paired for " + email + ". Safe Home Center tools are now available from Termux.");
                            appendStatus("Termux Codex paired.");
                        });
                    } catch (Exception ex) {
                        main.post(() -> {
                            pendingTermuxPairingApprovalRunning = false;
                            setBusy(false);
                            showAssistantMessage("Termux Codex pairing failed: " + shortMessage(ex.getMessage()));
                        });
                    }
                }))
                .addOnFailureListener(ex -> {
                    pendingTermuxPairingApprovalRunning = false;
                    setBusy(false);
                    showAssistantMessage("Could not verify Google sign-in: " + shortMessage(ex.getMessage()));
                });
    }

    private void showShizukuAutomationSetup() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(18), dp(10), dp(18), dp(4));

        TextView summary = new TextView(this);
        summary.setText("One guided setup path for Termux, @mmmbuto Codex, Shizuku, rish, and Home Center pairing. Shizuku launches pairing automatically; Android only stops for real install, Shizuku, or Google approval.");
        summary.setTextColor(COLOR_TEXT);
        summary.setTextSize(15);
        summary.setPadding(0, 0, 0, dp(10));
        panel.addView(summary, matchWrap());

        TextView status = new TextView(this);
        status.setText(shizukuAutomationStatusText());
        status.setTextColor(COLOR_SECONDARY);
        status.setTextSize(14);
        status.setPadding(0, 0, 0, dp(12));
        panel.addView(status, matchWrap());

        Button termux = button(packageInstalled(TERMUX_PACKAGE) ? "Open Termux" : "Install Termux", 15, "Open Termux or the official Termux install page");
        Button shizuku = button(packageInstalled(SHIZUKU_PACKAGE) ? "Open Shizuku" : "Install Shizuku", 15, "Open Shizuku or the official Shizuku download page");
        Button setup = button("Open Shizuku pairing guide", 15, "Open the official Shizuku wireless debugging setup guide");
        Button copyProbe = button("Copy one-click Termux command", 15, "Copy the Home Center setup command that installs, verifies, and launches pairing through Shizuku");
        Button pair = button("Manual pairing fallback", 15, "Open the manual pairing dialog only if Shizuku launch is unavailable");
        Button refresh = button("Refresh checks", 15, "Refresh installed package checks");
        Button diagnostics = button("Copy readiness JSON shape", 15, "Copy the readiness contract used by the Termux probe");

        panel.addView(termux, matchHeight(dp(52)));
        panel.addView(shizuku, matchHeight(dp(52)));
        panel.addView(setup, matchHeight(dp(52)));
        panel.addView(copyProbe, matchHeight(dp(52)));
        panel.addView(pair, matchHeight(dp(52)));
        panel.addView(refresh, matchHeight(dp(52)));
        panel.addView(diagnostics, matchHeight(dp(52)));

        ScrollView scroll = new ScrollView(this);
        scroll.addView(panel, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));
        scroll.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                Math.max(dp(420), getResources().getDisplayMetrics().heightPixels - dp(130))));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Enable Shizuku Automation")
                .setView(scroll)
                .setNegativeButton("Close", null)
                .create();
        termux.setOnClickListener(v -> openPackageOrUrl(TERMUX_PACKAGE, TERMUX_FDROID_URL));
        shizuku.setOnClickListener(v -> openPackageOrUrl(SHIZUKU_PACKAGE, SHIZUKU_DOWNLOAD_URL));
        setup.setOnClickListener(v -> openUrl(SHIZUKU_SETUP_URL));
        copyProbe.setOnClickListener(v -> {
            copyToClipboard("Home Center Shizuku setup", shizukuAutomationTermuxCommand());
            Toast.makeText(this, "Termux setup command copied.", Toast.LENGTH_SHORT).show();
        });
        pair.setOnClickListener(v -> {
            dialog.dismiss();
            showTermuxPairingDialog();
        });
        refresh.setOnClickListener(v -> status.setText(shizukuAutomationStatusText()));
        diagnostics.setOnClickListener(v -> {
            copyToClipboard("Home Center readiness JSON", shizukuAutomationReadinessContract());
            Toast.makeText(this, "Readiness JSON shape copied.", Toast.LENGTH_SHORT).show();
        });
        dialog.show();
    }

    private String shizukuAutomationStatusText() {
        boolean termuxInstalled = packageInstalled(TERMUX_PACKAGE);
        boolean shizukuInstalled = packageInstalled(SHIZUKU_PACKAGE);
        StringBuilder builder = new StringBuilder();
        builder.append("Checking device\n");
        builder.append(termuxInstalled ? "OK " : "Needs ").append("Termux app").append(termuxInstalled ? " installed" : " from F-Droid or official GitHub releases").append("\n");
        builder.append(shizukuInstalled ? "OK " : "Needs ").append("Shizuku app").append(shizukuInstalled ? " installed" : " installed and started").append("\n");
        builder.append("Termux packages: verified by the copied Termux command\n");
        builder.append("Codex package: @mmmbuto/codex-cli-termux verified by Termux\n");
        builder.append("rish bridge: verified by Termux with a harmless id probe\n");
        builder.append("Home Center pairing: Shizuku launches the pairing approval automatically after readiness is green");
        return builder.toString();
    }

    private String shizukuAutomationTermuxCommand() {
        return "cd /storage/emulated/0/Documents/GodotProjects/home-center && sh tools/home_center_shizuku_setup_probe.sh --install-approved --install-codex-approved --auto-pair";
    }

    private String shizukuAutomationReadinessContract() {
        try {
            JSONObject root = new JSONObject();
            root.put("status", "ready | blocked | partial");
            root.put("termux", new JSONObject()
                    .put("installed", true)
                    .put("source_ok", true)
                    .put("packages_ok", true));
            root.put("codex", new JSONObject()
                    .put("installed", true)
                    .put("package", "@mmmbuto/codex-cli-termux")
                    .put("home_center_runner_ok", true));
            root.put("shizuku", new JSONObject()
                    .put("installed", true)
                    .put("service_running", true)
                    .put("authorized", true));
            root.put("rish", new JSONObject()
                    .put("installed", true)
                    .put("probe_ok", true));
            root.put("automation_probe", new JSONObject()
                    .put("package_inspection_ok", true)
                    .put("foreground_inspection_ok", true));
            root.put("human_actions_required", new JSONArray());
            root.put("blockers", new JSONArray());
            root.put("diagnostics_path", "generated/shizuku_setup/home_center_shizuku_readiness.json");
            return root.toString(2);
        } catch (Exception ex) {
            return "{}";
        }
    }

    private boolean packageInstalled(String packageName) {
        try {
            getPackageManager().getPackageInfo(packageName, 0);
            return true;
        } catch (Exception ex) {
            return false;
        }
    }

    private void openPackageOrUrl(String packageName, String fallbackUrl) {
        Intent launch = getPackageManager().getLaunchIntentForPackage(packageName);
        if (launch != null) {
            startActivity(launch);
            return;
        }
        openUrl(fallbackUrl);
    }

    private void openUrl(String url) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            startActivity(intent);
        } catch (ActivityNotFoundException ex) {
            copyToClipboard("Home Center setup URL", url);
            Toast.makeText(this, "No browser available. URL copied.", Toast.LENGTH_LONG).show();
        }
    }

    private void copyToClipboard(String label, String text) {
        ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        if (clipboard != null) {
            clipboard.setPrimaryClip(ClipData.newPlainText(label, text));
        }
    }

    private void connectGoogleToolsFromShell() {
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (account != null && hasAllGoogleToolScopes(account)) {
            showLoginShellEvent("Refreshing cloud Google token...");
            exchangeGoogleServerAuthCode(account);
            appendStatus("Google tools already approved. Refreshing cloud token.");
            return;
        }
        if (account != null && firebaseAuth != null && firebaseAuth.getCurrentUser() != null) {
            showLoginShellEvent("Opening Google tool permission approval...");
            appendStatus("Requesting Google tool permissions.");
            requestGoogleToolPermissions(account);
            return;
        }
        showLoginShellEvent("Opening Google sign-in...");
        startGoogleSignIn();
    }

    private void showLoginShellEvent(String message) {
        if (loginShellEventView != null && message != null && !message.trim().isEmpty()) {
            loginShellEventView.setText(message.trim());
            loginShellEventView.setTextColor(message.toLowerCase(Locale.US).contains("fail") || message.toLowerCase(Locale.US).contains("need") ? COLOR_DANGER : COLOR_ACCENT);
        }
    }

    private void toggleLegacyChatVisible() {
        setChatVisible(!legacyChatVisible, "toggle_button");
    }

    private void setChatVisible(boolean visible, String reason) {
        legacyChatVisible = visible;
        if (visible) {
            clearStalePendingWorkForChat(reason);
        }
        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putBoolean(KEY_LEGACY_CHAT_VISIBLE, legacyChatVisible)
                .apply();
        updateLoginShellVisibility();
    }

    private void clearStalePendingWorkForChat(String reason) {
        pendingAgentTurnAfterGoogleReconnect = "";
        pendingToolConfirmation = null;
        LocalLog.info("agent", "chat_open_cleared_pending_work reason=" + shortMessage(reason));
    }

    private void updateLoginShellVisibility() {
        if (chatScroll != null) {
            chatScroll.setVisibility(legacyChatVisible ? View.VISIBLE : View.GONE);
        }
        if (composeRow != null) {
            composeRow.setVisibility(legacyChatVisible ? View.VISIBLE : View.GONE);
        }
        if (bottomPanel != null) {
            bottomPanel.setVisibility(legacyChatVisible ? View.VISIBLE : View.GONE);
        }
        if (legacyChatToggleButton != null) {
            legacyChatToggleButton.setText(legacyChatVisible ? "Hide chat" : "Open chat");
        }
        if (conversationDrawerButton != null) {
            conversationDrawerButton.setVisibility(legacyChatVisible ? View.VISIBLE : View.GONE);
        }
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
        help.setText("Secondary controls and diagnostics. Google login is the primary surface.");
        help.setTextSize(14);
        help.setTextColor(COLOR_SECONDARY);
        help.setPadding(0, 0, 0, dp(10));
        panel.addView(help, matchWrap());

        Button shizukuAutomation = button("Enable Shizuku Automation", 16, "Install and verify Termux, Codex, Shizuku, and rish automation");
        Button termuxPair = button("Pair Termux Codex", 16, "Approve a Termux Codex pairing code for Home Center tools");
        Button household = button("Household and list", 16, "Set household bucket and default list");
        Button ticktick = button("TickTick token", 16, "Set TickTick fallback token");
        Button cartReview = button("Walmart cart review", 16, "Import a Walmart cart review bundle");
        Button cartHelper = button("Cart helper settings", 16, "Open Android accessibility settings for the cart helper");
        Button diagnostics = button("Check cart helper", 16, "Check whether the cart helper is installed and enabled");
        Button driveCheck = button("Check Google Drive", 16, "Check whether Home Center can list Google Drive files");
        Button usage = button("Usage dashboard", 16, "Show AI and tool spend by user");
        Button netrunner = button("Netrunner browser", 16, "Open the secondary browser tool");
        Button compact = button("Compact chat", 16, "Compact the current chat history");

        panel.addView(shizukuAutomation, matchHeight(dp(56)));
        panel.addView(termuxPair, matchHeight(dp(56)));
        panel.addView(household, matchHeight(dp(52)));
        panel.addView(ticktick, matchHeight(dp(52)));
        panel.addView(cartReview, matchHeight(dp(52)));
        panel.addView(cartHelper, matchHeight(dp(52)));
        panel.addView(diagnostics, matchHeight(dp(52)));
        panel.addView(driveCheck, matchHeight(dp(52)));
        panel.addView(usage, matchHeight(dp(52)));
        panel.addView(netrunner, matchHeight(dp(52)));
        panel.addView(compact, matchHeight(dp(52)));

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(false);
        int menuMaxHeight = Math.max(dp(360), getResources().getDisplayMetrics().heightPixels - dp(140));
        scroll.addView(panel, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));
        scroll.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                menuMaxHeight));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Home Center menu")
                .setView(scroll)
                .setNegativeButton("Close", null)
                .create();
        shizukuAutomation.setOnClickListener(v -> {
            dialog.dismiss();
            showShizukuAutomationSetup();
        });
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
        termuxPair.setOnClickListener(v -> {
            dialog.dismiss();
            showShizukuAutomationSetup();
        });
        usage.setOnClickListener(v -> {
            dialog.dismiss();
            showUsageDashboard();
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

    private void showUsageDashboard() {
        if (openAiAgentClient == null || !openAiAgentClient.isConfigured()) {
            showAssistantMessage("Usage dashboard requires the Home Center gateway.");
            return;
        }
        if (!hasSignedInHomeUser()) {
            showAssistantMessage("Sign in with Google first to view usage.");
            startGoogleSignIn();
            return;
        }
        String bucket = bucketValue();
        if (bucket.isEmpty()) {
            showAssistantMessage("Select a household bucket before opening usage.");
            return;
        }
        FirebaseUser user = firebaseAuth == null ? null : firebaseAuth.getCurrentUser();
        if (user == null) {
            showAssistantMessage("Sign in with Google first to view usage.");
            return;
        }
        setBusy(true);
        setStatus("Loading usage...");
        user.getIdToken(false)
                .addOnSuccessListener(token -> executor.execute(() -> {
                    try {
                        JSONObject summary = openAiAgentClient.usageSummary(token.getToken(), bucket, 7);
                        main.post(() -> {
                            setBusy(false);
                            showUsageDashboardDialog(summary);
                        });
                    } catch (Exception ex) {
                        main.post(() -> {
                            setBusy(false);
                            showAssistantMessage("Could not load usage dashboard: " + shortMessage(ex.getMessage()));
                        });
                    }
                }))
                .addOnFailureListener(ex -> {
                    setBusy(false);
                    showAssistantMessage("Could not verify Google sign-in: " + shortMessage(ex.getMessage()));
                });
    }

    private void showUsageDashboardDialog(JSONObject summary) {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(18), dp(10), dp(18), dp(4));
        TextView body = new TextView(this);
        body.setTextColor(COLOR_TEXT);
        body.setTextSize(15);
        body.setText(usageDashboardText(summary));
        panel.addView(body, matchWrap());
        new AlertDialog.Builder(this)
                .setTitle("Usage dashboard")
                .setView(panel)
                .setNegativeButton("Close", null)
                .show();
    }

    private String usageDashboardText(JSONObject summary) {
        if (summary == null || !summary.optBoolean("ok", false)) {
            return "Usage is unavailable: " + (summary == null ? "no response" : firstNonEmpty(summary.optString("detail", ""), summary.optString("error", ""), "", "unknown error"));
        }
        JSONObject totals = summary.optJSONObject("totals");
        JSONArray users = summary.optJSONArray("users");
        JSONArray providers = summary.optJSONArray("providers");
        StringBuilder builder = new StringBuilder();
        builder.append("Range: ").append(summary.optString("startDay", "")).append(" to ").append(summary.optString("endDay", "")).append("\n\n");
        builder.append("Total: $").append(formatMoney(totals == null ? 0 : totals.optDouble("costUsd", 0))).append("\n");
        builder.append("Calls: ").append(totals == null ? 0 : totals.optInt("calls", 0)).append("\n");
        builder.append("Tokens: ").append(totals == null ? 0 : totals.optInt("totalTokens", 0)).append("\n");
        int unpriced = totals == null ? 0 : totals.optInt("unpricedEvents", 0);
        if (unpriced > 0) {
            builder.append("Unpriced events: ").append(unpriced).append("\n");
        }
        builder.append("\nBy provider\n");
        if (providers == null || providers.length() == 0) {
            builder.append("No usage recorded yet.\n");
        } else {
            for (int i = 0; i < providers.length(); i++) {
                JSONObject row = providers.optJSONObject(i);
                if (row == null) continue;
                builder.append("- ").append(row.optString("provider", "unknown"))
                        .append(": $").append(formatMoney(row.optDouble("costUsd", 0)))
                        .append(" · ").append(row.optInt("calls", 0)).append(" calls");
                if (row.optInt("unpricedEvents", 0) > 0) {
                    builder.append(" · ").append(row.optInt("unpricedEvents", 0)).append(" unpriced");
                }
                builder.append("\n");
            }
        }
        builder.append("\nBy user\n");
        if (users == null || users.length() == 0) {
            builder.append("No user usage recorded yet.\n");
        } else {
            for (int i = 0; i < users.length(); i++) {
                JSONObject row = users.optJSONObject(i);
                if (row == null) continue;
                builder.append("- ").append(firstNonEmpty(row.optString("email", ""), row.optString("uid", ""), "", "unknown"))
                        .append(": $").append(formatMoney(row.optDouble("costUsd", 0)))
                        .append(" · OpenAI $").append(formatMoney(row.optDouble("openAiCostUsd", 0)))
                        .append(" · Google/tool $").append(formatMoney(row.optDouble("googleCostUsd", 0)))
                        .append("\n");
            }
        }
        String note = summary.optString("note", "").trim();
        if (!note.isEmpty()) {
            builder.append("\n").append(note);
        }
        return builder.toString().trim();
    }

    private String formatMoney(double value) {
        return String.format(Locale.US, "%.4f", value);
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
        if (tryHandleLocalCommand(clean)) {
            return;
        }
        sendAgentTurn(clean);
    }

    private boolean tryHandleLocalCommand(String raw) {
        if (tryHandleChatSurfaceCommand(raw)) {
            return true;
        }
        if (tryHandleDocumentReaderCommand(raw)) {
            return true;
        }
        Command command = CommandParser.parse(raw);
        if (command == null || Command.UNKNOWN.equals(command.action)) {
            return false;
        }
        if (!isSafeLocalCommand(command, raw)) {
            LocalLog.info("ai_cost", "local_command_passthrough action=" + command.action);
            return false;
        }
        LocalLog.info("ai_cost", "local_command_bypass action=" + command.action + " openaiCalls=0");
        rememberAgentTrace("local_command_bypass", -1, raw, "openai_calls_0", command.action);
        switch (command.action) {
            case Command.ADD_LIST_ITEM:
                addListItem(command);
                return true;
            case Command.READ_LIST:
                readList(command.listName);
                return true;
            case Command.NEXT_ITEM:
                speakNextItem();
                return true;
            case Command.PREVIOUS_ITEM:
                speakPreviousItem();
                return true;
            case Command.MARK_DONE:
                markCurrentDone();
                return true;
            case Command.REMOVE_LIST_ITEM:
                removeListItem(command);
                return true;
            case Command.CREATE_LIST:
                createList(command);
                return true;
            case Command.SET_PREFERENCE:
                savePreference(command);
                return true;
            case Command.SET_STORE_TARGET:
                saveStoreTarget(command);
                return true;
            case Command.READ_PREFERENCES:
                readGroceryPreferences(command.listName);
                return true;
            case Command.BUILD_CART:
                buildWalmartCartDraft(command.listName);
                return true;
            case Command.SET_HOTSPOT:
                showAssistantMessage("Hotspot control is not available from Home Center yet.");
                return true;
            default:
                return false;
        }
    }

    private boolean isSafeLocalCommand(Command command, String raw) {
        String lower = raw == null ? "" : raw.toLowerCase(Locale.US);
        String listName = command.listName == null ? "" : command.listName.toLowerCase(Locale.US);
        boolean namesList = lower.contains(" list")
                || lower.contains("shopping")
                || lower.contains("grocery")
                || lower.contains("groceries")
                || lower.contains("walmart")
                || "shopping".equals(listName)
                || "grocery".equals(listName)
                || "groceries".equals(listName);
        switch (command.action) {
            case Command.NEXT_ITEM:
            case Command.PREVIOUS_ITEM:
            case Command.MARK_DONE:
            case Command.CREATE_LIST:
            case Command.SET_PREFERENCE:
            case Command.SET_STORE_TARGET:
            case Command.READ_PREFERENCES:
            case Command.BUILD_CART:
            case Command.SET_HOTSPOT:
                return true;
            case Command.ADD_LIST_ITEM:
            case Command.READ_LIST:
            case Command.REMOVE_LIST_ITEM:
                return namesList;
            default:
                return false;
        }
    }



    private boolean tryHandleChatSurfaceCommand(String raw) {
        String lower = raw == null ? "" : raw.trim().toLowerCase(Locale.US).replaceAll("\\s+", " ");
        if (lower.isEmpty()) {
            return false;
        }
        if (lower.equals("show chat")
                || lower.equals("open chat")
                || lower.equals("show home center chat")
                || lower.equals("open home center chat")
                || lower.equals("start chat")
                || lower.equals("bring up chat")
                || lower.equals("launch chat")
                || lower.equals("show assistant chat")
                || lower.equals("open assistant chat")
                || lower.equals("show legacy chat")
                || lower.equals("open legacy chat")) {
            setChatVisible(true, "local_chat_command");
            showAssistantMessage("Chat is open.");
            return true;
        }
        if (lower.equals("hide chat")
                || lower.equals("close chat")
                || lower.equals("hide home center chat")
                || lower.equals("close home center chat")
                || lower.equals("hide legacy chat")
                || lower.equals("close legacy chat")) {
            setChatVisible(false, "local_chat_command");
            showAssistantMessage("Chat is hidden.");
            return true;
        }
        if (lower.equals("toggle chat") || lower.equals("toggle home center chat") || lower.equals("toggle legacy chat")) {
            setChatVisible(!legacyChatVisible, "local_chat_command");
            showAssistantMessage(legacyChatVisible ? "Chat is open." : "Chat is hidden.");
            return true;
        }
        return false;
    }

    private boolean tryHandleDocumentReaderCommand(String raw) {
        String clean = raw == null ? "" : raw.trim();
        String lower = clean.toLowerCase(Locale.US).replaceAll("\\s+", " ").trim();
        if (lower.isEmpty()) {
            return false;
        }
        if (lower.equals("stop reading") || lower.equals("stop document") || lower.equals("stop reader")) {
            stopDocumentReader("stopped");
            return true;
        }
        if (lower.equals("close") || lower.equals("close document") || lower.equals("close reader") || lower.equals("close document reader")) {
            closeDocumentReaderView("closed");
            return true;
        }
        if (lower.equals("pause reading") || lower.equals("pause document") || lower.equals("pause reader")) {
            pauseDocumentReader();
            return true;
        }
        if (lower.equals("download voice") || lower.equals("download document voice") || lower.equals("save voice file")) {
            downloadDocumentVoice();
            return true;
        }
        if (lower.equals("resume reading") || lower.equals("continue reading") || lower.equals("play document") || lower.equals("play with brian") || lower.equals("resume document")) {
            resumeDocumentReader();
            return true;
        }
        if ((lower.equals("next") || lower.equals("next chunk") || lower.equals("next section")) && activeDocumentReader != null) {
            moveDocumentReader(1);
            return true;
        }
        if ((lower.equals("previous") || lower.equals("previous chunk") || lower.equals("previous section") || lower.equals("back")) && activeDocumentReader != null) {
            moveDocumentReader(-1);
            return true;
        }
        if (lower.equals("read last document") || lower.equals("read last google doc") || lower.equals("read the last document")) {
            readLastDriveDocument();
            return true;
        }
        String query = extractDocumentReaderQuery(clean, lower);
        if (!query.isEmpty()) {
            String directFileId = extractGoogleDocFileId(query);
            if (!directFileId.isEmpty()) {
                readDocumentById(directFileId, "Google Doc from provided link", "provided Google Doc");
                return true;
            }
            startDocumentReaderSearch(query);
            return true;
        }
        return false;
    }

    private String extractDocumentReaderQuery(String original, String lower) {
        String[] prefixes = new String[]{
                "please read google doc ",
                "read google doc ",
                "please read google document ",
                "read google document ",
                "please read doc ",
                "read doc ",
                "please read document ",
                "read document "
        };
        for (String prefix : prefixes) {
            if (lower.startsWith(prefix)) {
                return original.substring(Math.min(original.length(), prefix.length())).trim();
            }
        }
        return "";
    }

    private String extractGoogleDocFileId(String query) {
        String clean = query == null ? "" : query.trim();
        if (clean.isEmpty()) {
            return "";
        }
        java.util.regex.Matcher docMatcher = java.util.regex.Pattern
                .compile("(?:docs\\.google\\.com/document/d/|/d/)([A-Za-z0-9_.-]{8,220})")
                .matcher(clean);
        if (docMatcher.find()) {
            return docMatcher.group(1);
        }
        String bare = clean.replaceAll("[^A-Za-z0-9_.-]", "").trim();
        if (bare.matches("[A-Za-z0-9_.-]{20,220}") && (bare.contains("_") || bare.contains("-"))) {
            return bare;
        }
        return "";
    }

    private void startDocumentReaderSearch(String query) {
        if (busy) {
            appendStatus("Finish the current request first.");
            return;
        }
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (!hasAllGoogleToolScopes(account)) {
            pendingAgentTurnAfterGoogleReconnect = "read google doc " + query;
            showAssistantMessage("Google needs one more approval before I can read Docs. I am opening Google permission approval now, then I will continue this request.");
            requestGoogleToolPermissions(account);
            return;
        }
        setBusy(true);
        setStatus("Searching Google Docs...");
        executor.execute(() -> {
            try {
                JSONObject searchArgs = new JSONObject()
                        .put("query", query)
                        .put("pageSize", 5);
                JSONObject search = googleDriveClient.runTool("docs.search", searchArgs, account);
                if (!search.optBoolean("ok", false)) {
                    handleDocumentReaderFailure("docs.search", search, query);
                    return;
                }
                JSONArray files = search.optJSONArray("files");
                if (files == null || files.length() == 0) {
                    main.post(() -> {
                        setBusy(false);
                        showAssistantMessage("I could not find a Google Doc matching " + query + ".");
                    });
                    return;
                }
                JSONObject file = selectDocumentReaderFile(files, query);
                readDocumentReaderFile(file, query, account, false);
            } catch (Exception ex) {
                main.post(() -> {
                    setBusy(false);
                    showAssistantMessage("I could not start the Google Doc reader: " + shortMessage(ex.getMessage()));
                });
            }
        });
    }

    private JSONObject selectDocumentReaderFile(JSONArray files, String query) {
        String normalizedQuery = query == null ? "" : query.trim().toLowerCase(Locale.US);
        JSONObject first = files.optJSONObject(0);
        for (int i = 0; i < files.length(); i++) {
            JSONObject file = files.optJSONObject(i);
            if (file == null) {
                continue;
            }
            String name = file.optString("name", "").trim().toLowerCase(Locale.US);
            if (name.equals(normalizedQuery) || name.contains(normalizedQuery)) {
                return file;
            }
        }
        return first == null ? new JSONObject() : first;
    }

    private void readLastDriveDocument() {
        if (lastDriveDocumentId == null || lastDriveDocumentId.trim().isEmpty()) {
            showAssistantMessage("I do not have a last Google Doc in this conversation yet.");
            return;
        }
        readDocumentById(lastDriveDocumentId, lastDriveDocumentName, "last document");
    }

    private void readDocumentById(String fileId, String name, String queryLabel) {
        readDocumentById(fileId, name, queryLabel, false);
    }

    private void readDocumentById(String fileId, String name, String queryLabel, boolean autoPlay) {
        if (busy) {
            appendStatus("Finish the current request first.");
            return;
        }
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (!hasAllGoogleToolScopes(account)) {
            pendingAgentTurnAfterGoogleReconnect = "read last document";
            showAssistantMessage("Google needs one more approval before I can read Docs. I am opening Google permission approval now, then I will continue this request.");
            requestGoogleToolPermissions(account);
            return;
        }
        setBusy(true);
        setStatus("Reading Google Doc...");
        setDriveBrowserStatus("Reading " + safeDisplayName(name) + "...", false);
        LocalLog.info("doc_audio", "drive_narrate_clicked fileId=" + shortMessage(fileId) + " autoPlay=" + autoPlay);
        executor.execute(() -> {
            try {
                JSONObject file = new JSONObject()
                        .put("id", fileId == null ? "" : fileId.trim())
                        .put("name", name == null ? "" : name.trim());
                readDocumentReaderFile(file, queryLabel, account, autoPlay);
            } catch (Exception ex) {
                main.post(() -> {
                    setBusy(false);
                    setDriveBrowserStatus("Could not read that Google Doc: " + shortMessage(ex.getMessage()), true);
                    showAssistantMessage("I could not read that Google Doc: " + shortMessage(ex.getMessage()));
                });
            }
        });
    }

    private void readDocumentReaderFile(JSONObject file, String queryLabel, GoogleSignInAccount account, boolean autoPlay) throws Exception {
        String fileId = file == null ? "" : file.optString("id", "").trim();
        if (fileId.isEmpty()) {
            main.post(() -> {
                setBusy(false);
                showAssistantMessage("I found a Google Doc result, but it did not include a file id.");
            });
            return;
        }
        JSONObject readArgs = new JSONObject()
                .put("fileId", fileId)
                .put("name", file == null ? "" : file.optString("name", ""));
        JSONObject read = googleDriveClient.runTool("docs.read", readArgs, account);
        if (!read.optBoolean("ok", false)) {
            handleDocumentReaderFailure("docs.read", read, queryLabel);
            return;
        }
        updateWorkingMemoryFromToolResult("docs.read", readArgs, read);
        JSONObject readFile = read.optJSONObject("file");
        if (readFile == null) {
            readFile = file == null ? new JSONObject() : file;
        }
        String content = read.optString("content", "");
        refreshDriveCharacterRegistryForAccount(account);
        JSONObject finalFile = readFile;
        main.post(() -> {
            setBusy(false);
            beginDocumentReader(finalFile, content, autoPlay);
        });
    }

    private void handleDocumentReaderFailure(String toolName, JSONObject result, String query) {
        main.post(() -> {
            setBusy(false);
            if (isGoogleToolAuthFailure(result)) {
                pendingAgentTurnAfterGoogleReconnect = query == null ? "" : "read google doc " + query;
                showAssistantMessage("Google needs one more approval before I can read that document. I am opening Google permission approval now.");
                requestGoogleToolPermissions(GoogleSignIn.getLastSignedInAccount(this));
                return;
            }
            showAssistantMessage("I could not read that Google Doc: " + shortMessage(result == null ? "unknown error" : firstNonEmpty(result.optString("detail", ""), result.optString("error", ""), "", "unknown error")));
        });
    }

    private void beginDocumentReader(JSONObject file, String content) {
        beginDocumentReader(file, content, false);
    }

    private void replaceActiveDocumentReader(String reason) {
        if (activeDocumentReader != null) {
            activeDocumentReader.cancelRequested = true;
            activeDocumentReader.renderRequested = false;
            activeDocumentReader.downloadRequested = false;
            activeDocumentReader.playbackRequested = false;
            activeDocumentReader.paused = true;
            activeDocumentReader.status = reason == null ? "replaced" : reason;
        }
        stopSpeechPlayback();
        activeDocumentReader = null;
        setBusy(false);
        refreshDriveReaderPlayer();
    }

    private void beginDocumentReader(JSONObject file, String content, boolean autoPlay) {
        String text = content == null ? "" : content.trim();
        if (text.isEmpty()) {
            setDriveBrowserStatus("That Google Doc is empty.", true);
            showAssistantMessage("That Google Doc is empty, so there is nothing to read aloud.");
            return;
        }
        MarkdownNarrationDocument narrationDocument = compileDriveMarkdownNarration(text);
        activeDocumentReader = new DocumentReaderState(file, text, narrationDocument);
        activeDocumentReader.applySpeechProfile(driveSpeechProvider, driveSpeechModelId, driveNarratorVoiceName, driveDialogueVoiceName, driveNotesVoiceName, driveSpeechProfileKey(), true);
        ingestStructuredDocumentSpeakers(activeDocumentReader, text);
        materializeVoiceSplitPlan(activeDocumentReader);
        lastDriveDocumentId = activeDocumentReader.fileId;
        lastDriveDocumentName = activeDocumentReader.name;
        ensureGoogleDocAudioEntry(activeDocumentReader);
        if (!activeDocumentReader.playbackRestoredFromManifest) {
            resetDriveReaderPlaybackForNewContent(activeDocumentReader);
        }
        activeDocumentReader.status = driveReaderReadyStatus(activeDocumentReader);
        refreshDriveReaderPlayer();
        appendDocumentReaderArtifact(activeDocumentReader);
        if (autoPlay) {
            activeDocumentReader.playbackRequested = true;
            activeDocumentReader.paused = false;
            activeDocumentReader.previewOnlyPlayback = false;
            setDriveBrowserStatus("Reading title and preparing " + activeDocumentReader.name + ".", false);
            playDocumentTitleIntroThenContinue(activeDocumentReader);
        } else {
            appendStatus("Indexed " + activeDocumentReader.name + ". Use Render to save the audio artifact.");
        }
    }

    private void refreshActiveReaderSpeechProfileForRegistryChange(String reason) {
        if (activeDocumentReader == null) return;
        configureReaderSpeechProfile(activeDocumentReader, true);
        materializeVoiceSplitPlan(activeDocumentReader);
        activeDocumentReader.withClearedAudioEntry();
        LocalLog.info("doc_audio", "doc_audio_profile_invalidated reason=" + firstNonEmpty(reason, "registry_changed") + " profile=" + activeDocumentReader.speechProfileKey);
    }

    private void ingestStructuredDocumentSpeakers(DocumentReaderState reader, String documentText) {
        if (reader == null) return;
        StringBuilder candidateText = new StringBuilder(documentText == null ? "" : documentText);
        if (reader.chunks != null) for (String chunk : reader.chunks) candidateText.append('\n').append(chunk == null ? "" : chunk);
        List<CandidateSpeakerProfile> candidates = CandidateSpeakerProfile.extract(candidateText.toString(), reader.fileId, reader.name);
        if (candidates.isEmpty()) return;
        CharacterVoiceRegistry.MergeResult merged = driveCharacterRegistry.mergeCandidates(candidates, driveVoiceCatalog);
        if (merged.added <= 0) return;
        try {
            JSONObject registryJson = driveCharacterRegistry.toJson();
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_DRIVE_CHARACTER_REGISTRY_JSON, registryJson.toString()).apply();
            LocalLog.info("doc_audio", "speaker_profile_registry_ingested_no_reader_reset entries=" + driveCharacterRegistry.size() + " names=" + merged.names);
            setDriveBrowserStatus("Ingested " + merged.added + " speaker profile" + (merged.added == 1 ? "" : "s") + " from " + reader.name + ".", false);
            appendStatus("Drive Narrate ingested speakers: " + merged.names + ". Defaults are overrideable in Speech.");
            persistDriveCharacterRegistryDocument();
        } catch (Exception ex) {
            LocalLog.warn("doc_audio", "speaker_profile_cache_failed " + shortMessage(ex.getMessage()));
        }
    }

    private void persistDriveCharacterRegistryDocument() {
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (account == null || googleDriveClient == null || driveCharacterRegistryDocId == null || driveCharacterRegistryDocId.trim().isEmpty()) return;
        executor.execute(() -> {
            try {
                JSONObject args = new JSONObject()
                        .put("fileId", driveCharacterRegistryDocId)
                        .put("name", DRIVE_CHARACTER_REGISTRY_TITLE)
                        .put("body", driveCharacterRegistry.toMarkdown());
                JSONObject update = googleDriveClient.runTool("docs.update", args, account);
                if (!update.optBoolean("ok", false)) {
                    LocalLog.warn("doc_audio", "speaker_profile_registry_update_failed error=" + shortMessage(update.optString("error", "")) + " detail=" + shortMessage(update.optString("detail", "")));
                    return;
                }
                LocalLog.info("doc_audio", "speaker_profile_registry_updated entries=" + driveCharacterRegistry.size());
            } catch (Exception ex) {
                LocalLog.warn("doc_audio", "speaker_profile_registry_update_failed " + shortMessage(ex.getMessage()));
            }
        });
    }

    private void createDriveVoiceSplitFolderStructure() {
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if (!ensureDriveVoiceSplitAccess(account)) return;
        setBusy(true);
        setDriveBrowserStatus("Creating narration rendering Drive workspace.", false);
        executor.execute(() -> {
            try {
                JSONObject workspace = ensureDriveVoiceSplitWorkspace(account);
                String rootId = workspace.optString("rootId", "");
                String readmeId = ensureVoiceSplitReadmeDoc(account, rootId);
                LocalLog.info("doc_audio", "voice_split_workspace_ready rootId=" + shortMessage(rootId) + " readmeId=" + shortMessage(readmeId));
                main.post(() -> {
                    setBusy(false);
                    setDriveBrowserStatus("Narration rendering workspace is ready in Drive.", false);
                    showAssistantMessage("Created or found " + DRIVE_VOICE_SPLIT_FOLDER_TITLE + ". Render follows the narrator/character plan without creating plan documents.");
                });
            } catch (Exception ex) {
                main.post(() -> {
                    setBusy(false);
                    setDriveBrowserStatus("Narration workspace failed: " + shortMessage(ex.getMessage()), true);
                    showAssistantMessage("Narration workspace failed: " + shortMessage(ex.getMessage()));
                });
            }
        });
    }

    private void prepareVoiceSplitRenderingPlanForActiveDocument() {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null) {
            showAssistantMessage("Open a Google Doc first, then render the document.");
            return;
        }
        buildVoiceSplitRenderingPlan(reader, true);
    }

    private void buildVoiceSplitRenderingPlan(DocumentReaderState reader, boolean announce) {
        if (reader == null) return;
        try {
            materializeVoiceSplitPlan(reader);
            JSONObject plan = voiceSplitRenderingPlanJson(reader);
            JSONArray sections = plan.optJSONArray("sections");
            LocalLog.info("doc_audio", "voice_split_plan_materialized_no_doc fileId=" + shortMessage(reader.fileId)
                    + " textHash=" + reader.textHash
                    + " sections=" + (sections == null ? 0 : sections.length()));
            if (announce) {
                setDriveBrowserStatus("Narration plan is ready for " + reader.name + " without creating a document.", false);
                showAssistantMessage("Narration plan is ready in the render manifest. No Google Doc was created.");
            }
        } catch (Exception ex) {
            LocalLog.warn("doc_audio", "voice_split_plan_materialize_failed_no_doc fileId=" + shortMessage(reader.fileId) + " detail=" + shortMessage(ex.getMessage()));
            if (announce) {
                setDriveBrowserStatus("Narration plan failed: " + shortMessage(ex.getMessage()), true);
                showAssistantMessage("Narration plan failed before render. No Google Doc was created.");
            }
        }
    }

    private boolean ensureDriveVoiceSplitAccess(GoogleSignInAccount account) {
        if (account == null || googleDriveClient == null) {
            showAssistantMessage("Sign in with Google first, then create the narration workspace.");
            startGoogleSignIn();
            return false;
        }
        if (!hasAllGoogleToolScopes(account)) {
            showAssistantMessage("Approve Google Drive and Docs tools first, then create the narration workspace.");
            requestGoogleToolPermissions(account);
            return false;
        }
        return true;
    }

    private JSONObject ensureDriveVoiceSplitWorkspace(GoogleSignInAccount account) throws Exception {
        JSONObject root = ensureDriveFolder(account, DRIVE_VOICE_SPLIT_FOLDER_TITLE, "");
        String rootId = root.optString("id", "");
        JSONArray folders = new JSONArray();
        for (String name : DRIVE_VOICE_SPLIT_SUBFOLDERS) {
            JSONObject folder = ensureDriveFolder(account, name, rootId);
            folders.put(folder);
        }
        return new JSONObject()
                .put("rootId", rootId)
                .put("rootName", root.optString("name", DRIVE_VOICE_SPLIT_FOLDER_TITLE))
                .put("folders", folders);
    }

    private JSONObject ensureDriveFolder(GoogleSignInAccount account, String name, String parentId) throws Exception {
        String existingId = findDriveItemId(account, name, "application/vnd.google-apps.folder", parentId);
        if (!existingId.isEmpty()) return new JSONObject().put("id", existingId).put("name", name).put("reused", true).put("parentId", parentId == null ? "" : parentId);
        JSONObject create = googleDriveClient.runTool("drive.create_folder", new JSONObject().put("name", name).put("parentId", parentId == null ? "" : parentId), account);
        if (!create.optBoolean("ok", false)) throw new IOException(firstNonEmpty(create.optString("detail", ""), create.optString("error", ""), "folder create failed"));
        JSONObject file = create.optJSONObject("file");
        if (file == null || file.optString("id", "").trim().isEmpty()) throw new IOException("folder create returned no id");
        return new JSONObject().put("id", file.optString("id", "")).put("name", file.optString("name", name)).put("reused", false).put("parentId", parentId == null ? "" : parentId);
    }

    private String findDriveItemId(GoogleSignInAccount account, String name, String mimeType, String parentId) throws Exception {
        JSONObject args = new JSONObject().put("query", name).put("mimeType", mimeType).put("pageSize", 10);
        if (parentId != null && !parentId.trim().isEmpty()) args.put("parentId", parentId.trim());
        JSONObject search = googleDriveClient.runTool("drive.search", args, account);
        if (!search.optBoolean("ok", false)) return "";
        JSONArray files = search.optJSONArray("files");
        if (files == null) return "";
        for (int i = 0; i < files.length(); i++) {
            JSONObject file = files.optJSONObject(i);
            if (file == null || !name.equalsIgnoreCase(file.optString("name", "").trim())) continue;
            if (parentId != null && !parentId.trim().isEmpty() && !jsonArrayContainsTrimmed(file.optJSONArray("parents"), parentId.trim())) continue;
            return file.optString("id", "").trim();
        }
        return "";
    }

    private String ensureVoiceSplitReadmeDoc(GoogleSignInAccount account, String rootId) throws Exception {
        String existingId = findDriveItemId(account, DRIVE_VOICE_SPLIT_README_TITLE, "application/vnd.google-apps.document", rootId);
        if (!existingId.isEmpty()) return existingId;
        JSONObject created = googleDriveClient.runTool("docs.create", new JSONObject()
                .put("title", DRIVE_VOICE_SPLIT_README_TITLE)
                .put("folderId", rootId)
                .put("body", voiceSplitFolderContractText()), account);
        if (!created.optBoolean("ok", false)) throw new IOException(firstNonEmpty(created.optString("detail", ""), created.optString("error", ""), "readme create failed"));
        JSONObject file = created.optJSONObject("file");
        return file == null ? "" : file.optString("id", "");
    }

    private String folderIdFromWorkspace(JSONObject workspace, String name) {
        JSONArray folders = workspace == null ? null : workspace.optJSONArray("folders");
        if (folders == null) return workspace == null ? "" : workspace.optString("rootId", "");
        for (int i = 0; i < folders.length(); i++) {
            JSONObject folder = folders.optJSONObject(i);
            if (folder != null && name.equalsIgnoreCase(folder.optString("name", ""))) return folder.optString("id", "");
        }
        return workspace.optString("rootId", "");
    }

    private JSONObject voiceSplitRenderingPlanJson(DocumentReaderState reader) throws Exception {
        if (reader != null && reader.voiceSplitAssignments.isEmpty()) materializeVoiceSplitPlan(reader);
        JSONArray speakers = new JSONArray();
        JSONArray sections = new JSONArray();
        for (int i = 0; reader != null && i < reader.chunkCount(); i++) {
            CharacterVoiceRule rule = characterRuleForSection(reader, i);
            SectionVoiceAssignment assignment = reader.voiceSplitAssignmentAt(i);
            String providerAlias = assignment == null ? activeSpeechVoiceName(reader, i) : assignment.voiceName;
            boolean voiceResolved = !providerAlias.isEmpty() || (assignment != null && !assignment.voiceId.isEmpty());
            if (!speakerArrayContains(speakers, rule.characterId)) {
                speakers.put(new JSONObject()
                        .put("speakerId", rule.characterId)
                        .put("displayName", rule.characterName)
                        .put("role", firstNonEmpty(rule.narrationRole, "narrator"))
                        .put("registryVoiceAlias", rule.voiceAlias)
                        .put("providerVoiceAlias", providerAlias)
                        .put("voiceResolved", voiceResolved)
                        .put("acousticDirection", rule.acousticDirection)
                        .put("matchTags", new JSONArray(rule.matchTags)));
            }
            String text = reader.chunks.get(i);
            sections.put(new JSONObject()
                    .put("index", i)
                    .put("label", sectionLabelAt(reader, i))
                    .put("capstone", voiceSplitCapstoneForText(text))
                    .put("sectionHash", sectionHashAt(reader, i))
                    .put("speakerId", rule.characterId)
                    .put("speaker", rule.characterName)
                    .put("role", speechRoleForSection(reader, i))
                    .put("registryVoiceAlias", rule.voiceAlias)
                    .put("providerVoiceAlias", providerAlias)
                    .put("voiceResolved", voiceResolved)
                    .put("fallbackRoleVoice", activeSpeechVoiceName(reader, i))
                    .put("status", voiceResolved ? "ready_for_cloud_render" : "needs_voice_assignment")
                    .put("textPreview", previewForPlan(text)));
        }
        return new JSONObject()
                .put("type", "voice_split_rendering_plan")
                .put("version", 1)
                .put("status", "draft_agent_breakdown")
                .put("workflowBoundary", "separate_voice_split_rendering_workspace")
                .put("cloudsideGeneration", true)
                .put("noAutomaticVoiceInterpolation", true)
                .put("sourceDocument", new JSONObject()
                        .put("fileId", reader.fileId)
                        .put("title", reader.name)
                        .put("modifiedTime", reader.modifiedTime)
                        .put("textHash", reader.textHash)
                        .put("charCount", reader.charCount)
                        .put("chunkCount", reader.chunkCount()))
                .put("registry", new JSONObject()
                        .put("title", DRIVE_CHARACTER_REGISTRY_TITLE)
                        .put("documentId", driveCharacterRegistryDocId)
                        .put("fingerprint", driveCharacterRegistryFingerprint()))
                .put("speech", new JSONObject()
                        .put("provider", driveSpeechProvider)
                        .put("modelId", driveSpeechModelId)
                        .put("roleDefaults", new JSONObject()
                                .put("narrator", driveNarratorVoiceName)
                                .put("dialogue", driveDialogueVoiceName)
                                .put("notes", driveNotesVoiceName)))
                .put("speakers", speakers)
                .put("sections", sections);
    }

    private String voiceSplitRenderingPlanMarkdown(DocumentReaderState reader, JSONObject plan) {
        StringBuilder out = new StringBuilder();
        out.append("# Narration Plan - ").append(reader == null ? "Google Doc" : reader.name).append("\n\n");
        out.append("This is the first-stage agent breakdown for character-specific cloud rendering. It does not change the simple Drive Narrate role-default player.\n\n");
        out.append("Source document: ").append(reader == null ? "" : reader.name).append("\n");
        out.append("Text hash: ").append(reader == null ? "" : reader.textHash).append("\n");
        out.append("Registry: ").append(DRIVE_CHARACTER_REGISTRY_TITLE).append("\n");
        out.append("Provider/model: ").append(driveSpeechProvider).append(" / ").append(driveSpeechModelId).append("\n\n");
        out.append("## Required Next Step\n\n");
        out.append("Resolve every section with status needs_voice_assignment before character-specific chunk generation. Do not auto-interpolate voices; use explicit registry aliases or selected role defaults.\n\n");
        out.append("## Plan JSON\n\n```json\n");
        try {
            out.append(plan == null ? "{}" : plan.toString(2));
        } catch (Exception ex) {
            out.append(plan == null ? "{}" : plan.toString());
        }
        out.append("\n```\n");
        return out.toString();
    }

    private String voiceSplitFolderContractText() {
        StringBuilder out = new StringBuilder();
        out.append("# Voice Split Rendering - Folder Contract\n\n");
        out.append("Drive Narrate renders materialize this plan in the audio manifest path without creating Google Docs. The workspace is only for explicit saved artifacts.\n\n");
        out.append("## Folders\n\n");
        for (String folder : DRIVE_VOICE_SPLIT_SUBFOLDERS) out.append("- ").append(folder).append("\n");
        out.append("\n## Flow\n\n");
        out.append("1. Intake keeps source documents or links.\n");
        out.append("2. Split Plans stores the agent breakdown: narrators, character ids, registry voice aliases, section hashes, capstones, and unresolved voices.\n");
        out.append("3. Rendered Chunks stores cloud-generated per-section audio after the plan is resolved.\n");
        out.append("4. Final Mixes stores assembled audio artifacts.\n");
        out.append("5. Voice Registry Snapshots stores the registry fingerprint used for a render.\n");
        out.append("6. Failed Runs keeps aborted provider runs without losing partial sections.\n\n");
        out.append("## Rendering Rules\n\n");
        out.append("- Generation is cloudside. Browser playback is only a player for saved audio.\n");
        out.append("- The existing Home Drive Character Voice Orientation Registry is the source of character voice assignment.\n");
        out.append("- No separate voice interpolation happens here. Unknown characters are marked unresolved until a voice is explicitly assigned.\n");
        out.append("- Section hashes, capstones, speaker ids, provider voice aliases, and audio paths must be preserved in the plan/manifest.\n");
        return out.toString();
    }

    private boolean speakerArrayContains(JSONArray speakers, String speakerId) {
        String clean = speakerId == null ? "" : speakerId.trim();
        for (int i = 0; speakers != null && i < speakers.length(); i++) {
            JSONObject speaker = speakers.optJSONObject(i);
            if (speaker != null && clean.equals(speaker.optString("speakerId", ""))) return true;
        }
        return false;
    }

    private boolean jsonArrayContainsTrimmed(JSONArray array, String value) {
        String clean = value == null ? "" : value.trim();
        for (int i = 0; array != null && i < array.length(); i++) {
            if (clean.equals(array.optString(i, "").trim())) return true;
        }
        return false;
    }

    private String sectionLabelAt(DocumentReaderState reader, int index) {
        if (reader != null && reader.sectionLabels != null && index >= 0 && index < reader.sectionLabels.size()) {
            String label = reader.sectionLabels.get(index);
            if (label != null && !label.trim().isEmpty()) return label.trim();
        }
        return "section " + (index + 1);
    }

    private String sectionHashAt(DocumentReaderState reader, int index) {
        if (reader != null && reader.sectionHashes != null && index >= 0 && index < reader.sectionHashes.size()) {
            String hash = reader.sectionHashes.get(index);
            if (hash != null && !hash.trim().isEmpty()) return hash.trim();
        }
        return reader == null || index < 0 || index >= reader.chunkCount() ? "" : stableTextHash(reader.chunks.get(index));
    }

    private String voiceSplitCapstoneForText(String text) {
        String clean = (text == null ? "" : text).trim().toLowerCase(Locale.US);
        if (clean.startsWith("title:")) return "title";
        if (clean.startsWith("section:")) return "section";
        if (clean.startsWith("subsection:")) return "subsection";
        if (clean.startsWith("[speaker:") || clean.startsWith("[voice:")) return "dialogue";
        if (clean.startsWith("list item:")) return "list";
        if (clean.startsWith("quoted note:") || clean.startsWith("code:")) return "note";
        if (clean.startsWith("break.")) return "break";
        return "body";
    }

    private String previewForPlan(String text) {
        String clean = text == null ? "" : text.replaceAll("\\s+", " ").trim();
        return clean.length() > 220 ? clean.substring(0, 220) + "..." : clean;
    }

    private String safeDriveTitle(String value) {
        String clean = value == null ? "Google Doc" : value.replaceAll("[\\r\\n]+", " ").replaceAll("[\\\\/:*?\"<>|]+", " ").replaceAll("\\s+", " ").trim();
        return clean.isEmpty() ? "Google Doc" : clean;
    }

    private void resetDriveReaderPlaybackForNewContent(DocumentReaderState reader) {
        if (reader == null) return;
        reader.paused = true;
        reader.playbackRequested = false;
        reader.previewOnlyPlayback = false;
        reader.currentIndex = 0;
        reader.playbackTargetKind = "section";
        reader.playbackTargetIndex = 0;
        reader.playbackOffsetBytes = 0L;
        reader.activePlaybackStartOffsetBytes = 0L;
        reader.activePlaybackWrittenBytes = 0L;
        reader.activePlaybackPcmBytes = 0L;
        reader.activePlaybackSampleRate = activeTargetSampleRate(reader);
        if (driveReaderPlayerSeekBar != null && !driveReaderUserSeeking) {
            driveReaderPlayerSeekBar.setProgress(0);
        }
    }

    private MarkdownNarrationDocument compileDriveMarkdownNarration(String text) {
        return MarkdownNarrationDocument.compile(text, DOC_READER_FIRST_CHUNK_CHARS, DOC_READER_TARGET_CHARS, DOC_READER_MIN_CHARS);
    }

    private List<String> chunkDocumentReaderText(String text) {
        return compileDriveMarkdownNarration(text).chunks;
    }

    private void appendDocumentReaderArtifact(DocumentReaderState reader) {
        if (reader == null) {
            return;
        }
        String summary = reader.summaryText();
        chatTurns.add(new ChatTurn("assistant", summary, reader.toMetadata()));
        trimChatTurns();
        recordTranscriptTurn("assistant", summary);
        appendDocumentReaderCard(reader, true);
    }

    private void renderChatTurn(ChatTurn turn) {
        if (turn != null && turn.metadata != null && "doc_reader_pair".equals(turn.metadata.optString("type", ""))) {
            appendDocumentReaderCard(DocumentReaderState.fromMetadata(turn.metadata), false);
            return;
        }
        appendChatBubble("assistant".equals(turn.role) ? "Home Center" : "You", turn == null ? "" : turn.text, turn != null && "user".equals(turn.role), false);
    }

    private void appendDocumentReaderCard(DocumentReaderState reader, boolean activateButtons) {
        if (chatLogContainer == null || reader == null) {
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
        title.setText("Google Doc reader");
        title.setTextSize(14);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(Color.parseColor("#5B4B2A"));
        card.addView(title, matchWrap());

        TextView source = new TextView(this);
        source.setText(reader.sourceLine());
        source.setTextSize(13);
        source.setTextColor(COLOR_TEXT);
        source.setPadding(0, dp(4), 0, dp(8));
        card.addView(source, matchWrap());

        TextView textVersion = new TextView(this);
        textVersion.setText("Text version: Drive snapshot " + reader.textHash + " | " + reader.charCount + " chars | chunk " + (reader.currentIndex + 1) + " of " + reader.chunkCount());
        textVersion.setTextSize(12);
        textVersion.setTypeface(Typeface.DEFAULT_BOLD);
        textVersion.setTextColor(COLOR_ACCENT);
        card.addView(textVersion, matchWrap());

        TextView excerpt = new TextView(this);
        excerpt.setText(reader.previewText());
        excerpt.setTextSize(14);
        excerpt.setTextColor(COLOR_TEXT);
        excerpt.setPadding(0, dp(6), 0, dp(10));
        card.addView(excerpt, matchWrap());

        TextView voiceVersion = new TextView(this);
        voiceVersion.setText("Voice version: " + reader.voiceProviderLabel() + " | Speech model: " + reader.speechModelId + " | Roles: " + reader.voiceSummary() + " | Status: " + reader.status);
        voiceVersion.setTextSize(12);
        voiceVersion.setTypeface(Typeface.DEFAULT_BOLD);
        voiceVersion.setTextColor(COLOR_PRIMARY);
        voiceVersion.setPadding(0, 0, 0, dp(8));
        card.addView(voiceVersion, matchWrap());

        chatLogContainer.addView(card);
        chatLogContainer.post(this::scrollChatToBottom);
    }

    private Button readerControlButton(String label, Runnable action, boolean enabled) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextSize(11);
        button.setMinWidth(0);
        button.setMinHeight(0);
        button.setPadding(dp(4), dp(6), dp(4), dp(6));
        button.setEnabled(enabled);
        button.setTextColor(enabled ? COLOR_TEXT : COLOR_SECONDARY);
        button.setBackgroundColor(enabled ? COLOR_CARD : COLOR_SURFACE);
        button.setOnClickListener(v -> action.run());
        return button;
    }

    private String driveReaderReadyStatus(DocumentReaderState reader) {
        if (reader == null) return "ready";
        return countDownloadedSections(reader) > 0 ? "ready with cached audio" : "ready to render";
    }

    private void ensureGoogleDocAudioEntry(DocumentReaderState reader) {
        if (reader == null || reader.audioEntry != null || googleDocAudioLibrary == null) {
            return;
        }
        reader.audioEntry = googleDocAudioLibrary.ingest(reader.fileId, reader.name, reader.modifiedTime, reader.textHash, reader.charCount, reader.chunks, reader.sectionLabels, reader.sectionHashes, reader.speechProfileKey, driveSpeechProfileJson(reader.voiceSplitRenderingMode));
        JSONObject manifest = reader.audioEntry.readManifest();
        reader.downloadedSections = manifest.optInt("downloadedSections", countDownloadedSections(reader));
        restoreDocumentPlaybackPosition(reader, manifest);
        reader.status = driveReaderReadyStatus(reader);
    }

    private int countDownloadedSections(DocumentReaderState reader) {
        if (reader == null || reader.audioEntry == null) {
            return 0;
        }
        int count = 0;
        for (int i = 0; i < reader.chunkCount(); i++) {
            if (reader.audioEntry.isDownloaded(i)) {
                count += 1;
            }
        }
        return count;
    }

    private void restoreDocumentPlaybackPosition(DocumentReaderState reader, JSONObject manifest) {
        if (reader == null || manifest == null) return;
        JSONObject playback = manifest.optJSONObject("playback");
        if (playback == null || playback.length() == 0) {
            restorePartialRenderCheckpoint(reader, manifest);
            return;
        }
        reader.playbackRestoredFromManifest = true;
        int section = Math.max(0, Math.min(reader.chunkCount() - 1, playback.optInt("sectionIndex", reader.currentIndex)));
        applyRestoredPlaybackTarget(reader, section, playback.optLong("offsetBytes", 0L), firstNonEmpty(playback.optString("status", ""), "restored playback position"));
    }

    private void restorePartialRenderCheckpoint(DocumentReaderState reader, JSONObject manifest) {
        if (reader == null || reader.audioEntry == null) return;
        int downloaded = Math.max(manifest.optInt("downloadedSections", 0), countDownloadedSections(reader));
        if (downloaded <= 0) return;
        int firstMissing = firstMissingRenderedSection(reader);
        int section = firstMissing >= 0 ? firstMissing : Math.max(0, Math.min(reader.chunkCount() - 1, downloaded - 1));
        String status = firstMissing >= 0
                ? "restored partial render at section " + (section + 1)
                : "restored completed render at section " + (section + 1);
        applyRestoredPlaybackTarget(reader, section, 0L, status);
        persistDocumentPlaybackPosition(reader, status);
        LocalLog.info("doc_audio", "partial_render_checkpoint_restored fileId=" + shortMessage(reader.fileId) + " section=" + section + " downloaded=" + downloaded);
    }

    private int firstMissingRenderedSection(DocumentReaderState reader) {
        if (reader == null || reader.audioEntry == null) return -1;
        for (int i = 0; i < reader.chunkCount(); i++) {
            if (!reader.audioEntry.isDownloaded(i)) return i;
        }
        return -1;
    }

    private void applyRestoredPlaybackTarget(DocumentReaderState reader, int section, long offsetBytes, String status) {
        if (reader == null) return;
        int safeSection = Math.max(0, Math.min(reader.chunkCount() - 1, section));
        reader.playbackRestoredFromManifest = true;
        reader.currentIndex = safeSection;
        reader.playbackTargetKind = "section";
        reader.playbackTargetIndex = safeSection;
        File cachedSection = reader.audioEntry == null ? null : reader.audioEntry.sectionFile(safeSection);
        long pcmBytes = cachedSection != null && cachedSection.exists() ? Math.max(0L, cachedSection.length() - 44L) : 0L;
        reader.activePlaybackPcmBytes = pcmBytes;
        reader.activePlaybackSampleRate = activeTargetSampleRate(reader);
        reader.activePlaybackStartOffsetBytes = 0L;
        reader.activePlaybackWrittenBytes = 0L;
        reader.playbackOffsetBytes = Math.max(0L, Math.min(pcmBytes, offsetBytes));
        reader.paused = true;
        reader.playbackRequested = false;
        reader.status = firstNonEmpty(status, "restored playback position");
    }

    private void persistDocumentPlaybackPosition(DocumentReaderState reader, String status) {
        if (reader == null || reader.audioEntry == null) return;
        long total = visiblePlayheadPcmBytes(reader);
        long visible = visiblePlayheadOffsetBytes(reader, total);
        reader.audioEntry.markPlaybackPosition(reader.playbackTargetIndex, reader.playbackOffsetBytes, visible, status);
    }

    private void playDocumentReader() {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null) {
            showAssistantMessage("No Google Doc is indexed yet.");
            return;
        }
        configureReaderSpeechProfile(reader, true);
        materializeVoiceSplitPlan(reader);
        ensureGoogleDocAudioEntry(reader);
        reader.playbackTargetKind = "section";
        reader.playbackTargetIndex = reader.currentIndex;
        reader.playbackRequested = true;
        reader.cancelRequested = false;
        reader.previewOnlyPlayback = false;
        reader.paused = false;
        refreshDriveReaderPlayer();
        playOrDownloadCurrentSection(true);
    }

    private void downloadDocumentVoice() {
        renderDocumentAudio();
    }

    private void configureReaderSpeechProfile(DocumentReaderState reader, boolean voiceSplitRendering) {
        if (reader == null) return;
        String nextKey = driveSpeechProfileKey(voiceSplitRendering);
        if (!nextKey.equals(reader.speechProfileKey) || reader.voiceSplitRenderingMode != voiceSplitRendering) {
            reader.applySpeechProfile(driveSpeechProvider, driveSpeechModelId, driveNarratorVoiceName, driveDialogueVoiceName, driveNotesVoiceName, nextKey, voiceSplitRendering);
            reader.audioEntry = null;
            reader.downloadedSections = 0;
            reader.exportedWavPath = "";
            reader.playbackOffsetBytes = 0L;
            reader.playbackTargetIndex = Math.max(0, Math.min(reader.chunkCount() - 1, reader.currentIndex));
        }
    }

    private String voiceSplitUnresolvedSummary(DocumentReaderState reader) {
        List<String> unresolved = new ArrayList<>();
        for (int i = 0; reader != null && i < reader.chunkCount(); i++) {
            CharacterVoiceRule rule = characterRuleForSection(reader, i);
            String alias = resolvedProviderVoiceAlias(rule);
            if (alias.isEmpty()) {
                String label = rule == null ? "section " + (i + 1) : rule.characterName + " section " + (i + 1);
                unresolved.add(label);
                if (unresolved.size() >= 4) break;
            }
        }
        if (unresolved.isEmpty()) return "";
        String suffix = unresolved.size() >= 4 ? ", ..." : "";
        return TextUtils.join(", ", unresolved) + suffix;
    }

    private void renderDocumentAudio() {
        renderDocumentAudio(false);
    }

    private void rerenderDocumentAudio() {
        renderDocumentAudio(true);
    }

    private void renderDocumentAudio(boolean forceRerender) {
        renderDocumentAudio(forceRerender, true);
    }

    private void renderDocumentAudio(boolean forceRerender, boolean voiceSplitRendering) {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null) {
            showAssistantMessage("No Google Doc is indexed yet.");
            return;
        }
        configureReaderSpeechProfile(reader, true);
        materializeVoiceSplitPlan(reader);
        ensureGoogleDocAudioEntry(reader);
        final boolean renderUsesVoicePlan = true;
        reader.cancelRequested = false;
        if (forceRerender) {
            stopHostedSpeechPlayback("rerender_document_audio");
            reader.playbackRequested = false;
            reader.downloadRequested = false;
            reader.paused = true;
            reader.exportedWavPath = "";
            reader.audioEntry.clearRenderedSections();
            reader.downloadedSections = 0;
            LocalLog.info("doc_audio", "doc_audio_rerender_requested fileId=" + shortMessage(reader.fileId) + " textHash=" + reader.textHash + " profile=" + reader.speechProfileKey);
        }
        reader.renderRequested = true;
        reader.downloadRequested = false;
        reader.status = forceRerender ? "rerendering audio artifact with registry voices" : "rendering audio artifact with registry voices";
        reader.audioEntry.markRendering(true, true);
        refreshDriveReaderPlayer();
        setDriveBrowserStatus((forceRerender ? "Rerendering and saving " : "Rendering and saving ") + reader.name + " with registry voices.", false);
        appendStatus((forceRerender ? "Rerendering and saving " : "Rendering and saving ") + reader.name + ". You can listen or leave; the audio artifact remains the work product.");
        documentRenderExecutor.execute(() -> {
            for (int i = 0; i < reader.chunkCount(); i++) {
                if (reader != activeDocumentReader || reader.cancelRequested || !reader.renderRequested) break;
                if (!reader.audioEntry.isDownloaded(i)) {
                    boolean generated = generateDocumentSection(reader, i, false);
                    if (!generated) {
                        break;
                    }
                }
                if (reader != activeDocumentReader || reader.cancelRequested || !reader.renderRequested) break;
                reader.downloadedSections = countDownloadedSections(reader);
                reader.status = forceRerender ? "rerendering audio artifact with registry voices" : "rendering audio artifact with registry voices";
                main.post(() -> { if (reader == activeDocumentReader) refreshDriveReaderPlayer(); });
            }
            reader.downloadedSections = countDownloadedSections(reader);
            reader.renderRequested = false;
            String savedWavPath = "";
            String exportError = "";
            if (reader.downloadedSections >= reader.chunkCount()) {
                try {
                    savedWavPath = exportRenderedDocumentWav(reader, forceRerender || renderUsesVoicePlan, renderUsesVoicePlan);
                    reader.exportedWavPath = savedWavPath;
                    reader.status = "rendered audio artifact complete";
                } catch (Exception ex) {
                    exportError = shortMessage(ex.getMessage());
                    reader.status = "render complete; WAV export failed";
                    LocalLog.warn("doc_audio", "document_wav_export_failed fileId=" + shortMessage(reader.fileId) + " textHash=" + reader.textHash + " detail=" + exportError);
                }
            } else if (reader.status == null || !reader.status.startsWith("render blocked,")) {
                reader.status = "render incomplete";
            }
            if (reader.audioEntry != null) {
                if (reader.downloadedSections >= reader.chunkCount() && exportError.isEmpty()) {
                    reader.audioEntry.markRenderComplete();
                } else {
                    reader.audioEntry.markRendering(false);
                }
            }
            String finalSavedWavPath = savedWavPath;
            String finalExportError = exportError;
            main.post(() -> {
                if (reader != activeDocumentReader) return;
                refreshDriveReaderPlayer();
                boolean danger = reader.downloadedSections < reader.chunkCount() || !finalExportError.isEmpty();
                setDriveBrowserStatus(reader.status + ": " + reader.name + (finalSavedWavPath.isEmpty() ? "." : ". Saved WAV: " + finalSavedWavPath), danger);
                appendStatus(reader.status + ": " + reader.name + (finalSavedWavPath.isEmpty() ? "." : ". Saved WAV: " + finalSavedWavPath));
                if (!finalExportError.isEmpty()) appendStatus("WAV export failed: " + finalExportError);
            });
        });
    }

    private void reconcileCachedRenderedDocuments() {
        if (googleDocAudioLibrary == null) return;
        int exported = 0;
        int failed = 0;
        for (GoogleDocAudioLibrary.Entry entry : googleDocAudioLibrary.completedEntriesFromManifests()) {
            try {
                exportRenderedEntryWav(entry, entry.title, entry.textHash, entry.sectionCount, entry.fileId);
                exported += 1;
            } catch (Exception ex) {
                failed += 1;
                LocalLog.warn("doc_audio", "cached_document_reconcile_failed fileId=" + shortMessage(entry.fileId) + " textHash=" + entry.textHash + " detail=" + shortMessage(ex.getMessage()));
            }
        }
        if (exported > 0 || failed > 0) {
            int finalExported = exported;
            int finalFailed = failed;
            main.post(() -> appendStatus("Recovered cached document WAVs: " + finalExported + " saved" + (finalFailed > 0 ? ", " + finalFailed + " failed" : "") + "."));
        }
    }

    private String exportRenderedDocumentWav(DocumentReaderState reader) throws IOException {
        return exportRenderedDocumentWav(reader, false);
    }

    private String exportRenderedDocumentWav(DocumentReaderState reader, boolean forceNewFile) throws IOException {
        return exportRenderedDocumentWav(reader, forceNewFile, false);
    }

    private String exportRenderedDocumentWav(DocumentReaderState reader, boolean forceNewFile, boolean voiceSplitRendering) throws IOException {
        if (reader == null || reader.audioEntry == null) throw new IOException("no rendered document audio");
        String exportTitle = reader.name;
        return exportRenderedEntryWav(reader.audioEntry, exportTitle, reader.textHash, reader.chunkCount(), reader.fileId, !forceNewFile);
    }

    private String exportRenderedEntryWav(GoogleDocAudioLibrary.Entry entry, String title, String textHash, int sectionCount, String fileId) throws IOException {
        return exportRenderedEntryWav(entry, title, textHash, sectionCount, fileId, true);
    }

    private String exportRenderedEntryWav(GoogleDocAudioLibrary.Entry entry, String title, String textHash, int sectionCount, String fileId, boolean reuseExisting) throws IOException {
        if (entry == null) throw new IOException("no rendered document audio");
        int safeSectionCount = Math.max(1, sectionCount);
        int sampleRate = GoogleDocAudioLibrary.DEFAULT_SAMPLE_RATE;
        long pcmBytes = 0L;
        for (int i = 0; i < safeSectionCount; i++) {
            File section = entry.sectionFile(i);
            if (section == null || !section.exists() || section.length() <= 44L) {
                throw new IOException("section " + (i + 1) + " is not rendered");
            }
            pcmBytes += Math.max(0L, section.length() - 44L);
        }
        if (pcmBytes <= 0L) throw new IOException("rendered audio is empty");
        String hash = firstNonEmpty(textHash, String.valueOf(System.currentTimeMillis()), "", "audio");
        String fileName = safeFileName(title) + "-" + hash + (reuseExisting ? "" : "-" + System.currentTimeMillis()) + ".wav";
        long expectedBytes = 44L + pcmBytes;
        String existingPath = reuseExisting ? existingRenderedDownloadPath(fileName, expectedBytes) : "";
        if (!existingPath.isEmpty()) {
            LocalLog.info("doc_audio", "document_wav_export_reused fileId=" + shortMessage(fileId) + " textHash=" + textHash + " path=" + existingPath + " bytes=" + expectedBytes);
            return existingPath;
        }
        String existingNamedPath = reuseExisting ? existingRenderedDownloadPath(fileName, -1L) : "";
        if (!existingNamedPath.isEmpty()) {
            LocalLog.warn("doc_audio", "document_wav_export_existing_name_reused fileId=" + shortMessage(fileId) + " textHash=" + textHash + " path=" + existingNamedPath + " expectedBytes=" + expectedBytes);
            return existingNamedPath;
        }
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, fileName);
        values.put(MediaStore.Downloads.MIME_TYPE, "audio/wav");
        values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/audio/");
        Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IOException("MediaStore insert returned null");
        try (OutputStream output = getContentResolver().openOutputStream(uri, "w")) {
            if (output == null) throw new IOException("MediaStore output stream returned null");
            output.write(wavHeaderBytes(sampleRate, pcmBytes));
            for (int i = 0; i < safeSectionCount; i++) {
                copyWavPcm(entry.sectionFile(i), output);
            }
        }
        String path = "Downloads/HomeCenter/audio/" + fileName;
        LocalLog.info("doc_audio", "document_wav_exported fileId=" + shortMessage(fileId) + " textHash=" + textHash + " path=" + path + " pcmBytes=" + pcmBytes);
        return path;
    }

    private String existingRenderedDownloadPath(String fileName, long expectedBytes) {
        String relativePath = Environment.DIRECTORY_DOWNLOADS + "/HomeCenter/audio/";
        String[] projection = new String[]{MediaStore.Downloads.DISPLAY_NAME, MediaStore.Downloads.SIZE};
        String selection = MediaStore.Downloads.RELATIVE_PATH + "=? AND " + MediaStore.Downloads.DISPLAY_NAME + "=?";
        String[] args = new String[]{relativePath, fileName};
        try (Cursor cursor = getContentResolver().query(MediaStore.Downloads.EXTERNAL_CONTENT_URI, projection, selection, args, null)) {
            if (cursor == null) return "";
            while (cursor.moveToNext()) {
                long size = cursor.isNull(1) ? -1L : cursor.getLong(1);
                if (expectedBytes <= 0L || size == expectedBytes) {
                    return "Downloads/HomeCenter/audio/" + fileName;
                }
            }
        } catch (Exception ex) {
            LocalLog.warn("doc_audio", "document_wav_existing_check_failed name=" + shortMessage(fileName) + " detail=" + shortMessage(ex.getMessage()));
        }
        return "";
    }

    private void copyWavPcm(File wav, OutputStream output) throws IOException {
        try (InputStream input = new BufferedInputStream(new FileInputStream(wav))) {
            long skipped = 0L;
            while (skipped < 44L) {
                long step = input.skip(44L - skipped);
                if (step <= 0L) {
                    if (input.read() == -1) throw new IOException("invalid wav header");
                    step = 1L;
                }
                skipped += step;
            }
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
        }
    }

    private byte[] wavHeaderBytes(int sampleRate, long pcmBytes) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(44);
        bytes.write(new byte[]{'R','I','F','F'});
        writeLeInt(bytes, 36L + Math.max(0L, pcmBytes));
        bytes.write(new byte[]{'W','A','V','E'});
        bytes.write(new byte[]{'f','m','t',' '});
        writeLeInt(bytes, 16L);
        writeLeShort(bytes, 1);
        writeLeShort(bytes, 1);
        writeLeInt(bytes, sampleRate);
        writeLeInt(bytes, sampleRate * 2L);
        writeLeShort(bytes, 2);
        writeLeShort(bytes, 16);
        bytes.write(new byte[]{'d','a','t','a'});
        writeLeInt(bytes, Math.max(0L, pcmBytes));
        return bytes.toByteArray();
    }

    private void writeLeInt(OutputStream output, long value) throws IOException {
        output.write((int) (value & 0xff));
        output.write((int) ((value >> 8) & 0xff));
        output.write((int) ((value >> 16) & 0xff));
        output.write((int) ((value >> 24) & 0xff));
    }

    private void writeLeShort(OutputStream output, int value) throws IOException {
        output.write(value & 0xff);
        output.write((value >> 8) & 0xff);
    }

    private String safeFileName(String value) {
        String clean = value == null ? "" : value.trim().replaceAll("[^A-Za-z0-9_.-]+", "-").replaceAll("^-|-$", "");
        if (clean.isEmpty()) clean = "google-doc-audio";
        return clean.length() > 80 ? clean.substring(0, 80) : clean;
    }

    private void playDocumentTitleIntroThenContinue(DocumentReaderState reader) {
        if (reader == null) return;
        configureReaderSpeechProfile(reader, true);
        materializeVoiceSplitPlan(reader);
        ensureGoogleDocAudioEntry(reader);
        if (reader.titleIntroPlayed) {
            playOrDownloadCurrentSection(true);
            return;
        }
        if (!shouldUseHostedSpeech()) {
            reader.titleIntroPlayed = true;
            playOrDownloadCurrentSection(true);
            return;
        }
        String titleText = readerTitleSpeech(reader.name);
        String utteranceId = "home_center_doc_title_" + System.currentTimeMillis();
        activeSpeechUtteranceId = utteranceId;
        requestSpeechFocus();
        long sequence = beginSpeechSequence("new_google_doc_title_intro");
        setSpeechPlaying(true);
        refreshDriveReaderPlayer();
        documentAudioExecutor.execute(() -> playDocumentTitleIntroStream(reader, titleText, utteranceId, sequence));
    }

    private void playDocumentTitleIntroStream(DocumentReaderState reader, String titleText, String utteranceId, long sequence) {
        HttpURLConnection connection = null;
        AudioTrack track = null;
        try {
            if (!isCurrentSpeechSequence(sequence)) return;
            connection = hostedSpeechClient.openSpeechStream(titleText, driveSpeechProvider, driveSpeechModelId, driveNarratorVoiceName, driveNarratorVoiceId, "narrator", "title", driveNarratorVoiceName, "");
            int sampleRate = hostedSpeechSampleRate(connection);
            track = createHostedSpeechTrack(sampleRate);
            synchronized (this) {
                if (!isCurrentSpeechSequence(sequence)) {
                    track.release();
                    return;
                }
                activeHostedSpeechTrack = track;
                track.play();
            }
            byte[] pcm = readSpeechPcm(connection.getInputStream(), sequence);
            long written = writePcmToTrack(track, pcm, sequence);
            waitForHostedSpeechPlaybackDrain(track, written, sampleRate, sequence);
            if (isCurrentSpeechSequence(sequence)) {
                main.post(() -> {
                    if (reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
                    reader.titleIntroPlayed = true;
                    finishSpeechPlaybackFor(utteranceId, "stream_complete");
                    playOrDownloadCurrentSection(true);
                });
            }
        } catch (Exception ex) {
            if (isCurrentSpeechSequence(sequence)) {
                main.post(() -> {
                    if (reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
                    reader.titleIntroPlayed = true;
                    LocalLog.warn("doc_audio", "title_intro_failed " + shortMessage(ex.getMessage()));
                    finishSpeechPlaybackFor(utteranceId, "hosted_speech_error");
                    playOrDownloadCurrentSection(true);
                });
            }
        } finally {
            releaseHostedTrackIfActive(track);
            if (connection != null) connection.disconnect();
        }
    }

    private void playDocumentAudioTarget(DocumentReaderState reader, String kind, int index, long offsetBytes) {
        if (reader == null) return;
        ensureGoogleDocAudioEntry(reader);
        File wav;
        int section = Math.max(0, Math.min(reader.chunkCount() - 1, index));
        if (reader.audioEntry == null || !reader.audioEntry.isDownloaded(section)) {
            appendStatus("That audio is not rendered yet.");
            return;
        }
        wav = reader.audioEntry.sectionFile(section);
        reader.currentIndex = section;
        reader.playbackTargetKind = "section";
        reader.playbackTargetIndex = section;
        long pcmBytes = wav == null || !wav.exists() ? 0L : Math.max(0L, wav.length() - 44L);
        long offset = Math.max(0L, Math.min(pcmBytes, offsetBytes));
        offset -= (offset & 1L);
        String utteranceId = "home_center_doc_audio_" + System.currentTimeMillis();
        activeSpeechUtteranceId = utteranceId;
        reader.utteranceId = utteranceId;
        reader.playbackRequested = true;
        reader.paused = false;
        reader.playbackOffsetBytes = offset;
        reader.playbackReconcileScheduled = false;
        reader.nextPlaybackReconcileAtMs = SystemClock.elapsedRealtime() + DOC_READER_FALSE_PLAYING_COOLDOWN_MS;
        reader.activePlaybackStartOffsetBytes = offset;
        reader.activePlaybackWrittenBytes = 0L;
        reader.activePlaybackPcmBytes = pcmBytes;
        reader.activePlaybackSampleRate = GoogleDocAudioLibrary.DEFAULT_SAMPLE_RATE;
        reader.status = "playing " + activeTargetLabel(reader);
        requestSpeechFocus();
        long sequence = beginSpeechSequence("new_google_doc_audio_playback");
        setSpeechPlaying(true);
        refreshDriveReaderPlayer();
        ensurePlaybackBufferAhead(reader);
        String label = "section=" + reader.playbackTargetIndex;
        final long playbackOffset = offset;
        documentAudioExecutor.execute(() -> playWavFile(wav, GoogleDocAudioLibrary.DEFAULT_SAMPLE_RATE, utteranceId, sequence, label, playbackOffset));
    }

    private void playWavFile(File wav, int sampleRate, String utteranceId, long sequence, String label, long offsetBytes) {
        AudioTrack track = null;
        try {
            track = createHostedSpeechTrack(sampleRate);
            synchronized (this) {
                if (!isCurrentSpeechSequence(sequence)) {
                    track.release();
                    return;
                }
                activeHostedSpeechTrack = track;
                track.play();
            }
            long written = writeWavPcmToTrack(track, wav, sequence, offsetBytes);
            waitForHostedSpeechPlaybackDrain(track, written, sampleRate, sequence);
            if (isCurrentSpeechSequence(sequence)) {
                long finalWritten = written;
                main.post(() -> {
                    LocalLog.info("doc_audio", "doc_audio_play_local label=" + label + " writtenBytes=" + finalWritten);
                    DocumentReaderState reader = activeDocumentReader;
                    if (reader != null && utteranceId.equals(reader.utteranceId)) {
                        reader.playbackOffsetBytes = Math.max(0L, Math.min(reader.activePlaybackPcmBytes, reader.activePlaybackStartOffsetBytes + finalWritten));
                        persistDocumentPlaybackPosition(reader, "played section");
                    }
                    refreshDriveReaderPlayer();
                    finishSpeechPlaybackFor(utteranceId, "stream_complete");
                });
            }
        } catch (Exception ex) {
            if (isCurrentSpeechSequence(sequence)) {
                main.post(() -> {
                    appendStatus("Could not play " + label + ": " + shortMessage(ex.getMessage()));
                    refreshDriveReaderPlayer();
                    finishSpeechPlaybackFor(utteranceId, "hosted_speech_error");
                });
            }
        } finally {
            releaseHostedTrackIfActive(track);
        }
    }

    private void restartDocumentPlaybackFromSavedPosition(DocumentReaderState reader, String reason) {
        if (reader == null || reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
        ensureGoogleDocAudioEntry(reader);
        if (reader.audioEntry != null) {
            int target = Math.max(0, Math.min(reader.chunkCount() - 1, reader.playbackTargetIndex));
            if (reader.audioEntry.isDownloaded(target)) {
                long offset = Math.max(0L, Math.min(activeTargetPcmBytes(reader), reader.playbackOffsetBytes));
                LocalLog.warn("doc_audio", "doc_audio_false_playing_restart fileId=" + shortMessage(reader.fileId)
                        + " section=" + target
                        + " offsetBytes=" + offset
                        + " reason=" + shortMessage(reason));
                playDocumentAudioTarget(reader, "section", target, offset);
                return;
            }
        }
        long total = visiblePlayheadPcmBytes(reader);
        if (total > 0L) {
            long visible = Math.max(0L, Math.min(Math.max(0L, total - 2L), visiblePlayheadOffsetBytes(reader, total)));
            LocalLog.warn("doc_audio", "doc_audio_false_playing_visible_restart fileId=" + shortMessage(reader.fileId)
                    + " visibleBytes=" + visible
                    + " totalBytes=" + total
                    + " reason=" + shortMessage(reason));
            playDocumentAudioAtVisibleOffset(reader, visible);
            return;
        }
        LocalLog.warn("doc_audio", "doc_audio_false_playing_buffer_restart fileId=" + shortMessage(reader.fileId)
                + " section=" + reader.playbackTargetIndex
                + " reason=" + shortMessage(reason));
        playOrDownloadCurrentSection(true);
    }

    private boolean isDocumentAudioPlaybackLive(DocumentReaderState reader) {
        if (reader == null || reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return false;
        if (!speechPlaying || reader.utteranceId == null || !reader.utteranceId.equals(activeSpeechUtteranceId)) return false;
        synchronized (this) {
            if (activeHostedSpeechTrack == null) return false;
            try {
                return activeHostedSpeechTrack.getPlayState() == AudioTrack.PLAYSTATE_PLAYING;
            } catch (Exception ignored) {
                return false;
            }
        }
    }

    private void reconcileDocumentPlaybackIfNeeded(DocumentReaderState reader, String reason) {
        if (reader == null || reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
        if (isDocumentAudioPlaybackLive(reader)) return;
        long now = SystemClock.elapsedRealtime();
        if (reader.playbackReconcileScheduled || reader.nextPlaybackReconcileAtMs > now) return;
        reader.playbackReconcileScheduled = true;
        reader.nextPlaybackReconcileAtMs = now + DOC_READER_FALSE_PLAYING_COOLDOWN_MS;
        LocalLog.warn("doc_audio", "doc_audio_false_playing_detected fileId=" + shortMessage(reader.fileId)
                + " section=" + reader.playbackTargetIndex
                + " downloaded=" + reader.downloadedSections
                + " reason=" + shortMessage(reason));
        main.postDelayed(() -> {
            reader.playbackReconcileScheduled = false;
            if (reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
            if (isDocumentAudioPlaybackLive(reader)) return;
            restartDocumentPlaybackFromSavedPosition(reader, reason);
        }, DOC_READER_FALSE_PLAYING_RECHECK_MS);
    }

    private void playOrDownloadCurrentSection(boolean allowDownload) {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null) {
            return;
        }
        configureReaderSpeechProfile(reader, true);
        materializeVoiceSplitPlan(reader);
        ensureGoogleDocAudioEntry(reader);
        int section = reader.currentIndex;
        reader.playbackTargetKind = "section";
        reader.playbackTargetIndex = Math.max(0, Math.min(reader.chunkCount() - 1, section));
        if (reader.audioEntry.isDownloaded(section)) {
            long offset = reader.playbackTargetIndex == section ? reader.playbackOffsetBytes : 0L;
            playDocumentAudioTarget(reader, "section", section, offset);
            return;
        }
        if (!allowDownload) {
            appendStatus("That audio is not rendered yet.");
            return;
        }
        reader.playbackOffsetBytes = 0L;
        persistDocumentPlaybackPosition(reader, "waiting for section render");
        refreshDriveReaderPlayer();
        setDriveBrowserStatus("Rendering audio for " + reader.name + " with " + activeSpeechVoiceLabel(reader, section) + ".", false);
        appendStatus("Rendering audio for " + reader.name + " with " + activeSpeechVoiceLabel(reader, section) + ".");
        documentAudioExecutor.execute(() -> generateDocumentSection(reader, section, true));
    }

    private void playDownloadedDocumentSection(DocumentReaderState reader, int sectionIndex) {
        if (reader == null || reader.audioEntry == null) return;
        reader.playbackTargetKind = "section";
        reader.playbackTargetIndex = Math.max(0, Math.min(reader.chunkCount() - 1, sectionIndex));
        reader.playbackOffsetBytes = 0L;
        playDocumentAudioTarget(reader, "section", reader.playbackTargetIndex, 0L);
    }

    private boolean generateDocumentSection(DocumentReaderState reader, int sectionIndex, boolean playAfterDownload) {
        HttpURLConnection connection = null;
        RandomAccessFile output = null;
        File part = null;
        long pcmBytes = 0L;
        int sampleRate = GoogleDocAudioLibrary.DEFAULT_SAMPLE_RATE;
        try {
            if (reader == null || reader.audioEntry == null || reader.cancelRequested || reader.audioEntry.isDownloaded(sectionIndex)) {
                if (reader != null && playAfterDownload) {
                    main.post(() -> {
                    if (reader == activeDocumentReader) {
                        long offset = reader.playbackTargetIndex == sectionIndex ? reader.playbackOffsetBytes : 0L;
                        playDocumentAudioTarget(reader, "section", sectionIndex, offset);
                    }
                });
                }
                return true;
            }
            if (reader != activeDocumentReader && playAfterDownload) return false;
            reader.audioEntry.markDownloading(sectionIndex);
            LocalLog.info("doc_audio", "doc_audio_download_start fileId=" + reader.fileId + " textHash=" + reader.textHash + " section=" + sectionIndex + " play=" + playAfterDownload);
            if (playAfterDownload) {
                main.post(() -> setDriveBrowserStatus("Rendering audio for " + reader.name + " with " + activeSpeechVoiceLabel(reader, sectionIndex) + ".", false));
            }
            CharacterVoiceRule voiceRule = characterRuleForSection(reader, sectionIndex);
            String speechRole = speechRoleForSection(reader, sectionIndex);
            reader.activeCharacterId = voiceRule.characterId;
            reader.activeVoiceAlias = activeSpeechVoiceName(reader, sectionIndex);
            reader.activeAcousticDirection = voiceRule.acousticDirection;
            connection = hostedSpeechClient.openSpeechStream(sectionSpeechText(reader, sectionIndex), driveSpeechProvider, driveSpeechModelId, activeSpeechVoiceName(reader, sectionIndex), activeSpeechVoiceId(reader, sectionIndex), speechRole, voiceRule.characterId, voiceRule.voiceAlias, voiceRule.acousticDirection);
            sampleRate = hostedSpeechSampleRate(connection);
            String resolvedVoiceName = hostedSpeechResolvedVoiceName(connection);
            String resolvedVoiceId = hostedSpeechResolvedVoiceId(connection);
            String requestedVoiceName = activeSpeechVoiceName(reader, sectionIndex);
            String requestedVoiceId = activeSpeechVoiceId(reader, sectionIndex);
            if ("cartesia".equals(driveSpeechProvider) && !requestedVoiceId.isEmpty() && !resolvedVoiceId.isEmpty() && !requestedVoiceId.equalsIgnoreCase(resolvedVoiceId)) {
                throw new IOException("cartesia_voice_id_mismatch requested=" + requestedVoiceName + ":" + requestedVoiceId + " resolved=" + resolvedVoiceName + ":" + resolvedVoiceId);
            }
            if (isLegacySkylarVoice(resolvedVoiceName, resolvedVoiceId) && !isLegacySkylarVoice(requestedVoiceName, requestedVoiceId)) {
                throw new IOException("cartesia_resolved_legacy_skylar_for_requested_voice requested=" + requestedVoiceName);
            }
            File wav = reader.audioEntry.sectionFile(sectionIndex);
            File parent = wav == null ? null : wav.getParentFile();
            if (parent != null && !parent.exists()) parent.mkdirs();
            part = new File(parent, wav.getName() + "." + SystemClock.elapsedRealtime() + "." + Thread.currentThread().getId() + ".part");
            output = new RandomAccessFile(part, "rw");
            output.setLength(0L);
            GoogleDocAudioLibrary.writeWavHeader(output, sampleRate, 0L);
            try (InputStream input = new BufferedInputStream(connection.getInputStream())) {
                byte[] buffer = new byte[8192];
                int read;
                while ((read = input.read(buffer)) != -1) {
                    output.write(buffer, 0, read);
                    pcmBytes += read;
                }
            }
            if ((pcmBytes & 1L) == 1L) {
                output.write(0);
                pcmBytes += 1L;
                LocalLog.warn("doc_audio", "padded_trailing_pcm_half_frame section=" + sectionIndex);
            }
            GoogleDocAudioLibrary.writeWavHeader(output, sampleRate, pcmBytes);
            output.close();
            output = null;
            if (wav.exists() && wav.length() > 44L) {
                long existingPcmBytes = Math.max(0L, wav.length() - 44L);
                if (part.exists() && !part.delete()) LocalLog.warn("doc_audio", "audio_cache_part_delete_failed path=" + shortMessage(part.getAbsolutePath()));
                reader.audioEntry.markDownloaded(sectionIndex, existingPcmBytes, sampleRate, voiceRule.characterId, requestedVoiceName, voiceRule.acousticDirection, resolvedVoiceName, resolvedVoiceId);
                LocalLog.info("doc_audio", "doc_audio_section_race_reused section=" + sectionIndex + " pcmBytes=" + existingPcmBytes);
            } else if (!part.renameTo(wav)) {
                if (wav.exists() && wav.length() > 44L) {
                    long existingPcmBytes = Math.max(0L, wav.length() - 44L);
                    if (part.exists() && !part.delete()) LocalLog.warn("doc_audio", "audio_cache_part_delete_failed path=" + shortMessage(part.getAbsolutePath()));
                    reader.audioEntry.markDownloaded(sectionIndex, existingPcmBytes, sampleRate, voiceRule.characterId, requestedVoiceName, voiceRule.acousticDirection, resolvedVoiceName, resolvedVoiceId);
                    LocalLog.info("doc_audio", "doc_audio_section_race_reused section=" + sectionIndex + " pcmBytes=" + existingPcmBytes);
                } else {
                    throw new IOException("could not finalize section audio");
                }
            } else {
                reader.audioEntry.markDownloaded(sectionIndex, pcmBytes, sampleRate, voiceRule.characterId, requestedVoiceName, voiceRule.acousticDirection, resolvedVoiceName, resolvedVoiceId);
            }
            reader.downloadedSections = countDownloadedSections(reader);
            main.post(() -> {
                if (reader == activeDocumentReader && !reader.cancelRequested) refreshDriveReaderPlayer();
            });
            if (playAfterDownload && reader.playbackRequested && !reader.paused) {
                main.post(() -> {
                    if (reader != activeDocumentReader) return;
                    setDriveBrowserStatus("Playing " + reader.name + " with " + activeSpeechVoiceLabel(reader, sectionIndex) + ".", false);
                    refreshDriveReaderPlayer();
                    playDownloadedDocumentSection(reader, sectionIndex);
                    ensurePlaybackBufferAhead(reader);
                });
            }
            return true;
        } catch (Exception ex) {
            if (reader != null && reader.audioEntry != null) {
                reader.audioEntry.markFailed(sectionIndex, shortMessage(ex.getMessage()));
                if (!playAfterDownload) {
                    String cause = speechFailureCause(ex);
                    reader.renderRequested = false;
                    reader.status = "render blocked, section " + (sectionIndex + 1) + " failed: " + cause;
                }
            }
            LocalLog.warn("doc_audio", "doc_audio_download_failed section=" + sectionIndex + " detail=" + shortMessage(ex.getMessage()));
            if (playAfterDownload) {
                main.post(() -> {
                    String cause = speechFailureCause(ex);
                    if (reader == activeDocumentReader && reader.playbackRequested && !reader.paused && !reader.cancelRequested) {
                        reader.status = "buffering; retrying section " + (sectionIndex + 1) + ": " + cause;
                        setDriveBrowserStatus(reader.status + ".", false);
                        refreshDriveReaderPlayer();
                        retryDocumentPlayback(reader, reader.status);
                    } else {
                        setDriveBrowserStatus("Hosted narration failed: " + cause + ".", true);
                        setStatus("Hosted narration failed: " + cause + ".");
                        setSpeechPlaying(false);
                        refreshDriveReaderPlayer();
                    }
                });
            }
            return false;
        } finally {
            if (output != null) {
                try { output.close(); } catch (Exception ignored) { }
            }
            if (part != null && part.exists() && (reader == null || reader.audioEntry == null || !reader.audioEntry.isDownloaded(sectionIndex))) {
                if (!part.delete()) LocalLog.warn("doc_audio", "audio_cache_part_delete_failed path=" + shortMessage(part.getAbsolutePath()));
            }
            if (connection != null) connection.disconnect();
        }
    }

    private void ensurePlaybackBufferAhead(DocumentReaderState reader) {
        if (reader == null || reader.audioEntry == null || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
        int start = Math.max(0, reader.playbackTargetIndex + 1);
        int end = Math.min(reader.chunkCount() - 1, reader.playbackTargetIndex + DOC_READER_PLAYBACK_BUFFER_CHUNKS);
        if (start > end) return;
        documentRenderExecutor.execute(() -> {
            for (int i = start; i <= end; i++) {
                if (reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
                if (reader.audioEntry != null && !reader.audioEntry.isDownloaded(i)) {
                    generateDocumentSection(reader, i, false);
                }
            }
        });
    }

    private void retryDocumentPlayback(DocumentReaderState reader, String reason) {
        if (reader == null || reader.playbackRetryScheduled) return;
        reader.playbackRetryScheduled = true;
        LocalLog.info("doc_audio", "doc_audio_playback_retry_scheduled fileId=" + shortMessage(reader.fileId) + " section=" + reader.playbackTargetIndex + " reason=" + shortMessage(reason));
        main.postDelayed(() -> {
            reader.playbackRetryScheduled = false;
            if (reader != activeDocumentReader || reader.paused || !reader.playbackRequested || reader.cancelRequested) return;
            playOrDownloadCurrentSection(true);
        }, DOC_READER_PLAYBACK_RETRY_DELAY_MS);
    }

    private String sectionSpeechText(DocumentReaderState reader, int sectionIndex) {
        if (reader == null || reader.chunks == null || reader.chunks.isEmpty()) return "";
        int safeIndex = Math.max(0, Math.min(reader.chunks.size() - 1, sectionIndex));
        return stripReaderMetadataForSpeech(stripVoiceTags(reader.chunks.get(safeIndex)));
    }

    private String stripReaderMetadataForSpeech(String text) {
        String clean = text == null ? "" : text.trim();
        if (clean.isEmpty()) return "";
        clean = clean.replaceAll("(?i)voice orientation\\s*:[^\\n.]*[\\n.]?", " ");
        clean = clean.replaceAll("(?i)acoustic direction\\s*:[^\\n.]*[\\n.]?", " ");
        clean = clean.replaceAll("(?i)rendering directive\\s*:[^\\n.]*[\\n.]?", " ");
        clean = clean.replaceAll("(?i)artificial voice pitch; satisfying acoustic distortion", " ");
        clean = clean.replaceAll("\\s+", " ").trim();
        return clean;
    }

    private void continueDocumentReaderAfterSpeech(String utteranceId, String reason) {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null || reader.paused || !utteranceId.equals(reader.utteranceId)) {
            return;
        }
        if (!"stream_complete".equals(reason)) {
            reader.playbackOffsetBytes = Math.max(0L, Math.min(reader.activePlaybackPcmBytes, reader.activePlaybackStartOffsetBytes + reader.activePlaybackWrittenBytes));
            reader.status = "retrying " + activeTargetLabel(reader) + " " + playbackClock(reader.playbackOffsetBytes, reader.activePlaybackSampleRate);
            persistDocumentPlaybackPosition(reader, reader.status);
            refreshDriveReaderPlayer();
            retryDocumentPlayback(reader, "playback interrupted: " + reason);
            return;
        }
        reader.previewOnlyPlayback = false;
        if (reader.currentIndex + 1 >= reader.chunkCount()) {
            reader.playbackRequested = false;
            reader.status = "complete";
            refreshDriveReaderPlayer();
            setDriveBrowserStatus("Finished reading " + reader.name + ".", false);
            appendStatus("Finished reading " + reader.name + ".");
            return;
        }
        int next = reader.currentIndex + 1;
        if (reader.audioEntry != null && !reader.audioEntry.isDownloaded(next)) {
            reader.currentIndex = next;
            reader.playbackTargetKind = "section";
            reader.playbackTargetIndex = next;
            reader.playbackOffsetBytes = 0L;
            persistDocumentPlaybackPosition(reader, "waiting for section render");
            refreshDriveReaderPlayer();
            appendStatus("Waiting for section " + (next + 1) + " to download.");
            playOrDownloadCurrentSection(true);
            return;
        }
        reader.currentIndex = next;
        reader.playbackTargetKind = "section";
        reader.playbackTargetIndex = next;
        reader.playbackOffsetBytes = 0L;
        persistDocumentPlaybackPosition(reader, "advancing section");
        refreshDriveReaderPlayer();
        ensurePlaybackBufferAhead(reader);
        main.postDelayed(() -> playOrDownloadCurrentSection(true), 250L);
    }

    private void pauseDocumentReader() {
        if (activeDocumentReader == null) {
            showAssistantMessage("No Google Doc is indexed yet.");
            return;
        }
        activeDocumentReader.playbackOffsetBytes = Math.max(0L, Math.min(activeDocumentReader.activePlaybackPcmBytes, activeDocumentReader.activePlaybackStartOffsetBytes + activeDocumentReader.activePlaybackWrittenBytes));
        activeDocumentReader.paused = true;
        activeDocumentReader.playbackRequested = false;
        activeDocumentReader.status = "paused at " + activeTargetLabel(activeDocumentReader) + " " + playbackClock(activeDocumentReader.playbackOffsetBytes, activeDocumentReader.activePlaybackSampleRate);
        persistDocumentPlaybackPosition(activeDocumentReader, activeDocumentReader.status);
        refreshDriveReaderPlayer();
        stopSpeechPlayback();
        appendStatus(activeDocumentReader.status + ".");
    }

    private void resumeDocumentReader() {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null) {
            showAssistantMessage("No Google Doc is indexed yet.");
            return;
        }
        reader.playbackRequested = true;
        reader.paused = false;
        reader.cancelRequested = false;
        reader.playbackReconcileScheduled = false;
        long total = visiblePlayheadPcmBytes(reader);
        if (total > 0L) {
            long visible = Math.max(0L, Math.min(total, visiblePlayheadOffsetBytes(reader, total)));
            playDocumentAudioAtVisibleOffset(reader, visible);
        } else {
            playOrDownloadCurrentSection(true);
        }
    }

    private void stopDocumentReader(String status) {
        if (activeDocumentReader == null) {
            stopSpeechPlayback();
            return;
        }
        activeDocumentReader.paused = true;
        activeDocumentReader.playbackRequested = false;
        activeDocumentReader.downloadRequested = false;
        activeDocumentReader.renderRequested = false;
        activeDocumentReader.cancelRequested = true;
        activeDocumentReader.playbackReconcileScheduled = false;
        activeDocumentReader.status = status == null ? "stopped" : status;
        persistDocumentPlaybackPosition(activeDocumentReader, activeDocumentReader.status);
        refreshDriveReaderPlayer();
        stopSpeechPlayback();
        appendStatus("Document reader " + activeDocumentReader.status + ".");
    }

    private void closeDocumentReaderView(String status) {
        if (activeDocumentReader == null) {
            showAssistantMessage("No document reader is active.");
            return;
        }
        DocumentReaderState reader = activeDocumentReader;
        reader.paused = true;
        reader.playbackRequested = false;
        reader.downloadRequested = false;
        reader.renderRequested = false;
        reader.cancelRequested = true;
        reader.playbackReconcileScheduled = false;
        reader.status = status == null ? "closed" : status;
        persistDocumentPlaybackPosition(reader, reader.status);
        finishSpeechPlayback("document_reader_close");
        activeDocumentReader = null;
        refreshDriveReaderPlayer();
        setDriveRenderInteractionEnabled(true);
        setDriveBrowserStatus("Closed " + safeDisplayName(reader.name) + ". Saved audio and playback position are preserved.", false);
        appendStatus("Closed document reader for " + safeDisplayName(reader.name) + ".");
    }

    private void moveDocumentReader(int delta) {
        if (activeDocumentReader == null) {
            showAssistantMessage("No Google Doc is indexed yet.");
            return;
        }
        ensureGoogleDocAudioEntry(activeDocumentReader);
        int next = Math.max(0, Math.min(activeDocumentReader.chunkCount() - 1, activeDocumentReader.currentIndex + delta));
        if (delta > 0 && activeDocumentReader.audioEntry != null && !activeDocumentReader.audioEntry.isDownloaded(next)) {
            appendStatus("That audio is not rendered yet.");
            return;
        }
        activeDocumentReader.currentIndex = next;
        activeDocumentReader.playbackTargetKind = "section";
        activeDocumentReader.playbackTargetIndex = next;
        activeDocumentReader.playbackOffsetBytes = 0L;
        activeDocumentReader.paused = false;
        activeDocumentReader.playbackRequested = true;
        refreshDriveReaderPlayer();
        stopHostedSpeechPlayback("reader_move");
        playDocumentAudioTarget(activeDocumentReader, "section", next, 0L);
    }

    private AudioTrack createHostedSpeechTrack(int sampleRate) throws IOException {
        int minBufferSize = AudioTrack.getMinBufferSize(sampleRate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
        if (minBufferSize <= 0) {
            throw new IOException("Unable to create audio track buffer");
        }
        return new AudioTrack.Builder()
                .setAudioAttributes(new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build())
                .setAudioFormat(new AudioFormat.Builder()
                        .setSampleRate(sampleRate)
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build())
                .setTransferMode(AudioTrack.MODE_STREAM)
                .setBufferSizeInBytes(Math.max(minBufferSize * 2, 8192))
                .build();
    }

    private long writeWavPcmToTrack(AudioTrack track, File wav, long sequence, long offsetBytes) throws IOException {
        if (wav == null || !wav.exists()) {
            throw new IOException("cached audio missing");
        }
        long pcmLength = Math.max(0L, wav.length() - 44L);
        long startOffset = Math.max(0L, Math.min(pcmLength, offsetBytes));
        startOffset -= (startOffset & 1L);
        long written = 0L;
        long lastUiUpdate = 0L;
        byte[] buffer = new byte[8192];
        try (FileInputStream input = new FileInputStream(wav)) {
            long targetSkip = 44L + startOffset;
            long skipped = 0L;
            while (skipped < targetSkip) {
                long step = input.skip(targetSkip - skipped);
                if (step <= 0L) throw new IOException("cached audio seek failed");
                skipped += step;
            }
            int read;
            while (isCurrentSpeechSequence(sequence) && (read = input.read(buffer)) != -1) {
                written += writeBufferToTrack(track, buffer, read, sequence);
                long now = SystemClock.elapsedRealtime();
                if (now - lastUiUpdate > 220L) {
                    lastUiUpdate = now;
                    updateDocumentPlaybackProgress(sequence, written);
                }
            }
        }
        updateDocumentPlaybackProgress(sequence, written);
        return written;
    }

    private void updateDocumentPlaybackProgress(long sequence, long writtenBytes) {
        DocumentReaderState reader = activeDocumentReader;
        if (reader == null || !isCurrentSpeechSequence(sequence)) return;
        reader.activePlaybackWrittenBytes = Math.max(0L, writtenBytes);
        reader.playbackOffsetBytes = Math.max(0L, Math.min(reader.activePlaybackPcmBytes, reader.activePlaybackStartOffsetBytes + reader.activePlaybackWrittenBytes));
        persistDocumentPlaybackPosition(reader, "playing");
        main.post(this::refreshDriveReaderPlayer);
    }

    private long writeBufferToTrack(AudioTrack track, byte[] buffer, int length, long sequence) throws IOException {
        long writtenBytes = 0L;
        int offset = 0;
        int playableLength = length - (length & 1);
        if (playableLength != length) {
            LocalLog.warn("speech", "dropped_trailing_pcm_half_frame receivedBytes=" + length);
        }
        int zeroWrites = 0;
        while (offset < playableLength && isCurrentSpeechSequence(sequence)) {
            int count = track.write(buffer, offset, playableLength - offset, AudioTrack.WRITE_BLOCKING);
            if (count < 0) throw new IOException("Hosted speech audio playback failed: write=" + count + " receivedBytes=" + length + " writtenBytes=" + writtenBytes);
            if (count == 0) {
                zeroWrites += 1;
                if (zeroWrites > 500) throw new IOException("Hosted speech audio playback stalled: receivedBytes=" + length + " writtenBytes=" + writtenBytes);
                SystemClock.sleep(20L);
                continue;
            }
            zeroWrites = 0;
            offset += count;
            writtenBytes += count;
        }
        return writtenBytes;
    }

    private void releaseHostedTrackIfActive(AudioTrack track) {
        if (track == null) return;
        boolean releaseTrack;
        synchronized (this) {
            releaseTrack = activeHostedSpeechTrack == track;
            if (releaseTrack) activeHostedSpeechTrack = null;
        }
        if (releaseTrack) {
            try { track.stop(); } catch (Exception ignored) { }
            track.release();
        }
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
        lastDriveHandoffAtMs = SystemClock.elapsedRealtime();
        GoogleSignIn.requestPermissions(this, REQUEST_GOOGLE_TOOL_PERMISSIONS, account, scopes.toArray(new Scope[0]));
    }

    private void sendAgentTurn(String clean) {
        if (openAiAgentClient == null || !openAiAgentClient.isConfigured()) {
            showAssistantMessage("GPT-5.5 is not configured in this build.");
            return;
        }
        if (!hasSignedInHomeUser()) {
            pendingAgentTurnAfterGoogleReconnect = clean == null ? "" : clean.trim();
            showAssistantMessage("Sign in with Google first. That one sign-in unlocks GPT-5.5, web search, Google tools, Home Center lists, TickTick fallback, and Cartesia hosted narration.");
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
            int openAiCalls = 0;
            for (int step = 0; step < MAX_AGENT_TOOL_STEPS; step++) {
                GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
                JSONArray availableTools = ToolRegistry.availableTools(account, hasSignedInHomeUser());
                JSONArray unavailableGroups = ToolRegistry.unavailableToolGroups(account, hasSignedInHomeUser());
                openAiCalls++;
                LocalLog.info("ai_cost", "openai_call step=" + step + " callsThisTurn=" + openAiCalls + " toolResults=" + toolResults.length() + " availableTools=" + availableTools.length());
                LocalLog.info("agent_trace", "step=" + step + " availableTools=" + shortMessage(availableTools.toString()));
                rememberAgentTrace("gateway_request_started", step, clean, "", "");
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
                        evidenceContextSnapshot(clean),
                        attachmentImagesSnapshot(),
                        false);
                LocalLog.info("agent_trace", "step=" + step + " gateway_type=" + turn.type + " status=" + turn.status + " requestedTool=" + turn.toolName + " technicalDetails=" + shortMessage(turn.technicalDetails));
                rememberAgentTrace("gateway_response_received", step, clean, turn.status, turn.type + (turn.toolName.isEmpty() ? "" : ":" + turn.toolName));
                applyTaskStateUpdate(turn.taskStateUpdate);
                if (turn.requestsTool()) {
                    LocalLog.info("agent_trace", "android_received_tool=" + turn.toolName);
                    JSONObject pendingForRetry = turn.arguments.optBoolean("_confirmedByGateway", false)
                            ? cloneJson(pendingToolConfirmation)
                            : null;
                    long toolStartedAt = SystemClock.elapsedRealtime();
                    JSONObject result = executeRegisteredTool(turn.toolName, turn.arguments, idToken);
                    recordToolUsageEvent(idToken, turn.toolName, result, SystemClock.elapsedRealtime() - toolStartedAt);
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
                    if (shouldFinishAfterToolResult(turn.toolName, result)) {
                        String directReply = directToolResultReply(turn.toolName, result);
                        LocalLog.info("ai_cost", "direct_tool_finish tool=" + turn.toolName + " openaiCalls=" + openAiCalls);
                        finishAgentReply(clean, directReply, directReply, result.optString("status", "tool_completed"), null);
                        return;
                    }
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
            LocalLog.info("ai_cost", "tool_loop_limit_recovery openaiCallsBeforeRecovery=" + openAiCalls);
            finishFromToolResultsAfterLimit(idToken, clean, toolResults);
        } catch (Exception ex) {
            main.post(() -> {
                LocalLog.info("agent", "tool_loop_failed: " + shortMessage(ex.getMessage()));
                rememberAgentTrace("gateway_error", -1, clean, "exception", shortMessage(ex.getMessage()));
                setBusy(false);
                showAssistantMessage(agentFailureMessage("Home Center gateway", ex.getMessage()));
            });
        }
    }

    private void finishFromToolResultsAfterLimit(String idToken, String clean, JSONArray toolResults) throws Exception {
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        JSONArray availableTools = ToolRegistry.availableTools(account, hasSignedInHomeUser());
        JSONArray unavailableGroups = ToolRegistry.unavailableToolGroups(account, hasSignedInHomeUser());
        LocalLog.info("agent_trace", "tool_loop_limit_recovery_start toolResults=" + toolResults.length() + " availableTools=" + availableTools.length());
        OpenAiAgentClient.ToolTurn recovery = openAiAgentClient.sendToolTurn(
                idToken,
                clean,
                recentTranscriptSnapshot(),
                conversationSummary,
                toolResults,
                availableTools,
                unavailableGroups,
                null,
                workingMemorySnapshot(),
                currentTimeContext(),
                evidenceContextSnapshot(clean),
                attachmentImagesSnapshot(),
                true);
        LocalLog.info("agent_trace", "tool_loop_limit_recovery status=" + recovery.status + " type=" + recovery.type + " requestedTool=" + recovery.toolName);
        if (recovery.requestsTool()) {
            String fallback = synthesizeToolLoopProgressReply(toolResults);
            finishAgentReply(clean,
                    fallback,
                    fallback,
                    "tool_loop_limit_recovery_requested_tool",
                    null);
            return;
        }
        String reply = recovery.reply == null || recovery.reply.trim().isEmpty()
                ? "I found information, but I could not turn it into a final answer."
                : recovery.reply;
        if (containsForbiddenToolPlanPhrase(reply)) {
            reply = synthesizeToolLoopProgressReply(toolResults);
        }
        finishAgentReply(clean, reply, reply, "tool_loop_limit_recovered", null);
    }

    private boolean containsForbiddenToolPlanPhrase(String value) {
        String lower = value == null ? "" : value.toLowerCase(Locale.US);
        return lower.contains("tool plan") && lower.contains("did not converge");
    }

    private String synthesizeToolLoopProgressReply(JSONArray toolResults) {
        List<String> successes = new ArrayList<>();
        String failedTool = "";
        String failedMessage = "";
        for (int i = 0; i < toolResults.length(); i++) {
            JSONObject entry = toolResults.optJSONObject(i);
            if (entry == null) {
                continue;
            }
            String toolName = entry.optString("name", "tool");
            JSONObject result = entry.optJSONObject("result");
            boolean ok = result != null && result.optBoolean("ok", false);
            if (ok) {
                if (successes.size() < 8) {
                    successes.add(toolProgressSummary(toolName, result));
                }
            } else if (failedTool.isEmpty()) {
                failedTool = toolName;
                failedMessage = result == null ? "the tool did not return a result" : firstNonEmpty(
                        result.optString("spokenMessage", ""),
                        result.optString("detail", ""),
                        result.optString("error", ""),
                        "the tool failed");
            }
        }
        String succeeded = successes.isEmpty() ? "nothing" : joinSentences(successes);
        if (!failedTool.isEmpty()) {
            return "Failed at " + failedTool + ": " + failedMessage
                    + "\n\nSucceeded before it: " + succeeded
                    + "\n\nNext action needed: fix that failure, then ask me to continue.";
        }
        if (successes.isEmpty()) {
            return "I stopped before completing the request."
                    + "\n\nSucceeded before it: nothing."
                    + "\n\nNext action needed: ask me to continue or narrow the request.";
        }
        return "I completed these steps before the tool loop stopped: " + succeeded
                + "\n\nI stopped before completing the remaining requested steps."
                + "\n\nNext action needed: ask me to continue from the last completed step.";
    }

    private String toolProgressSummary(String toolName, JSONObject result) {
        if (result == null) {
            return toolName;
        }
        String spoken = result.optString("spokenMessage", "").trim();
        if (!spoken.isEmpty()) {
            return toolName + " (" + spoken + ")";
        }
        JSONObject file = result.optJSONObject("file");
        if (file != null && !file.optString("name", "").trim().isEmpty()) {
            return toolName + " (" + file.optString("name").trim() + ")";
        }
        String status = result.optString("status", "").trim();
        if (!status.isEmpty()) {
            return toolName + " (" + status + ")";
        }
        return toolName;
    }

    private boolean shouldFinishAfterToolResult(String toolName, JSONObject result) {
        if (toolName == null || result == null || !result.optBoolean("ok", false)) {
            return false;
        }
        if ("docs.read".equals(toolName)
                || "docs.search".equals(toolName)
                || "drive.search".equals(toolName)
                || "sheets.read".equals(toolName)
                || "gmail.read".equals(toolName)
                || "calendar.search".equals(toolName)
                || "contacts.search".equals(toolName)
                || "contacts.read".equals(toolName)
                || "knowledge.read".equals(toolName)) {
            return false;
        }
        return toolName.startsWith("docs.")
                || toolName.startsWith("drive.")
                || toolName.startsWith("sheets.")
                || toolName.startsWith("gmail.")
                || toolName.startsWith("calendar.")
                || toolName.startsWith("lists.")
                || toolName.startsWith("knowledge.")
                || "github.create_issue".equals(toolName);
    }

    private String directToolResultReply(String toolName, JSONObject result) {
        if (result == null) {
            return "Done.";
        }
        String spoken = result.optString("spokenMessage", "").trim();
        if (!spoken.isEmpty()) {
            return spoken;
        }
        String reply = result.optString("reply", "").trim();
        if (!reply.isEmpty()) {
            return reply;
        }
        String title = firstNonEmpty(
                result.optString("title", ""),
                result.optString("name", ""),
                result.optString("summary", ""),
                "");
        JSONObject file = result.optJSONObject("file");
        if (title.isEmpty() && file != null) {
            title = file.optString("name", "").trim();
        }
        String link = firstNonEmpty(
                result.optString("webViewLink", ""),
                result.optString("htmlLink", ""),
                file == null ? "" : file.optString("webViewLink", ""),
                "");
        String status = result.optString("status", "").trim();
        String action = status.isEmpty() ? toolName : status.replace('_', ' ');
        if (toolName != null && toolName.startsWith("docs.create")) {
            return link.isEmpty()
                    ? "Created Google Doc: " + (title.isEmpty() ? "Untitled" : title)
                    : "Created Google Doc: " + (title.isEmpty() ? "Untitled" : title) + "\n" + link;
        }
        if (!title.isEmpty()) {
            return link.isEmpty()
                    ? "Done: " + title + "."
                    : "Done: " + title + "\n" + link;
        }
        if (!action.isEmpty()) {
            return "Done: " + action + ".";
        }
        return "Done.";
    }

    private String firstNonEmpty(String first, String fallback) {
        return firstNonEmpty(first, "", "", fallback);
    }

    private String firstNonEmpty(String first, String second, String fallback) {
        return firstNonEmpty(first, second, "", fallback);
    }

    private String firstNonEmpty(String first, String second, String third, String fallback) {
        if (first != null && !first.trim().isEmpty()) return first.trim();
        if (second != null && !second.trim().isEmpty()) return second.trim();
        if (third != null && !third.trim().isEmpty()) return third.trim();
        return fallback;
    }

    private String joinSentences(List<String> values) {
        StringBuilder builder = new StringBuilder();
        for (String value : values) {
            if (value == null || value.trim().isEmpty()) {
                continue;
            }
            if (builder.length() > 0) {
                builder.append("; ");
            }
            builder.append(value.trim());
        }
        return builder.length() == 0 ? "nothing" : builder.toString();
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
        if (definition.doubleConfirmationRequired && (arguments == null || !arguments.optBoolean("_doubleConfirmedByGateway", false))) {
            return toolError(toolName, "double_confirmation_required", "This delete tool requires two explicit confirmations.");
        }
        if (definition.confirmationRequired && (arguments == null || !arguments.optBoolean("_confirmedByGateway", false))) {
            return toolError(toolName, "confirmation_required", "This write tool requires explicit gateway confirmation.");
        }
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        if ("drive".equals(definition.group) || "docs".equals(definition.group)) {
            if (googleDriveClient == null) {
                return toolError(toolName, "drive_unavailable", "Google Drive and Docs tools are not available in this build.");
            }
            if ("drive.upload_file".equals(toolName)) {
                JSONObject file = findAttachedFile(toolArg(arguments, "sessionFileId", ""));
                if (file == null) {
                    return toolError(toolName, "attachment_missing", "No attached file matched that sessionFileId.");
                }
                JSONObject result = googleDriveClient.uploadAttachedFileTool(arguments, account, file);
                updateAttachmentAfterDriveUpload(toolArg(arguments, "sessionFileId", ""), result);
                return result;
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
        if ("knowledge".equals(definition.group)) {
            if (localKnowledgeClient == null) {
                return toolError(toolName, "knowledge_unavailable", "Local knowledge storage is not available in this build.");
            }
            return localKnowledgeClient.runTool(toolName, arguments);
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

    private void rememberAgentTrace(String event, int step, String latestUserText, String status, String detail) {
        synchronized (toolTraceLock) {
            try {
                JSONObject trace = new JSONObject()
                        .put("event", event == null ? "" : event)
                        .put("step", step)
                        .put("latestUserText", latestUserText == null ? "" : shortMessage(latestUserText))
                        .put("status", status == null ? "" : status)
                        .put("detail", detail == null ? "" : shortMessage(detail))
                        .put("timestamp", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.US).format(new Date()));
                recentToolTrace.put(trace);
                while (recentToolTrace.length() > 10) {
                    recentToolTrace.remove(0);
                }
            } catch (Exception ignored) {
            }
        }
    }

    private void rememberToolTrace(String toolName, JSONObject arguments, JSONObject result) {
        synchronized (toolTraceLock) {
            try {
                recentToolTrace.put(new JSONObject()
                        .put("event", "tool_result")
                        .put("toolName", toolName == null ? "" : toolName)
                        .put("arguments", arguments == null ? new JSONObject() : cloneJson(arguments))
                        .put("result", result == null ? new JSONObject() : cloneJson(result)));
                while (recentToolTrace.length() > 10) {
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
        String finalResponse = replyText == null || replyText.trim().isEmpty()
                ? "GPT-5.5 returned an empty response. Please retry or say \"report this\" so I can file the captured failure."
                : replyText.trim();
        if (looksLikeRawToolCallJson(finalResponse)) {
            LocalLog.warn("agent", "blocked_raw_tool_call_reply");
            finalResponse = "I could not safely display that tool request. Please try again.";
            status = "raw_tool_call_blocked";
            pendingConfirmation = null;
        }
        chatTurns.add(new ChatTurn("assistant", finalResponse));
        trimChatTurns();
        final String responseForUi = finalResponse;
        JSONObject pendingForUi = cloneJson(pendingConfirmation);
        String speechText = narration == null || narration.trim().isEmpty()
                ? finalResponse
                : narration.trim();
        if (pendingForUi != null) {
            speechText = confirmationSpeechReadbackForPending(pendingForUi);
        }
        final String speechForUi = speechText;
        final String statusForUi = status;
        main.post(() -> {
            setBusy(false);
            String displayedResponse = pendingForUi != null
                    ? appendAssistantMessageRaw(responseForUi)
                    : appendAssistantMessage(responseForUi, clean);
            if (pendingForUi != null) {
                appendPendingConfirmationCard(pendingForUi);
            }
            if (statusForUi != null && !statusForUi.trim().isEmpty()) {
                appendStatus(statusForUi.trim());
            }
            if (pendingForUi != null) {
                speakOperational(speechForUi);
            } else {
                speakRenderedResponse(speechForUi);
            }
        });
    }

    private boolean looksLikeRawToolCallJson(String text) {
        if (text == null) {
            return false;
        }
        String trimmed = text.trim();
        return trimmed.startsWith("{")
                && trimmed.contains("\"type\"")
                && trimmed.contains("tool_call")
                && (trimmed.contains("\"toolName\"") || trimmed.contains("\"name\""));
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

    private void applyTaskStateUpdate(JSONObject update) {
        if (update == null) {
            return;
        }
        try {
            String status = update.optString("status", "").trim();
            synchronized (workingMemoryLock) {
                if ("complete".equals(status) || "cancelled".equals(status)) {
                    workingMemory.remove("activeTask");
                    LocalLog.info("agent_trace", "working_memory_clear activeTask status=" + status);
                    return;
                }
                JSONObject task = new JSONObject();
                putIfPresent(task, "objective", update.optString("objective", ""));
                putIfPresent(task, "originalUserRequest", update.optString("originalUserRequest", ""));
                putIfPresent(task, "missingDetailQuestion", update.optString("missingDetailQuestion", ""));
                putIfPresent(task, "knownContext", update.optString("knownContext", ""));
                putIfPresent(task, "blockingReason", update.optString("blockingReason", ""));
                putIfPresent(task, "expectedNextAction", update.optString("expectedNextAction", ""));
                putIfPresent(task, "status", status);
                if (task.length() > 0) {
                    workingMemory.put("activeTask", task);
                    LocalLog.info("agent_trace", "working_memory_update activeTask=" + shortMessage(task.toString()));
                }
            }
        } catch (Exception ex) {
            LocalLog.warn("agent", "task_state_update_failed: " + shortMessage(ex.getMessage()));
        }
    }

    private void putIfPresent(JSONObject json, String key, String value) throws Exception {
        if (value != null && !value.trim().isEmpty()) {
            json.put(key, value.trim());
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
            if ("gmail.read".equals(toolName)) {
                rememberEmailMessage(toolName, result);
                return;
            }
            if ("gmail.search".equals(toolName)) {
                JSONArray messages = result.optJSONArray("messages");
                if (messages != null && messages.length() == 1) rememberEmailMessage(toolName, messages.optJSONObject(0));
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
                return;
            }
            if ("knowledge.append".equals(toolName)) {
                rememberLocalKnowledge(result);
                return;
            }
            if ("knowledge.read".equals(toolName)) {
                rememberLocalKnowledge(result);
            }
        } catch (Exception ex) {
            LocalLog.warn("agent", "working_memory_update_failed tool=" + toolName + " detail=" + shortMessage(ex.getMessage()));
        }
    }

    private void rememberLocalKnowledge(JSONObject result) throws Exception {
        if (result == null) return;
        JSONObject memory = new JSONObject()
                .put("file", result.optString("file", ""))
                .put("path", result.optString("path", ""))
                .put("title", result.optString("title", ""))
                .put("sourceTool", result.optString("tool", ""));
        String bodyPreview = result.optString("bodyPreview", "");
        synchronized (workingMemoryLock) {
            workingMemory.put("lastKnowledgeFile", memory);
            if (looksLikeWritingMemory(memory.optString("title", "") + "\n" + bodyPreview)) {
                JSONObject context = new JSONObject()
                        .put("title", memory.optString("title", ""))
                        .put("file", memory.optString("file", ""))
                        .put("sourceTool", memory.optString("sourceTool", ""))
                        .put("evidence", shortMessage(bodyPreview));
                workingMemory.put("rememberedWritingContext", context);
            }
        }
        LocalLog.info("agent_trace", "working_memory_update lastKnowledgeFile=" + memory.toString());
    }

    private boolean looksLikeWritingMemory(String text) {
        String lower = text == null ? "" : text.toLowerCase(Locale.US);
        return lower.contains("writing")
                || lower.contains("story")
                || lower.contains("scene")
                || lower.contains("draft")
                || lower.contains("prose")
                || lower.contains("novel")
                || lower.contains("manuscript")
                || lower.contains("character");
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

    private void rememberEmailMessage(String sourceTool, JSONObject message) throws Exception {
        if (message == null) return;
        String messageId = message.optString("messageId", message.optString("id", ""));
        if (messageId == null || messageId.trim().isEmpty()) return;
        JSONObject headers = message.optJSONObject("headers");
        JSONObject memory = new JSONObject()
                .put("messageId", messageId.trim())
                .put("threadId", message.optString("threadId", ""))
                .put("subject", headers == null ? "" : headers.optString("Subject", ""))
                .put("from", headers == null ? "" : headers.optString("From", ""))
                .put("sourceTool", sourceTool == null ? "" : sourceTool);
        synchronized (workingMemoryLock) {
            workingMemory.put("lastEmailMessage", memory);
        }
        LocalLog.info("agent_trace", "working_memory_update lastEmailMessage=" + memory.toString());
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

    private String confirmationActionForPending(JSONObject pending) {
        String action = pending == null ? "action" : pending.optString("action", "").trim();
        if (!action.isEmpty()) {
            return action;
        }
        String toolName = pending == null ? "" : pending.optString("toolName", "").trim();
        if ("docs.update".equals(toolName) || toolName.endsWith(".update") || toolName.contains("update")) {
            return "edit";
        }
        if ("docs.create".equals(toolName) || toolName.endsWith(".create") || toolName.contains("create")) {
            return "create";
        }
        if (toolName.contains("delete") || toolName.contains("trash") || toolName.contains("remove")) {
            return "delete";
        }
        return "action";
    }

    private String confirmationInstructionForPending(JSONObject pending) {
        String action = confirmationActionForPending(pending);
        return "Say \"confirm " + action + "\" or press Confirm.";
    }

    private String confirmationSpeechInstructionForPending(JSONObject pending) {
        String action = confirmationActionForPending(pending);
        return "Say confirm " + action + ", or press Confirm.";
    }

    private String confirmationSpeechReadbackForPending(JSONObject pending) {
        String action = confirmationActionForPending(pending);
        String title = pending == null ? "" : pending.optString("title", "").trim();
        String summary = pending == null ? "" : pending.optString("summary", "").trim();
        StringBuilder builder = new StringBuilder();
        builder.append("Confirm ").append(action).append(" required. ");
        if (!title.isEmpty()) {
            builder.append(title).append(". ");
        }
        if (!summary.isEmpty() && !summary.equals(title)) {
            builder.append(summary).append(" ");
        }
        builder.append(confirmationSpeechInstructionForPending(pending));
        return builder.toString().trim();
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
        summary.setPadding(0, dp(6), 0, dp(6));
        card.addView(summary, matchWrap());

        TextView instruction = new TextView(this);
        String confirmInstruction = confirmationInstructionForPending(pending);
        instruction.setText(confirmInstruction);
        instruction.setTextSize(15);
        instruction.setTypeface(Typeface.DEFAULT_BOLD);
        instruction.setTextColor(COLOR_TEXT);
        instruction.setPadding(0, 0, 0, dp(10));
        card.addView(instruction, matchWrap());
        card.setContentDescription(pending.optString("title", "Confirm Action") + ". "
                + pending.optString("summary", "Confirm this action.") + " " + confirmInstruction);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.CENTER_VERTICAL);

        String action = confirmationActionForPending(pending);
        String confirmLabel = "action".equals(action) ? "Confirm" : "Confirm " + action;
        Button confirm = button(confirmLabel, 14, confirmInstruction + " Confirm and run this action.");
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
        lastDriveHandoffAtMs = SystemClock.elapsedRealtime();
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

    private void startFileAttach() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try {
            startActivityForResult(intent, REQUEST_FILE_ATTACH);
        } catch (ActivityNotFoundException ex) {
            showAssistantMessage("No file picker is available on this device.");
        }
    }

    private void importAttachedFiles(Intent data) {
        if (data == null || (data.getData() == null && data.getClipData() == null)) {
            showAssistantMessage("No file was selected.");
            return;
        }
        ArrayList<Uri> uris = new ArrayList<>();
        if (data.getClipData() != null) {
            ClipData clipData = data.getClipData();
            for (int i = 0; i < clipData.getItemCount(); i++) {
                Uri uri = clipData.getItemAt(i).getUri();
                if (uri != null) {
                    uris.add(uri);
                }
            }
        } else if (data.getData() != null) {
            uris.add(data.getData());
        }
        synchronized (attachmentLock) {
            while (activeFileIds.length() > 0) {
                activeFileIds.remove(0);
            }
        }
        int flags = data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        int imported = 0;
        for (Uri uri : uris) {
            try {
                if ((flags & Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0) {
                    getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
                }
            } catch (Exception ex) {
                LocalLog.warn("attachment", "persist_permission_failed: " + shortMessage(ex.getMessage()));
            }
            try {
                JSONObject file = buildAttachmentRecord(uri);
                rememberAttachment(file);
                appendAttachmentMessage(file);
                imported += 1;
            } catch (Exception ex) {
                showAssistantMessage("Could not attach file: " + shortMessage(ex.getMessage()));
            }
        }
        if (imported > 0) {
            appendStatus("Attached " + imported + " file" + (imported == 1 ? "" : "s") + ".");
        }
    }

    private JSONObject buildAttachmentRecord(Uri uri) throws Exception {
        AttachmentMetadata metadata = attachmentMetadata(uri);
        String mimeType = metadata.mimeType == null || metadata.mimeType.trim().isEmpty()
                ? "application/octet-stream"
                : metadata.mimeType.trim();
        String kind = mimeType.toLowerCase(Locale.US).startsWith("image/") ? "image" : (isTextLikeMime(mimeType, metadata.displayName) ? "text" : "file");
        String sessionFileId;
        synchronized (attachmentLock) {
            sessionFileId = "file-" + nextSessionFileNumber++;
        }
        JSONObject json = new JSONObject()
                .put("sessionFileId", sessionFileId)
                .put("displayName", metadata.displayName)
                .put("mimeType", mimeType)
                .put("sizeBytes", metadata.sizeBytes)
                .put("kind", kind)
                .put("uri", uri.toString())
                .put("textPreview", "")
                .put("contentAvailableToAgent", false)
                .put("imagePreviewAvailable", false)
                .put("driveUploaded", false)
                .put("driveFileId", "")
                .put("driveWebViewLink", "");
        if ("text".equals(kind)) {
            json.put("textPreview", readTextPreviewFromUri(uri, MAX_ATTACHMENT_PREVIEW_CHARS));
            json.put("contentAvailableToAgent", true);
        } else if ("image".equals(kind)) {
            byte[] imageBytes = readBytesFromUri(uri, MAX_IMAGE_ATTACHMENT_BYTES + 1);
            if (imageBytes.length <= MAX_IMAGE_ATTACHMENT_BYTES) {
                json.put("imageDataUrl", "data:" + mimeType + ";base64," + Base64.encodeToString(imageBytes, Base64.NO_WRAP));
                json.put("imagePreviewAvailable", true);
                json.put("contentAvailableToAgent", true);
            } else {
                json.put("textPreview", "Image is too large for inline analysis. Ask to upload it to Drive or choose a smaller image.");
            }
        }
        return json;
    }

    private AttachmentMetadata attachmentMetadata(Uri uri) {
        String displayName = "";
        long sizeBytes = -1L;
        String mimeType = getContentResolver().getType(uri);
        try (Cursor cursor = getContentResolver().query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (nameIndex >= 0) {
                    displayName = cursor.getString(nameIndex);
                }
                int sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE);
                if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) {
                    sizeBytes = cursor.getLong(sizeIndex);
                }
            }
        } catch (Exception ex) {
            LocalLog.warn("attachment", "metadata_failed: " + shortMessage(ex.getMessage()));
        }
        if (displayName == null || displayName.trim().isEmpty()) {
            displayName = "attachment-" + System.currentTimeMillis();
        }
        return new AttachmentMetadata(displayName.trim(), mimeType == null ? "" : mimeType.trim(), sizeBytes);
    }

    private void rememberAttachment(JSONObject file) throws Exception {
        synchronized (attachmentLock) {
            attachedFiles.put(file);
            activeFileIds.put(file.optString("sessionFileId", ""));
        }
        updateAttachmentWorkingMemory();
        LocalLog.info("attachment", "attached sessionFileId=" + file.optString("sessionFileId", "") + " name=" + file.optString("displayName", "") + " kind=" + file.optString("kind", ""));
    }

    private void updateAttachmentWorkingMemory() throws Exception {
        synchronized (workingMemoryLock) {
            workingMemory.put("attachedFiles", sanitizedAttachedFilesSnapshot());
            workingMemory.put("activeFileIds", activeFileIdsSnapshot());
        }
    }

    private JSONArray sanitizedAttachedFilesSnapshot() {
        JSONArray array = new JSONArray();
        synchronized (attachmentLock) {
            for (int i = 0; i < attachedFiles.length(); i++) {
                JSONObject file = attachedFiles.optJSONObject(i);
                if (file == null) {
                    continue;
                }
                array.put(sanitizedAttachment(file));
            }
        }
        return array;
    }

    private JSONArray activeFileIdsSnapshot() {
        JSONArray array = new JSONArray();
        synchronized (attachmentLock) {
            for (int i = 0; i < activeFileIds.length(); i++) {
                String id = activeFileIds.optString(i, "");
                if (!id.isEmpty()) {
                    array.put(id);
                }
            }
        }
        return array;
    }

    private JSONObject sanitizedAttachment(JSONObject file) {
        JSONObject json = new JSONObject();
        try {
            json.put("sessionFileId", file.optString("sessionFileId", ""));
            json.put("displayName", file.optString("displayName", ""));
            json.put("mimeType", file.optString("mimeType", ""));
            json.put("sizeBytes", file.optLong("sizeBytes", -1L));
            json.put("kind", file.optString("kind", ""));
            json.put("textPreview", file.optString("textPreview", ""));
            json.put("contentAvailableToAgent", file.optBoolean("contentAvailableToAgent", false));
            json.put("imagePreviewAvailable", file.optBoolean("imagePreviewAvailable", false));
            json.put("driveUploaded", file.optBoolean("driveUploaded", false));
            json.put("driveFileId", file.optString("driveFileId", ""));
            json.put("driveWebViewLink", file.optString("driveWebViewLink", ""));
        } catch (Exception ignored) {
        }
        return json;
    }

    private JSONArray attachmentImagesSnapshot() {
        JSONArray array = new JSONArray();
        synchronized (attachmentLock) {
            for (int i = 0; i < attachedFiles.length(); i++) {
                JSONObject file = attachedFiles.optJSONObject(i);
                if (file == null || !"image".equals(file.optString("kind", "")) || !file.optBoolean("imagePreviewAvailable", false)) {
                    continue;
                }
                String dataUrl = file.optString("imageDataUrl", "");
                if (dataUrl.isEmpty()) {
                    continue;
                }
                try {
                    array.put(new JSONObject()
                            .put("sessionFileId", file.optString("sessionFileId", ""))
                            .put("displayName", file.optString("displayName", ""))
                            .put("mimeType", file.optString("mimeType", ""))
                            .put("imageUrl", dataUrl)
                            .put("detail", "auto"));
                } catch (Exception ignored) {
                }
            }
        }
        return array;
    }

    private JSONObject findAttachedFile(String sessionFileId) {
        if (sessionFileId == null || sessionFileId.trim().isEmpty()) {
            return null;
        }
        synchronized (attachmentLock) {
            for (int i = 0; i < attachedFiles.length(); i++) {
                JSONObject file = attachedFiles.optJSONObject(i);
                if (file != null && sessionFileId.equals(file.optString("sessionFileId", ""))) {
                    return file;
                }
            }
        }
        return null;
    }

    private void updateAttachmentAfterDriveUpload(String sessionFileId, JSONObject result) {
        if (sessionFileId == null || result == null || !result.optBoolean("ok", false)) {
            return;
        }
        JSONObject uploaded = result.optJSONObject("file");
        if (uploaded == null) {
            return;
        }
        synchronized (attachmentLock) {
            JSONObject file = findAttachedFile(sessionFileId);
            if (file != null) {
                try {
                    file.put("driveUploaded", true);
                    file.put("driveFileId", uploaded.optString("id", ""));
                    file.put("driveWebViewLink", uploaded.optString("webViewLink", ""));
                } catch (Exception ignored) {
                }
            }
        }
        try {
            updateAttachmentWorkingMemory();
        } catch (Exception ignored) {
        }
    }

    private void appendAttachmentMessage(JSONObject file) {
        String name = file == null ? "file" : file.optString("displayName", "file");
        String text = "Attached: " + name;
        appendAssistantMessageRaw(text);
        chatTurns.add(new ChatTurn("assistant", text));
        trimChatTurns();
        recordTranscriptTurn("assistant", text);
    }

    private boolean isTextLikeMime(String mimeType, String displayName) {
        String mime = mimeType == null ? "" : mimeType.toLowerCase(Locale.US);
        String name = displayName == null ? "" : displayName.toLowerCase(Locale.US);
        return mime.startsWith("text/")
                || mime.contains("json")
                || mime.contains("xml")
                || mime.contains("csv")
                || name.endsWith(".md")
                || name.endsWith(".txt")
                || name.endsWith(".json")
                || name.endsWith(".csv")
                || name.endsWith(".xml")
                || name.endsWith(".html")
                || name.endsWith(".css")
                || name.endsWith(".js");
    }

    private String readTextPreviewFromUri(Uri uri, int maxChars) throws IOException {
        String text = readTextFromUri(uri);
        if (text.length() <= maxChars) {
            return text;
        }
        return text.substring(0, maxChars) + "\n\n[Preview truncated.]";
    }

    private byte[] readBytesFromUri(Uri uri, int maxBytes) throws IOException {
        try (InputStream input = getContentResolver().openInputStream(uri); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            if (input == null) {
                throw new IOException("empty file");
            }
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) {
                if (output.size() + read > maxBytes) {
                    output.write(buffer, 0, Math.max(0, maxBytes - output.size()));
                    break;
                }
                output.write(buffer, 0, read);
            }
            return output.toByteArray();
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

    private void recordToolUsageEvent(String idToken, String toolName, JSONObject result, long latencyMs) {
        if (openAiAgentClient == null || !openAiAgentClient.isConfigured() || idToken == null || idToken.trim().isEmpty()) {
            return;
        }
        ToolRegistry.ToolDefinition definition = ToolRegistry.definition(toolName);
        JSONObject event = new JSONObject();
        try {
            event.put("toolName", toolName == null ? "" : toolName);
            event.put("provider", definition == null ? "tool" : definition.group);
            event.put("group", definition == null ? "tool" : definition.group);
            event.put("write", definition != null && definition.write);
            event.put("destructive", definition != null && definition.doubleConfirmationRequired);
            event.put("ok", result != null && result.optBoolean("ok", false));
            event.put("status", result == null ? "no_result" : result.optString("status", result.optString("error", "")));
            event.put("latencyMs", Math.max(0, latencyMs));
            event.put("resultCount", safeResultCount(result));
            event.put("resultBytes", result == null ? 0 : Math.min(200000, result.toString().length()));
            event.put("bucketId", bucketValue());
            event.put("conversationId", activeConversationId == null ? "" : activeConversationId);
        } catch (Exception ignored) {
        }
        executor.execute(() -> {
            try {
                openAiAgentClient.recordUsageToolEvent(idToken, event);
            } catch (Exception ex) {
                LocalLog.warn("usage", "tool_usage_event_failed tool=" + toolName + " detail=" + shortMessage(ex.getMessage()));
            }
        });
    }

    private int safeResultCount(JSONObject result) {
        if (result == null) {
            return 0;
        }
        JSONArray files = result.optJSONArray("files");
        if (files != null) {
            return files.length();
        }
        JSONArray messages = result.optJSONArray("messages");
        if (messages != null) {
            return messages.length();
        }
        JSONArray events = result.optJSONArray("events");
        if (events != null) {
            return events.length();
        }
        JSONArray contacts = result.optJSONArray("contacts");
        if (contacts != null) {
            return contacts.length();
        }
        JSONArray items = result.optJSONArray("items");
        if (items != null) {
            return items.length();
        }
        return result.optJSONObject("file") != null ? 1 : 0;
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
        if (attachFileButton != null) {
            attachFileButton.setEnabled(!busyState);
            attachFileButton.setAlpha(busyState ? 0.65f : 1.0f);
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
            authStatusView.setVisibility(View.VISIBLE);
            authStatusView.setText("Setup needed");
            authStatusView.setTextColor(COLOR_DANGER);
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.VISIBLE);
            }
            if (loginShellDetailView != null) {
                loginShellDetailView.setText("Drive Reader needs Firebase/Google config before it can browse cloud files.");
            }
            if (googleToolsButton != null) {
                googleToolsButton.setText("Google setup needed");
            }
            updateLoginShellVisibility();
            updateBackendStatus();
            return;
        }
        FirebaseUser user = firebaseAuth == null ? null : firebaseAuth.getCurrentUser();
        GoogleSignInAccount account = GoogleSignIn.getLastSignedInAccount(this);
        boolean hasToolScopes = hasAllGoogleToolScopes(account);
        if (user == null) {
            authStatusView.setVisibility(View.VISIBLE);
            authStatusView.setText("Not signed in");
            authStatusView.setTextColor(COLOR_PRIMARY);
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.VISIBLE);
            }
            if (loginShellDetailView != null) {
                loginShellDetailView.setText("Sign in once to browse Drive folders, recent files, and Google Docs.");
            }
            if (googleToolsButton != null) {
                googleToolsButton.setText("Sign in with Google");
            }
        } else if (!hasToolScopes) {
            authStatusView.setVisibility(View.VISIBLE);
            authStatusView.setText("Tools need approval");
            authStatusView.setTextColor(COLOR_PRIMARY);
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.VISIBLE);
            }
            if (loginShellDetailView != null) {
                loginShellDetailView.setText("Identity is connected. Approve Drive scope so the file reader can list folders and open Google Docs.");
            }
            if (googleToolsButton != null) {
                googleToolsButton.setText("Approve Drive");
            }
        } else {
            authStatusView.setVisibility(View.GONE);
            authStatusView.setText("Connected");
            authStatusView.setTextColor(COLOR_ACCENT);
            if (googleSignInButton != null) {
                googleSignInButton.setVisibility(View.GONE);
            }
            if (loginShellDetailView != null) {
                loginShellDetailView.setText("Narratable Google Docs. Search, sort, filter, then tap Narrate.");
            }
            if (googleToolsButton != null) {
                googleToolsButton.setText("Refresh Drive");
            }
        }
        updateLoginShellVisibility();
        updateBackendStatus();
    }

    private void speak(String message) {
        speakOperational(message);
    }

    private void speakOperational(String message) {
        String clean = sanitizeTextForSpeech(message);
        if (clean.isEmpty()) {
            LocalLog.info("speech", "skip_empty_message");
            return;
        }
        lastSpoken = clean;
        setStatus(clean);
        if (isSpeechMuted()) {
            logMutedSpeechSkip(clean);
            return;
        }
        LocalLog.info("speech", "native_tts_request reason=operational displayedResponseLength=" + clean.length() + " ttsTextLength=" + clean.length());
        requestSpeechFocus();
        String utteranceId = "home_center_" + System.currentTimeMillis();
        activeSpeechUtteranceId = utteranceId;
        long sequence = beginSpeechSequence("new_native_speech_request");
        speakWithNativeTtsPrepared(clean, utteranceId, sequence, "operational");
    }

    private void speakRenderedResponse(String message) {
        String clean = sanitizeTextForSpeech(message);
        if (clean.isEmpty()) {
            LocalLog.info("speech", "skip_empty_message");
            return;
        }
        lastSpoken = clean;
        setStatus(clean);
        if (isSpeechMuted()) {
            logMutedSpeechSkip(clean);
            return;
        }
        LocalLog.info("speech", "hosted_speech_request displayedResponseLength=" + clean.length() + " ttsTextLength=" + clean.length());
        requestSpeechFocus();
        String utteranceId = "home_center_" + System.currentTimeMillis();
        activeSpeechUtteranceId = utteranceId;
        long sequence = beginSpeechSequence("new_rendered_speech_request");
        if (shouldUseHostedSpeech()) {
            setSpeechPlaying(true);
            speakWithHostedSpeech(clean, utteranceId, sequence);
            return;
        }
        String cause = hostedSpeechUnavailableCause();
        LocalLog.info("speech", "hosted_speech_unavailable cause=" + cause);
        setStatus("Hosted narration is unavailable right now: " + cause + ".");
        finishSpeechPlaybackFor(utteranceId, "hosted_speech_error");
    }

    private void logMutedSpeechSkip(String clean) {
        LocalLog.info("speech", (isSmokeSpeechMuted() ? "smoke_mute_skip" : "global_mute_skip")
                + " displayedResponseLength=" + clean.length() + " ttsTextLength=" + clean.length());
        setSpeechPlaying(false);
        LocalLog.info("speech", "speech_cleanup reason=" + (isSmokeSpeechMuted() ? "smoke_muted" : "global_muted"));
    }

    private boolean isSmokeSpeechMuted() {
        return BuildConfig.DEBUG && smokeSpeechMutedUntilMillis > SystemClock.elapsedRealtime();
    }

    private boolean isSpeechMuted() {
        return narrationMuted || isSmokeSpeechMuted();
    }

    private String sanitizeTextForSpeech(String message) {
        String clean = message == null ? "" : message.trim();
        if (clean.isEmpty()) {
            return "";
        }
        String withoutUrls = clean.replaceAll("https?://\\S+", " Link available in chat. ");
        withoutUrls = withoutUrls.replaceAll("www\\.\\S+", " Link available in chat. ");
        withoutUrls = withoutUrls.replaceAll("\\s+", " ").trim();
        withoutUrls = withoutUrls.replaceAll("(Link available in chat\\.\\s*){2,}", "Link available in chat. ").trim();
        return withoutUrls;
    }

    private boolean shouldUseHostedSpeech() {
        return hostedSpeechClient != null && hostedSpeechClient.isConfigured();
    }

    private String hostedSpeechUnavailableCause() {
        if (hostedSpeechClient == null) {
            return "speech client missing";
        }
        if (!hostedSpeechClient.isConfigured()) {
            return "config missing: set AGENT_GATEWAY_BASE_URL to the hosted Home Center gateway";
        }
        return "unknown configuration failure";
    }

    private long beginSpeechSequence(String reason) {
        synchronized (this) {
            speechSequence += 1L;
            LocalLog.info("speech", "stop_reason=" + reason + " sequence=" + speechSequence); // includes stop_reason=new_speech_request
            stopHostedSpeechPlaybackLocked(reason);
            return speechSequence;
        }
    }

    private boolean isCurrentSpeechSequence(long sequence) {
        return speechSequence == sequence;
    }

    private void speakWithHostedSpeech(String message, String utteranceId, long sequence) {
        executor.execute(() -> {
            HttpURLConnection connection = null;
            AudioTrack track = null;
            try {
                if (!isCurrentSpeechSequence(sequence)) {
                    LocalLog.info("speech", "stop_reason=stale_sequence sequence=" + sequence);
                    return;
                }
                connection = hostedSpeechClient.openSpeechStream(message);
                if (!isCurrentSpeechSequence(sequence)) {
                    LocalLog.info("speech", "stop_reason=stale_sequence sequence=" + sequence);
                    return;
                }
                int sampleRate = hostedSpeechSampleRate(connection);
                int minBufferSize = AudioTrack.getMinBufferSize(sampleRate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
                if (minBufferSize <= 0) {
                    throw new IOException("Unable to create audio track buffer");
                }
                track = new AudioTrack.Builder()
                        .setAudioAttributes(new AudioAttributes.Builder()
                                .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                                .build())
                        .setAudioFormat(new AudioFormat.Builder()
                                .setSampleRate(sampleRate)
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
                    activeHostedSpeechTrack = track;
                    track.play();
                }
                byte[] pcm = readSpeechPcm(connection.getInputStream(), sequence);
                saveSpeechDebugPcm(pcm, "latest-hosted-speech");
                long receivedBytes = pcm.length;
                long writtenBytes = writePcmToTrack(track, pcm, sequence);
                waitForHostedSpeechPlaybackDrain(track, writtenBytes, sampleRate, sequence);
                long finalReceivedBytes = receivedBytes;
                long finalWrittenBytes = writtenBytes;
                if (isCurrentSpeechSequence(sequence)) {
                    main.post(() -> {
                        LocalLog.info("speech", "stop_reason=stream_complete receivedBytes=" + finalReceivedBytes + " writtenBytes=" + finalWrittenBytes);
                        finishSpeechPlaybackFor(utteranceId, "stream_complete");
                    });
                }
            } catch (Exception ex) {
                if (isCurrentSpeechSequence(sequence)) {
                    main.post(() -> {
                        if (!isCurrentSpeechSequence(sequence)) {
                            return;
                        }
                        String cause = speechFailureCause(ex);
                        LocalLog.info("speech", "stop_reason=hosted_speech_error detail=" + cause);
                        stopHostedSpeechPlayback("hosted_speech_error");
                        setStatus("Hosted narration failed: " + cause + ". Say resume reading to retry.");
                        finishSpeechPlaybackFor(utteranceId, "hosted_speech_error");
                    });
                }
            } finally {
                if (track != null) {
                    boolean releaseTrack;
                    synchronized (this) {
                        releaseTrack = activeHostedSpeechTrack == track;
                        if (releaseTrack) {
                            activeHostedSpeechTrack = null;
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
        if (lower.contains("endpoint returned http")) {
            return "Hosted speech HTTP error: " + message;
        }
        if (lower.contains("api returned http")) {
            return "Hosted provider API error: " + message;
        }
        if (lower.contains("connect") || lower.contains("failed to connect") || lower.contains("connection refused")) {
            return "Hosted speech gateway missing or unreachable: " + message;
        }
        if (lower.contains("stalled") || lower.contains("audio track") || lower.contains("write=")) {
            return "playback failure: " + message;
        }
        return "playback failure: " + message;
    }

    private void speakWithNativeTtsPrepared(String message, String utteranceId, long sequence, String nativeSpeechReason) {
        if (!isCurrentSpeechSequence(sequence)) {
            LocalLog.info("speech", "device_tts_skip_stale sequence=" + sequence);
            return;
        }
        if (deviceTextToSpeech != null && deviceTextToSpeechReady) {
            LocalLog.info("speech", "native_tts_request reason=" + shortMessage(nativeSpeechReason));
            setSpeechPlaying(true);
            configureDeviceTtsCompletionCallbacks();
            int result = deviceTextToSpeech.speak(message, TextToSpeech.QUEUE_FLUSH, null, utteranceId);
            if (result != TextToSpeech.ERROR) {
                return;
            }
            LocalLog.warn("speech", "device_tts_speak_failed cause=" + shortMessage(nativeSpeechReason));
        } else {
            LocalLog.warn("speech", "device_tts_unavailable ready=" + deviceTextToSpeechReady + " cause=" + shortMessage(nativeSpeechReason));
        }
        setStatus("Narration is unavailable right now: " + nativeSpeechReason + ".");
        finishSpeechPlaybackFor(utteranceId, "speech_unavailable");
    }

    private void configureDeviceTtsCompletionCallbacks() {
        if (deviceTextToSpeech == null) {
            return;
        }
        deviceTextToSpeech.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override
            public void onStart(String utteranceId) {
                LocalLog.info("speech", "device_tts_start utteranceId=" + utteranceId);
            }

            @Override
            public void onDone(String utteranceId) {
                main.post(() -> {
                    if (utteranceId != null && utteranceId.equals(activeSpeechUtteranceId)) {
                        LocalLog.info("speech", "device_tts_complete utteranceId=" + utteranceId);
                        finishSpeechPlaybackFor(utteranceId, "device_tts_complete");
                    }
                });
            }

            @Override
            public void onError(String utteranceId) {
                main.post(() -> {
                    if (utteranceId != null && utteranceId.equals(activeSpeechUtteranceId)) {
                        LocalLog.warn("speech", "device_tts_error utteranceId=" + utteranceId);
                        finishSpeechPlaybackFor(utteranceId, "device_tts_error");
                    }
                });
            }
        });
    }

    private String hostedSpeechResolvedVoiceName(HttpURLConnection connection) {
        return connection == null ? "" : firstNonEmpty(connection.getHeaderField("X-Speech-Voice"), "");
    }

    private String hostedSpeechResolvedVoiceId(HttpURLConnection connection) {
        return connection == null ? "" : firstNonEmpty(connection.getHeaderField("X-Speech-Voice-Id"), "");
    }

    private boolean isLegacySkylarVoice(String voiceName, String voiceId) {
        return LEGACY_DRIVE_NARRATOR_VOICE_ID.equalsIgnoreCase(voiceId == null ? "" : voiceId.trim())
                || LEGACY_DRIVE_NARRATOR_VOICE.equalsIgnoreCase(voiceName == null ? "" : voiceName.trim());
    }

    private int hostedSpeechSampleRate(HttpURLConnection connection) {
        if (connection != null) {
            String raw = connection.getHeaderField("X-Sample-Rate");
            try {
                int parsed = Integer.parseInt(raw == null ? "" : raw.trim());
                if (parsed >= 8000 && parsed <= 48000) {
                    return parsed;
                }
            } catch (Exception ignored) {
            }
        }
        return 24000;
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
                throw new IOException("Hosted speech audio playback failed: write=" + count + " receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes);
            }
            if (count == 0) {
                zeroWrites += 1;
                LocalLog.warn("speech", "audio_track_zero_write receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes + " zeroWrites=" + zeroWrites);
                if (zeroWrites > 500) {
                    throw new IOException("Hosted speech audio playback stalled: receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes);
                }
                SystemClock.sleep(20L);
                continue;
            }
            zeroWrites = 0;
            offset += count;
            writtenBytes += count;
        }
        if (offset < pcm.length && isCurrentSpeechSequence(sequence)) {
            throw new IOException("Hosted speech audio playback incomplete: receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes);
        }
        LocalLog.info("speech", "hosted_speech_pcm_write receivedBytes=" + pcm.length + " writtenBytes=" + writtenBytes);
        return writtenBytes;
    }

    private void waitForHostedSpeechPlaybackDrain(AudioTrack track, long writtenBytes, int sampleRate, long sequence) throws IOException {
        if (track == null || writtenBytes <= 0 || !isCurrentSpeechSequence(sequence)) {
            return;
        }
        long targetFrames = Math.max(1L, writtenBytes / 2L);
        long timeoutMs = Math.max(1200L, Math.min(30000L, (targetFrames * 1000L / Math.max(8000, sampleRate)) + 1500L));
        long started = SystemClock.elapsedRealtime();
        long lastPlayedFrames = Integer.toUnsignedLong(track.getPlaybackHeadPosition());
        while (isCurrentSpeechSequence(sequence)) {
            long playedFrames = Integer.toUnsignedLong(track.getPlaybackHeadPosition());
            lastPlayedFrames = playedFrames;
            if (playedFrames + 512L >= targetFrames) {
                LocalLog.info("speech", "hosted_speech_playback_drain playedFrames=" + playedFrames
                        + " targetFrames=" + targetFrames
                        + " waitMs=" + (SystemClock.elapsedRealtime() - started));
                return;
            }
            if (SystemClock.elapsedRealtime() - started > timeoutMs) {
                throw new IOException("Hosted speech audio playback drain timed out: playedFrames="
                        + playedFrames + " targetFrames=" + targetFrames + " writtenBytes=" + writtenBytes);
            }
            SystemClock.sleep(20L);
        }
        LocalLog.info("speech", "hosted_speech_playback_drain_cancelled playedFrames=" + lastPlayedFrames
                + " targetFrames=" + targetFrames);
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
            LocalLog.info("speech", "hosted_speech_debug_pcm path=" + file.getAbsolutePath() + " bytes=" + pcm.length);
        } catch (Exception ex) {
            LocalLog.warn("speech", "hosted_speech_debug_pcm_failed " + shortMessage(ex.getMessage()));
        }
    }

    private void stopHostedSpeechPlayback(String reason) {
        synchronized (this) {
            stopHostedSpeechPlaybackLocked(reason);
        }
    }

    private void stopSpeechPlayback() {
        synchronized (this) {
            speechSequence += 1L;
            LocalLog.info("speech", "stop_reason=user_stop sequence=" + speechSequence);
            stopHostedSpeechPlaybackLocked("user_stop");
            activeSpeechUtteranceId = "";
        }
        if (deviceTextToSpeech != null) {
            try {
                deviceTextToSpeech.stop();
            } catch (Exception ignored) {
            }
        }
        finishSpeechPlayback("user_stop");
        setStatus("Speech stopped.");
    }

    private void stopHostedSpeechPlaybackLocked(String reason) {
        if (activeHostedSpeechTrack != null) {
            LocalLog.info("speech", "stopping_active_track reason=" + reason);
            try {
                activeHostedSpeechTrack.stop();
            } catch (Exception ignored) {
            }
            activeHostedSpeechTrack.release();
            activeHostedSpeechTrack = null;
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
            speechFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                    .setAudioAttributes(attributes)
                    .setAcceptsDelayedFocusGain(false)
                    .setOnAudioFocusChangeListener(focusChange -> { })
                    .build();
        }
        LocalLog.info("audio", "audio_focus_request type=gain");
        speechFocusHeld = audioManager.requestAudioFocus(speechFocusRequest) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
    }

    private void finishSpeechPlaybackFor(String utteranceId, String reason) {
        if (utteranceId != null && !utteranceId.equals(activeSpeechUtteranceId)) {
            return;
        }
        boolean wasDocumentReader = activeDocumentReader != null
                && utteranceId != null
                && utteranceId.equals(activeDocumentReader.utteranceId);
        activeSpeechUtteranceId = "";
        finishSpeechPlayback(reason);
        if (wasDocumentReader) {
            continueDocumentReaderAfterSpeech(utteranceId, reason);
        }
    }

    private void finishSpeechPlayback(String reason) {
        LocalLog.info("audio", "media_key_handoff_disabled reason=" + reason);
        LocalLog.info("speech", "speech_cleanup reason=" + reason);
        setSpeechPlaying(false);
        abandonSpeechFocus();
    }

    private void abandonSpeechFocus() {
        if (audioManager != null && speechFocusRequest != null && speechFocusHeld) {
            audioManager.abandonAudioFocusRequest(speechFocusRequest);
            LocalLog.info("audio", "audio_focus_abandoned");
        }
        speechFocusHeld = false;
    }

    private void setStatus(String message) {
        if (message != null && !message.trim().isEmpty()) {
            LocalLog.info("status", shortMessage(message));
            showLoginShellEvent(shortMessage(message));
        }
        updateBackendStatus();
    }

    private void appendStatus(String message) {
        if (message != null && !message.trim().isEmpty()) {
            LocalLog.info("status", shortMessage(message));
            showLoginShellEvent(shortMessage(message));
        }
        updateBackendStatus();
    }

    private void setSpeechPlaying(boolean playing) {
        speechPlaying = playing;
        if (stopSpeechButton != null) {
            stopSpeechButton.setVisibility(playing && !narrationMuted ? View.VISIBLE : View.GONE);
        }
        updateSpeechMediaSession(playing);
        refreshDriveReaderPlayer();
    }

    private void toggleNarrationMute() {
        narrationMuted = !narrationMuted;
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_NARRATION_MUTED, narrationMuted).apply();
        LocalLog.info("speech", "narration_mute_toggle muted=" + narrationMuted);
        if (narrationMuted) {
            stopSpeechPlayback();
        } else {
            updateBackendStatus();
        }
        updateNarrationMuteButton();
    }

    private void updateNarrationMuteButton() {
        if (narrationMuteButton == null) {
            return;
        }
        narrationMuteButton.setText(narrationMuted ? "Unmute" : "Mute");
        narrationMuteButton.setContentDescription(narrationMuted ? "Narration muted. Tap to unmute." : "Narration on. Tap to mute.");
        narrationMuteButton.setBackgroundColor(narrationMuted ? COLOR_DANGER : COLOR_CARD);
    }

    private void updateDriveNarrationForegroundService() {
        DocumentReaderState reader = activeDocumentReader;
        boolean shouldRun = reader != null && !reader.cancelRequested && ((reader.playbackRequested && !reader.paused) || reader.renderRequested);
        if (reader != null && reader.playbackRequested && !reader.paused && !reader.cancelRequested) {
            reconcileDocumentPlaybackIfNeeded(reader, "foreground_service_update");
        }
        String title = reader == null ? "" : safeDisplayName(reader.name);
        if (shouldRun) {
            if (!driveNarrationForegroundRunning || !title.equals(driveNarrationForegroundTitle)) {
                Intent intent = new Intent(this, NarrationForegroundService.class)
                        .setAction(NarrationForegroundService.ACTION_START)
                        .putExtra(NarrationForegroundService.EXTRA_TITLE, title);
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(intent);
                    } else {
                        startService(intent);
                    }
                    driveNarrationForegroundRunning = true;
                    driveNarrationForegroundTitle = title;
                    LocalLog.info("doc_audio", "drive_narration_foreground_start title=" + shortMessage(title));
                } catch (Exception ex) {
                    LocalLog.warn("doc_audio", "drive_narration_foreground_start_failed " + shortMessage(ex.getMessage()));
                }
            }
            return;
        }
        if (driveNarrationForegroundRunning) {
            Intent intent = new Intent(this, NarrationForegroundService.class).setAction(NarrationForegroundService.ACTION_STOP);
            try {
                startService(intent);
            } catch (Exception ignored) {
                stopService(new Intent(this, NarrationForegroundService.class));
            }
            driveNarrationForegroundRunning = false;
            driveNarrationForegroundTitle = "";
            LocalLog.info("doc_audio", "drive_narration_foreground_stop");
        }
    }

    private void updateSpeechMediaSession(boolean playing) {
        if (speechMediaSession == null) {
            return;
        }
        DocumentReaderState reader = activeDocumentReader;
        long actions = PlaybackState.ACTION_STOP;
        int state = playing ? PlaybackState.STATE_PLAYING : PlaybackState.STATE_STOPPED;
        boolean active = playing;
        if (reader != null) {
            active = true;
            actions |= PlaybackState.ACTION_PLAY_PAUSE | PlaybackState.ACTION_SKIP_TO_NEXT | PlaybackState.ACTION_SKIP_TO_PREVIOUS;
            if (reader.paused || !reader.playbackRequested) {
                actions |= PlaybackState.ACTION_PLAY;
                state = PlaybackState.STATE_PAUSED;
            } else {
                actions |= PlaybackState.ACTION_PAUSE;
                state = PlaybackState.STATE_PLAYING;
            }
        } else {
            actions |= playing ? PlaybackState.ACTION_PAUSE : PlaybackState.ACTION_PLAY;
        }
        speechMediaSession.setPlaybackState(new PlaybackState.Builder()
                .setActions(actions)
                .setState(state, 0L, 1.0f)
                .build());
        speechMediaSession.setActive(active);
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

    private String agentFailureMessage(String source, String detail) {
        String clean = shortMessage(detail);
        String lower = clean.toLowerCase(Locale.US);
        String category = "provider";
        String workaround = "Retry once. If it repeats, say \"report this\" so I can preserve the exact failure.";
        if (lower.contains("unexpected end of stream") || lower.contains("unexpected end")) {
            category = "gateway connection closed before response";
            workaround = "Retry once. If it repeats, say \"report this\"; Home Center should return a bounded creative failure instead of stalling.";
        } else if (lower.contains("timeout") || lower.contains("timed out") || lower.contains("deadline")) {
            category = "timeout";
            workaround = "Try again with a narrower request or direct URL. If it repeats, say \"report this\".";
        } else if (lower.contains("network") || lower.contains("fetch") || lower.contains("econn") || lower.contains("enotfound")) {
            category = "network";
            workaround = "Try again, or give me the direct source URL/file name so I can avoid broad search.";
        } else if (lower.contains("401") || lower.contains("403") || lower.contains("auth") || lower.contains("permission") || lower.contains("scope")) {
            category = "authorization";
            workaround = "Reconnect Google or the relevant provider, then retry the same request.";
        } else if (lower.contains("json") || lower.contains("parse") || lower.contains("schema")) {
            category = "planner parse";
            workaround = "Say the request again more directly. If it repeats, report it as an agent parsing bug.";
        }
        return "I could not complete that because " + source + " hit a " + category + " problem."
                + "\n\nWhat failed: " + clean
                + "\n\nWorkaround: " + workaround;
    }

    private void updateBackendStatus() {
        if (statusView == null) {
            return;
        }
        boolean hasGateway = BuildConfig.AGENT_GATEWAY_BASE_URL != null && !BuildConfig.AGENT_GATEWAY_BASE_URL.trim().isEmpty();
        boolean hasDirectOpenAi = BuildConfig.OPENAI_API_KEY != null && !BuildConfig.OPENAI_API_KEY.trim().isEmpty();
        String gptState = (hasGateway || hasDirectOpenAi) ? "GPT-5.5" : "GPT offline";
        String speechState = narrationMuted ? "Muted" : (hasGateway ? driveSpeechProviderLabel() + " " + driveVoiceSummary() : "Native TTS");
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
                : "GPT-5.5, web search, Google tools, lists, TickTick, and Cartesia hosted narration routes through the gateway.";
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
        if (!user) {
            appendVisitButtons(row, text);
        }

        chatLogContainer.addView(row);
        chatLogContainer.post(() -> {
            scrollChatToBottom();
            captureVisualEvidenceIfDebugBuild("chat");
        });
    }

    private void appendVisitButtons(LinearLayout row, String text) {
        List<String> urls = extractChatUrls(text);
        if (urls.isEmpty()) {
            return;
        }
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams actionParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        actionParams.setMargins(0, dp(8), dp(42), 0);
        actions.setLayoutParams(actionParams);
        for (int i = 0; i < urls.size(); i++) {
            String url = urls.get(i);
            Button visit = button(visitButtonLabel(url, urls.size(), i), 16, "Visit link " + urlHostLabel(url));
            visit.setBackgroundColor(COLOR_ACCENT);
            visit.setTextColor(COLOR_BACKGROUND);
            visit.setMinHeight(dp(56));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    dp(56));
            params.setMargins(0, i == 0 ? 0 : dp(6), 0, 0);
            actions.addView(visit, params);
            visit.setOnClickListener(v -> openChatUrl(url));
        }
        row.addView(actions);
    }

    private List<String> extractChatUrls(String text) {
        List<String> urls = new ArrayList<>();
        if (text == null || text.trim().isEmpty()) {
            return urls;
        }
        Matcher matcher = CHAT_URL_PATTERN.matcher(text);
        while (matcher.find()) {
            String url = trimUrlPunctuation(matcher.group());
            if (!url.isEmpty() && !urls.contains(url)) {
                urls.add(url);
            }
        }
        return urls;
    }

    private String trimUrlPunctuation(String url) {
        String clean = url == null ? "" : url.trim();
        while (!clean.isEmpty() && ".,;:)\"'".indexOf(clean.charAt(clean.length() - 1)) >= 0) {
            clean = clean.substring(0, clean.length() - 1);
        }
        return clean;
    }

    private String visitButtonLabel(String url, int count, int index) {
        String host = urlHostLabel(url);
        if (count <= 1) {
            return "Visit " + host;
        }
        return "Visit " + (index + 1) + ": " + host;
    }

    private String urlHostLabel(String url) {
        try {
            String normalized = normalizeChatUrl(url);
            String host = Uri.parse(normalized).getHost();
            if (host == null || host.trim().isEmpty()) {
                return "link";
            }
            if (host.startsWith("www.")) {
                host = host.substring(4);
            }
            if (host.equals("docs.google.com")) {
                return "Google Doc";
            }
            return host;
        } catch (Exception ignored) {
            return "link";
        }
    }

    private String normalizeChatUrl(String url) {
        String clean = trimUrlPunctuation(url);
        if (clean.toLowerCase(Locale.US).startsWith("http://") || clean.toLowerCase(Locale.US).startsWith("https://")) {
            return clean;
        }
        return "https://" + clean;
    }

    private void openChatUrl(String url) {
        String normalized = normalizeChatUrl(url);
        if (normalized.trim().isEmpty()) {
            showAssistantMessage("No link is available.");
            return;
        }
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(normalized));
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            startActivity(intent);
            appendStatus("Opened link.");
            LocalLog.info("chat", "visit_link_opened host=" + urlHostLabel(normalized));
        } catch (Exception ex) {
            showAssistantMessage("Android could not open that link: " + shortMessage(ex.getMessage()));
        }
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
        try {
            JSONObject root = loadConversationStore();
            JSONObject conversation = activeConversation(root);
            conversation.put("summary", conversationSummary == null ? "" : conversationSummary.trim());
            conversation.put("turns", chatTurnsJson());
            conversation.put("updatedAt", System.currentTimeMillis());
            saveConversationStore(root);
        } catch (Exception ex) {
            LocalLog.warn("chat", "persist_conversation_failed: " + shortMessage(ex.getMessage()));
        }
    }

    private boolean restoreConversationHistory() {
        JSONObject root = loadConversationStore();
        JSONObject conversation = activeConversation(root);
        long now = System.currentTimeMillis();
        try {
            conversation.put("lastOpenedAt", now);
            saveConversationStore(root);
        } catch (Exception ignored) {
        }
        activeConversationId = conversation.optString("id", "");
        activeConversationTitle = conversation.optString("title", "New conversation");
        activeConversationTags = conversation.optJSONArray("tags") == null ? new JSONArray() : conversation.optJSONArray("tags");
        conversationSummary = clean(conversation.optString("summary", ""));
        refreshConversationHeader();
        JSONArray turns = conversation.optJSONArray("turns");
        chatTurns.clear();
        if (chatLogContainer != null) {
            chatLogContainer.removeAllViews();
        }
        boolean restored = false;
        if (!conversationSummary.isEmpty()) {
            appendChatBubble("Summary", conversationSummary, false, true);
            restored = true;
        }
        if (turns != null && turns.length() > 0) {
            boolean cleaned = false;
            for (int i = 0; i < turns.length(); i++) {
                ChatTurn turn = chatTurnFromJson(turns.optJSONObject(i));
                if (turn == null) {
                    continue;
                }
                if (ChatSystemShape.isStartupGreeting(turn.text)) {
                    cleaned = true;
                    continue;
                }
                chatTurns.add(turn);
                renderChatTurn(turn);
                restored = true;
            }
            if (cleaned) {
                persistChatHistory();
            }
        }
        if (restored) {
            appendStatus("Restored conversation: " + activeConversationTitle + ".");
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

    private ChatTurn chatTurnFromJson(JSONObject json) {
        if (json == null) {
            return null;
        }
        String role = json.optString("role", "").trim();
        String text = json.optString("text", "").trim();
        if (role.isEmpty() || text.isEmpty()) {
            return null;
        }
        JSONObject metadata = json.optJSONObject("metadata");
        return new ChatTurn(role, text, metadata == null ? null : cloneJson(metadata));
    }

    private JSONObject loadConversationStore() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String raw = prefs.getString(KEY_CONVERSATIONS_JSON, "");
        JSONObject root = null;
        if (raw != null && !raw.trim().isEmpty()) {
            try {
                root = new JSONObject(raw);
            } catch (Exception ex) {
                LocalLog.warn("chat", "conversation_store_parse_failed: " + shortMessage(ex.getMessage()));
            }
        }
        if (root == null) {
            root = new JSONObject();
        }
        try {
            if (root.optJSONArray("conversations") == null) {
                root.put("conversations", new JSONArray());
            }
            migrateLegacyConversationIfNeeded(root, prefs);
            if (root.optJSONArray("conversations").length() == 0) {
                JSONObject created = newConversationObject("New conversation");
                root.optJSONArray("conversations").put(created);
                activeConversationId = created.optString("id", "");
                prefs.edit().putString(KEY_ACTIVE_CONVERSATION_ID, activeConversationId).apply();
            }
        } catch (Exception ex) {
            LocalLog.warn("chat", "conversation_store_init_failed: " + shortMessage(ex.getMessage()));
        }
        return root;
    }

    private void migrateLegacyConversationIfNeeded(JSONObject root, SharedPreferences prefs) throws Exception {
        JSONArray conversations = root.optJSONArray("conversations");
        if (conversations == null || conversations.length() > 0) {
            return;
        }
        String summary = clean(prefs.getString(KEY_CHAT_SUMMARY, ""));
        String transcript = clean(prefs.getString(KEY_CHAT_TRANSCRIPT, ""));
        if (summary.isEmpty() && transcript.isEmpty()) {
            return;
        }
        JSONObject migrated = newConversationObject("Previous conversation");
        migrated.put("summary", summary);
        JSONArray turns = new JSONArray();
        if (!transcript.isEmpty()) {
            String[] lines = transcript.split("\n");
            for (String line : lines) {
                ChatTurn turn = chatTurnFromLine(line);
                if (turn != null && !ChatSystemShape.isStartupGreeting(turn.text)) {
                    turns.put(chatTurnJson(turn));
                }
            }
        }
        migrated.put("turns", turns);
        conversations.put(migrated);
        activeConversationId = migrated.optString("id", "");
        prefs.edit()
                .putString(KEY_ACTIVE_CONVERSATION_ID, activeConversationId)
                .remove(KEY_CHAT_TRANSCRIPT)
                .remove(KEY_CHAT_SUMMARY)
                .apply();
    }

    private void saveConversationStore(JSONObject root) {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(KEY_CONVERSATIONS_JSON, root == null ? "{}" : root.toString())
                .putString(KEY_ACTIVE_CONVERSATION_ID, activeConversationId == null ? "" : activeConversationId)
                .apply();
    }

    private JSONObject activeConversation(JSONObject root) {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        JSONArray conversations = root.optJSONArray("conversations");
        if (conversations == null) {
            conversations = new JSONArray();
            try {
                root.put("conversations", conversations);
            } catch (Exception ignored) {
            }
        }
        String activeId = activeConversationId == null || activeConversationId.trim().isEmpty()
                ? prefs.getString(KEY_ACTIVE_CONVERSATION_ID, "")
                : activeConversationId;
        JSONObject found = findConversation(root, activeId);
        if (found != null) {
            activeConversationId = found.optString("id", activeId);
            return found;
        }
        JSONObject first = conversations.length() == 0 ? null : conversations.optJSONObject(0);
        if (first != null) {
            activeConversationId = first.optString("id", "");
            return first;
        }
        JSONObject created = newConversationObject("New conversation");
        conversations.put(created);
        activeConversationId = created.optString("id", "");
        return created;
    }

    private JSONObject findConversation(JSONObject root, String conversationId) {
        if (conversationId == null || conversationId.trim().isEmpty()) {
            return null;
        }
        JSONArray conversations = root.optJSONArray("conversations");
        if (conversations == null) {
            return null;
        }
        for (int i = 0; i < conversations.length(); i++) {
            JSONObject conversation = conversations.optJSONObject(i);
            if (conversation != null && conversationId.equals(conversation.optString("id", ""))) {
                return conversation;
            }
        }
        return null;
    }

    private JSONObject newConversationObject(String title) {
        long now = System.currentTimeMillis();
        JSONObject json = new JSONObject();
        try {
            json.put("id", "conv-" + now + "-" + Math.abs((int) (Math.random() * 100000)));
            json.put("title", clean(title).isEmpty() ? "New conversation" : clean(title));
            json.put("tags", new JSONArray());
            json.put("summary", "");
            json.put("turns", new JSONArray());
            json.put("createdAt", now);
            json.put("updatedAt", now);
            json.put("lastOpenedAt", now);
        } catch (Exception ignored) {
        }
        return json;
    }

    private JSONArray chatTurnsJson() {
        JSONArray array = new JSONArray();
        int start = Math.max(0, chatTurns.size() - MAX_RECORDED_TURNS);
        for (int i = start; i < chatTurns.size(); i++) {
            array.put(chatTurnJson(chatTurns.get(i)));
        }
        return array;
    }

    private JSONObject chatTurnJson(ChatTurn turn) {
        JSONObject json = new JSONObject();
        try {
            json.put("role", turn.role == null ? "" : turn.role);
            json.put("text", turn.text == null ? "" : turn.text);
            if (turn.metadata != null) {
                json.put("metadata", cloneJson(turn.metadata));
            }
        } catch (Exception ignored) {
        }
        return json;
    }

    private void createAndSwitchConversation(String title) {
        persistChatHistory();
        JSONObject root = loadConversationStore();
        JSONArray conversations = root.optJSONArray("conversations");
        JSONObject conversation = newConversationObject(title);
        conversations.put(conversation);
        activeConversationId = conversation.optString("id", "");
        saveConversationStore(root);
        restoreConversationHistory();
        showAssistantMessage("New conversation started.");
    }

    private void switchConversation(String conversationId) {
        persistChatHistory();
        JSONObject root = loadConversationStore();
        JSONObject conversation = findConversation(root, conversationId);
        if (conversation == null) {
            showAssistantMessage("I could not find that conversation.");
            return;
        }
        activeConversationId = conversationId;
        try {
            conversation.put("lastOpenedAt", System.currentTimeMillis());
            saveConversationStore(root);
        } catch (Exception ignored) {
        }
        restoreConversationHistory();
    }

    private void refreshConversationHeader() {
        if (conversationTitleView == null) {
            return;
        }
        if (!legacyChatVisible) {
            conversationTitleView.setText("Narratable Docs");
            conversationTitleView.setContentDescription("Narratable Docs");
            return;
        }
        String title = clean(activeConversationTitle);
        if (title.isEmpty()) {
            title = "New conversation";
        }
        conversationTitleView.setText(title);
        conversationTitleView.setContentDescription("Current conversation: " + title);
    }

    private void showConversationList() {
        showConversationPanel();
    }

    private void showConversationPanel() {
        showConversationPanel("");
    }

    private void showConversationPanel(String rawQuery) {
        JSONObject root = loadConversationStore();
        String queryText = clean(rawQuery);
        String query = queryText.toLowerCase(Locale.US);
        List<JSONObject> conversations = new ArrayList<>();
        for (JSONObject conversation : sortedConversations(root)) {
            if (query.isEmpty() || conversationMatches(conversation, query)) {
                conversations.add(conversation);
            }
        }
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(20), dp(12), dp(20), dp(4));
        final AlertDialog[] holder = new AlertDialog[1];

        EditText search = singleLineEdit("Search conversations or #tag", queryText);
        panel.addView(search, matchHeight(dp(58)));

        LinearLayout searchActions = new LinearLayout(this);
        searchActions.setOrientation(LinearLayout.HORIZONTAL);
        Button searchButton = button("Search", 14, "Search saved conversations");
        Button clearButton = button("Clear", 14, "Clear conversation search");
        searchActions.addView(searchButton, new LinearLayout.LayoutParams(0, dp(48), 1f));
        LinearLayout.LayoutParams clearParams = new LinearLayout.LayoutParams(0, dp(48), 1f);
        clearParams.setMargins(dp(8), 0, 0, 0);
        searchActions.addView(clearButton, clearParams);
        panel.addView(searchActions, matchWrap());

        Button newConversation = button("New conversation", 16, "Start a new Home Center conversation");
        Button renameConversation = button("Rename current", 16, "Rename the current conversation");
        Button editTags = button("Edit tags", 16, "Edit tags for the current conversation");
        panel.addView(newConversation, matchHeight(dp(52)));
        panel.addView(renameConversation, matchHeight(dp(52)));
        panel.addView(editTags, matchHeight(dp(52)));

        TextView section = new TextView(this);
        section.setText(query.isEmpty() ? "Recent conversations" : "Matching conversations");
        section.setTextSize(13);
        section.setTypeface(Typeface.DEFAULT_BOLD);
        section.setTextColor(COLOR_SECONDARY);
        section.setPadding(0, dp(12), 0, dp(6));
        panel.addView(section, matchWrap());

        if (conversations.isEmpty()) {
            TextView empty = new TextView(this);
            empty.setText("No matching conversations.");
            empty.setTextColor(COLOR_SECONDARY);
            empty.setTextSize(16);
            empty.setPadding(0, dp(6), 0, dp(6));
            panel.addView(empty, matchWrap());
        }
        for (JSONObject conversation : conversations) {
            String id = conversation.optString("id", "");
            Button row = button(conversationRowLabel(conversation), 14, "Open conversation " + conversation.optString("title", ""));
            panel.addView(row, matchHeight(dp(64)));
            row.setOnClickListener(v -> {
                if (holder[0] != null) holder[0].dismiss();
                switchConversation(id);
            });
        }

        holder[0] = new AlertDialog.Builder(this)
                .setTitle("Conversations")
                .setView(panel)
                .setNegativeButton("Close", null)
                .create();
        searchButton.setOnClickListener(v -> {
            if (holder[0] != null) holder[0].dismiss();
            showConversationPanel(search.getText().toString());
        });
        clearButton.setOnClickListener(v -> {
            if (holder[0] != null) holder[0].dismiss();
            showConversationPanel("");
        });
        newConversation.setOnClickListener(v -> {
            if (holder[0] != null) holder[0].dismiss();
            createAndSwitchConversation("New conversation");
        });
        renameConversation.setOnClickListener(v -> {
            if (holder[0] != null) holder[0].dismiss();
            showRenameConversationDialog();
        });
        editTags.setOnClickListener(v -> {
            if (holder[0] != null) holder[0].dismiss();
            showEditConversationTagsDialog();
        });
        holder[0].show();
    }

    private void showRenameConversationDialog() {
        EditText title = singleLineEdit("Conversation title", activeConversationTitle);
        new AlertDialog.Builder(this)
                .setTitle("Rename conversation")
                .setView(title)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Save", (dialog, which) -> renameActiveConversation(title.getText().toString()))
                .show();
    }

    private void renameActiveConversation(String title) {
        JSONObject root = loadConversationStore();
        JSONObject conversation = activeConversation(root);
        try {
            String cleanTitle = clean(title);
            conversation.put("title", cleanTitle.isEmpty() ? "New conversation" : cleanTitle);
            conversation.put("updatedAt", System.currentTimeMillis());
            activeConversationTitle = conversation.optString("title", "New conversation");
            saveConversationStore(root);
            refreshConversationHeader();
            showAssistantMessage("Conversation renamed to " + activeConversationTitle + ".");
        } catch (Exception ex) {
            showAssistantMessage("Could not rename conversation: " + shortMessage(ex.getMessage()));
        }
    }

    private void showEditConversationTagsDialog() {
        EditText tags = singleLineEdit("Tags, comma separated", tagsText(activeConversationTags));
        new AlertDialog.Builder(this)
                .setTitle("Edit tags")
                .setView(tags)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Save", (dialog, which) -> saveActiveConversationTags(tags.getText().toString()))
                .show();
    }

    private void saveActiveConversationTags(String tagsText) {
        JSONObject root = loadConversationStore();
        JSONObject conversation = activeConversation(root);
        try {
            JSONArray tags = parseTags(tagsText);
            conversation.put("tags", tags);
            conversation.put("updatedAt", System.currentTimeMillis());
            activeConversationTags = tags;
            saveConversationStore(root);
            showAssistantMessage("Conversation tags saved.");
        } catch (Exception ex) {
            showAssistantMessage("Could not save tags: " + shortMessage(ex.getMessage()));
        }
    }

    private void showConversationSearchDialog() {
        showConversationPanel("");
    }

    private void showConversationSearchResults(String rawQuery) {
        showConversationPanel(rawQuery);
    }

    private List<JSONObject> sortedConversations(JSONObject root) {
        JSONArray array = root.optJSONArray("conversations");
        List<JSONObject> list = new ArrayList<>();
        if (array != null) {
            for (int i = 0; i < array.length(); i++) {
                JSONObject conversation = array.optJSONObject(i);
                if (conversation != null) {
                    list.add(conversation);
                }
            }
        }
        Collections.sort(list, (left, right) -> Long.compare(right.optLong("lastOpenedAt", 0L), left.optLong("lastOpenedAt", 0L)));
        return list;
    }

    private String conversationRowLabel(JSONObject conversation) {
        String title = conversation.optString("title", "New conversation");
        String tags = tagsText(conversation.optJSONArray("tags"));
        String preview = conversationPreview(conversation);
        String label = title;
        if (!tags.isEmpty()) {
            label += "  #" + tags.replace(", ", " #");
        }
        if (!preview.isEmpty()) {
            label += "\n" + preview;
        }
        return label;
    }

    private String conversationPreview(JSONObject conversation) {
        JSONArray turns = conversation.optJSONArray("turns");
        if (turns != null && turns.length() > 0) {
            JSONObject last = turns.optJSONObject(turns.length() - 1);
            if (last != null) {
                return shortMessage(last.optString("text", ""));
            }
        }
        return shortMessage(conversation.optString("summary", ""));
    }

    private boolean conversationMatches(JSONObject conversation, String query) {
        if (query.startsWith("#")) {
            String tag = normalizeTag(query.substring(1));
            JSONArray tags = conversation.optJSONArray("tags");
            for (int i = 0; tags != null && i < tags.length(); i++) {
                if (tag.equals(tags.optString(i, ""))) {
                    return true;
                }
            }
            return false;
        }
        String haystack = (conversation.optString("title", "") + "\n"
                + tagsText(conversation.optJSONArray("tags")) + "\n"
                + conversation.optString("summary", "") + "\n"
                + conversationTurnsText(conversation)).toLowerCase(Locale.US);
        return haystack.contains(query);
    }

    private String conversationTurnsText(JSONObject conversation) {
        JSONArray turns = conversation.optJSONArray("turns");
        StringBuilder builder = new StringBuilder();
        for (int i = 0; turns != null && i < turns.length(); i++) {
            JSONObject turn = turns.optJSONObject(i);
            if (turn != null) {
                builder.append(turn.optString("text", "")).append('\n');
            }
        }
        return builder.toString();
    }

    private JSONArray parseTags(String raw) {
        JSONArray array = new JSONArray();
        String[] parts = (raw == null ? "" : raw).split(",");
        for (String part : parts) {
            String tag = normalizeTag(part);
            if (tag.isEmpty() || jsonArrayContains(array, tag)) {
                continue;
            }
            array.put(tag);
        }
        return array;
    }

    private String normalizeTag(String value) {
        return clean(value).toLowerCase(Locale.US).replace("#", "").replaceAll("\\s+", "-");
    }

    private boolean jsonArrayContains(JSONArray array, String value) {
        for (int i = 0; i < array.length(); i++) {
            if (value.equals(array.optString(i, ""))) {
                return true;
            }
        }
        return false;
    }

    private String tagsText(JSONArray tags) {
        if (tags == null || tags.length() == 0) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < tags.length(); i++) {
            String tag = tags.optString(i, "");
            if (tag.isEmpty()) {
                continue;
            }
            if (builder.length() > 0) {
                builder.append(", ");
            }
            builder.append(tag);
        }
        return builder.toString();
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

    private static final class AttachmentMetadata {
        final String displayName;
        final String mimeType;
        final long sizeBytes;

        AttachmentMetadata(String displayName, String mimeType, long sizeBytes) {
            this.displayName = displayName == null || displayName.trim().isEmpty() ? "attachment" : displayName.trim();
            this.mimeType = mimeType == null ? "" : mimeType.trim();
            this.sizeBytes = sizeBytes;
        }
    }


    private static final class DriveFolderCrumb {
        final String id;
        final String name;
        DriveFolderCrumb(String id, String name) {
            this.id = id == null ? "" : id;
            this.name = name == null || name.trim().isEmpty() ? "My Drive" : name.trim();
        }
    }


    private static final class CandidateSpeakerProfile {
        final String characterId;
        final String characterName;
        final String sourceId;
        final String sourceName;
        final String cueType;

        CandidateSpeakerProfile(String characterName, String sourceId, String sourceName, String cueType) {
            this.characterName = cleanName(characterName);
            this.characterId = CharacterVoiceRule.normalizeId(this.characterName);
            this.sourceId = sourceId == null ? "" : sourceId.trim();
            this.sourceName = sourceName == null || sourceName.trim().isEmpty() ? "Google Doc" : sourceName.trim();
            this.cueType = cueType == null ? "structured-cue" : cueType.trim();
        }

        static List<CandidateSpeakerProfile> extract(String text, String sourceId, String sourceName) {
            List<CandidateSpeakerProfile> found = new ArrayList<>();
            String raw = text == null ? "" : text;
            Matcher tagMatcher = Pattern.compile("(?i)\\[(?:speaker|voice):([^\\]]+)\\]").matcher(raw);
            while (tagMatcher.find()) add(found, tagMatcher.group(1), sourceId, sourceName, "tag");
            String[] lines = raw.split("\\r?\\n");
            Pattern heading = Pattern.compile("^\\s*([A-Z][A-Z0-9 .\\'\\-]{1,48})\\s*:\\s+\\S.*$");
            for (String line : lines) {
                Matcher matcher = heading.matcher(line == null ? "" : line);
                if (matcher.matches()) add(found, matcher.group(1), sourceId, sourceName, "speaker-heading");
            }
            return found;
        }

        private static void add(List<CandidateSpeakerProfile> found, String name, String sourceId, String sourceName, String cueType) {
            String clean = cleanName(name);
            if (clean.length() < 2 || clean.length() > 48) return;
            String id = CharacterVoiceRule.normalizeId(clean);
            if ("voice".equals(id) || "speaker".equals(id) || "narrator".equals(id) || "section".equals(id)
                    || VoiceScriptPlanner.DEFAULT_DIALOGUE_SPEAKER.equals(id)) return;
            for (CandidateSpeakerProfile existing : found) {
                if (existing.characterId.equals(id)) return;
            }
            found.add(new CandidateSpeakerProfile(clean, sourceId, sourceName, cueType));
        }

        private static String cleanName(String value) {
            String clean = value == null ? "" : value.replaceAll("[_-]+", " ").replaceAll("\\s+", " ").trim();
            if (clean.isEmpty()) return "";
            if (clean.equals(clean.toUpperCase(Locale.US))) clean = titleCase(clean);
            return clean;
        }

        private static String titleCase(String value) {
            String[] parts = value.toLowerCase(Locale.US).split(" ");
            StringBuilder out = new StringBuilder();
            for (String part : parts) {
                if (part.isEmpty()) continue;
                if (out.length() > 0) out.append(' ');
                out.append(Character.toUpperCase(part.charAt(0))).append(part.length() > 1 ? part.substring(1) : "");
            }
            return out.toString();
        }
    }

    private static final class VoiceCatalogEntry {
        final String voiceId;
        final String name;
        final String category;
        final String description;
        final String labelsText;

        VoiceCatalogEntry(String voiceId, String name, String category, String description, String labelsText) {
            this.voiceId = voiceId == null ? "" : voiceId.trim();
            this.name = name == null ? "" : name.trim();
            this.category = category == null ? "" : category.trim();
            this.description = description == null ? "" : description.trim();
            this.labelsText = labelsText == null ? "" : labelsText.trim();
        }

        static List<VoiceCatalogEntry> fromArray(JSONArray array) {
            List<VoiceCatalogEntry> entries = new ArrayList<>();
            if (array == null) return entries;
            for (int i = 0; i < array.length(); i++) {
                JSONObject json = array.optJSONObject(i);
                VoiceCatalogEntry entry = fromJson(json);
                if (entry != null) entries.add(entry);
            }
            return entries;
        }

        static List<VoiceCatalogEntry> fromCache(String jsonText) {
            try {
                if (jsonText == null || jsonText.trim().isEmpty()) return new ArrayList<>();
                return fromArray(new JSONArray(jsonText));
            } catch (Exception ex) {
                return new ArrayList<>();
            }
        }

        static VoiceCatalogEntry fromJson(JSONObject json) {
            if (json == null) return null;
            String name = json.optString("name", "").trim();
            if (name.isEmpty()) return null;
            Object labels = json.opt("labels");
            return new VoiceCatalogEntry(json.optString("voiceId", ""), name, json.optString("category", ""), json.optString("description", ""), CharacterVoiceRule.firstNonEmptyStatic(json.optString("labelsText", ""), labels == null ? "" : labels.toString()));
        }

        static VoiceCatalogEntry chooseForSpeaker(String speakerId, List<VoiceCatalogEntry> catalog, int offset) {
            if (catalog == null || catalog.isEmpty()) return null;
            List<VoiceCatalogEntry> usable = new ArrayList<>();
            for (VoiceCatalogEntry entry : catalog) {
                if (entry == null || entry.name.isEmpty()) continue;
                if (entry.name.equalsIgnoreCase(DEFAULT_DRIVE_NARRATOR_VOICE)) continue;
                usable.add(entry);
            }
            if (usable.isEmpty()) usable.addAll(catalog);
            int index = Math.abs((speakerId == null ? "" : speakerId).hashCode() + offset) % usable.size();
            return usable.get(index);
        }

        static String categorySummary(List<VoiceCatalogEntry> catalog) {
            if (catalog == null || catalog.isEmpty()) return "No voice metadata cached.";
            List<String> categories = new ArrayList<>();
            for (VoiceCatalogEntry entry : catalog) {
                String bucket = entry == null || entry.category.isEmpty() ? "uncategorized" : entry.category;
                boolean seen = false;
                for (String existing : categories) if (existing.startsWith(bucket + "=")) seen = true;
                if (!seen) categories.add(bucket + "=" + countCategory(catalog, bucket));
            }
            return "Categories: " + join(categories, ", ") + ".";
        }

        private static int countCategory(List<VoiceCatalogEntry> catalog, String category) {
            int count = 0;
            for (VoiceCatalogEntry entry : catalog) {
                String bucket = entry == null || entry.category.isEmpty() ? "uncategorized" : entry.category;
                if (bucket.equals(category)) count++;
            }
            return count;
        }

        String voiceInput() { return name.isEmpty() && !voiceId.isEmpty() ? "voice_id:" + voiceId : name; }

        String displayLine() {
            StringBuilder out = new StringBuilder(name.isEmpty() ? voiceId : name);
            if (!voiceId.isEmpty()) out.append(" | ").append(voiceId);
            if (!category.isEmpty()) out.append(" | ").append(category);
            String meta = CharacterVoiceRule.firstNonEmptyStatic(description, labelsText);
            if (!meta.isEmpty()) out.append(" | ").append(meta.length() > 90 ? meta.substring(0, 90) : meta);
            return out.toString();
        }

        JSONObject toJson() throws Exception {
            return new JSONObject().put("voiceId", voiceId).put("name", name).put("category", category).put("description", description).put("labelsText", labelsText);
        }

        private static String join(List<String> values, String separator) {
            StringBuilder out = new StringBuilder();
            if (values != null) for (String value : values) {
                if (value == null || value.trim().isEmpty()) continue;
                if (out.length() > 0) out.append(separator);
                out.append(value.trim());
            }
            return out.toString();
        }
    }


    private static final class CharacterVoiceRegistry {
        final List<CharacterVoiceRule> rules;

        CharacterVoiceRegistry(List<CharacterVoiceRule> rules) {
            this.rules = rules == null || rules.isEmpty() ? defaultRules() : rules;
        }

        static CharacterVoiceRegistry defaults() {
            return new CharacterVoiceRegistry(defaultRules());
        }

        static CharacterVoiceRegistry fromAsset(Context context) {
            if (context == null) return defaults();
            try (InputStream input = context.getAssets().open("home_drive_character_voice_registry.md")) {
                ByteArrayOutputStream output = new ByteArrayOutputStream();
                byte[] buffer = new byte[4096];
                int read;
                while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
                return parse(output.toString(StandardCharsets.UTF_8.name()));
            } catch (Exception ex) {
                return defaults();
            }
        }

        static CharacterVoiceRegistry fromCache(String jsonText) {
            try {
                if (jsonText == null || jsonText.trim().isEmpty()) return defaults();
                JSONArray array = new JSONObject(jsonText).optJSONArray("rules");
                List<CharacterVoiceRule> parsed = new ArrayList<>();
                if (array != null) {
                    for (int i = 0; i < array.length(); i++) {
                        CharacterVoiceRule rule = CharacterVoiceRule.fromJson(array.optJSONObject(i));
                        if (rule != null) parsed.add(rule);
                    }
                }
                return parsed.isEmpty() ? defaults() : new CharacterVoiceRegistry(parsed);
            } catch (Exception ex) {
                return defaults();
            }
        }

        static CharacterVoiceRegistry fromCacheMergedWithAsset(String jsonText, CharacterVoiceRegistry assetRegistry) {
            CharacterVoiceRegistry cached = fromCache(jsonText);
            List<CharacterVoiceRule> merged = new ArrayList<>();
            if (assetRegistry != null && assetRegistry.rules != null) {
                for (CharacterVoiceRule rule : assetRegistry.rules) if (rule != null && !containsCharacter(merged, rule.characterId)) merged.add(rule);
            }
            if (cached.rules != null) {
                for (CharacterVoiceRule rule : cached.rules) if (rule != null && !containsCharacter(merged, rule.characterId)) merged.add(rule);
            }
            return merged.isEmpty() ? defaults() : new CharacterVoiceRegistry(merged);
        }

        private static boolean containsCharacter(List<CharacterVoiceRule> rules, String characterId) {
            String clean = CharacterVoiceRule.normalizeId(characterId);
            if (rules == null || clean.isEmpty()) return false;
            for (CharacterVoiceRule rule : rules) if (rule != null && rule.characterId.equals(clean)) return true;
            return false;
        }

        static CharacterVoiceRegistry parse(String documentText) {
            List<CharacterVoiceRule> parsed = new ArrayList<>();
            String[] lines = (documentText == null ? "" : documentText).split("\\r?\\n");
            for (String line : lines) {
                String clean = line == null ? "" : line.trim();
                if (!clean.startsWith("|") || clean.toLowerCase(Locale.US).contains("| character |") || clean.matches("^\\|[\\s:-]+\\|.*")) continue;
                String[] cells = clean.split("\\|", -1);
                if (cells.length < 8) continue;
                CharacterVoiceRule rule = CharacterVoiceRule.fromCells(cells);
                if (rule != null) parsed.add(rule);
            }
            return parsed.isEmpty() ? defaults() : new CharacterVoiceRegistry(parsed);
        }

        CharacterVoiceRule defaultNarrator() {
            for (CharacterVoiceRule rule : rules) {
                if ("she-raw".equals(rule.characterId)) return rule;
            }
            return defaultRules().get(0);
        }

        CharacterVoiceRule match(String text) {
            String speakerId = VoiceScriptPlanner.structuralSpeakerId(text);
            if (speakerId.isEmpty()) return defaultNarrator();
            CharacterVoiceRule matched = structuralRule(speakerId);
            return matched == null ? dialogueDefault() : matched;
        }

        boolean hasExplicitCastSignal(String text, CharacterVoiceRule rule) {
            String speakerId = VoiceScriptPlanner.structuralSpeakerId(text);
            if (speakerId.isEmpty() || VoiceScriptPlanner.DEFAULT_DIALOGUE_SPEAKER.equals(speakerId) || rule == null) {
                return false;
            }
            return rule.characterId.equals(speakerId);
        }

        private CharacterVoiceRule structuralRule(String speakerId) {
            String clean = CharacterVoiceRule.normalizeId(speakerId);
            for (CharacterVoiceRule rule : rules) {
                if (rule == null) continue;
                if (rule.characterId.equals(clean)
                        || CharacterVoiceRule.normalizeId(rule.characterName).equals(clean)
                        || CharacterVoiceRule.normalizeId(rule.aliases).equals(clean)) {
                    return rule;
                }
                for (String alias : rule.searchAliases()) {
                    if (CharacterVoiceRule.normalizeId(alias).equals(clean)) return rule;
                }
            }
            return null;
        }

        private CharacterVoiceRule dialogueDefault() {
            List<String> tags = new ArrayList<>();
            tags.add("[speaker:" + VoiceScriptPlanner.DEFAULT_DIALOGUE_SPEAKER + "]");
            return new CharacterVoiceRule(
                    VoiceScriptPlanner.DEFAULT_DIALOGUE_SPEAKER,
                    "Dialogue default",
                    "Dialogue default",
                    "",
                    "dialogue",
                    false,
                    tags,
                    "",
                    "balanced quote without an explicit or grammatical speaker attribution");
        }

        boolean hasEntries() { return rules != null && !rules.isEmpty(); }
        int size() { return rules == null ? 0 : rules.size(); }

        boolean hasDialogueEntries() { return dialogueCount() > 0; }

        int dialogueCount() {
            int count = 0;
            if (rules != null) for (CharacterVoiceRule rule : rules) if (isAuditionable(rule)) count++;
            return count;
        }

        List<CharacterVoiceRule> dialogueRules(int limit) {
            List<CharacterVoiceRule> values = new ArrayList<>();
            if (rules == null) return values;
            for (CharacterVoiceRule rule : rules) {
                if (!isAuditionable(rule)) continue;
                values.add(rule);
                if (limit > 0 && values.size() >= limit) break;
            }
            return values;
        }

        int dialogueOrdinal(String characterId) {
            String clean = CharacterVoiceRule.normalizeId(characterId);
            int ordinal = 0;
            if (rules == null) return 0;
            for (CharacterVoiceRule rule : rules) {
                if (!isAuditionable(rule)) continue;
                if (rule.characterId.equals(clean)) return ordinal;
                ordinal++;
            }
            return Math.max(0, ordinal);
        }

        private boolean isAuditionable(CharacterVoiceRule rule) {
            if (rule == null) return false;
            String role = rule.narrationRole == null ? "" : rule.narrationRole.trim().toLowerCase(Locale.US);
            return ("dialogue".equals(role) || "notes".equals(role)) && !"she-raw".equals(rule.characterId);
        }

        MergeResult mergeCandidates(List<CandidateSpeakerProfile> candidates, List<VoiceCatalogEntry> catalog) {
            int added = 0;
            StringBuilder names = new StringBuilder();
            if (candidates == null) return new MergeResult(0, "none");
            for (CandidateSpeakerProfile candidate : candidates) {
                if (candidate == null || candidate.characterId.isEmpty() || hasCharacter(candidate.characterId)) continue;
                VoiceCatalogEntry selected = VoiceCatalogEntry.chooseForSpeaker(candidate.characterId, catalog, added);
                String voiceAlias = selected == null ? "" : selected.name;
                String assignment = selected == null ? "voice metadata pending; defaults to Cartesia" : "auto voice metadata: " + selected.displayLine();
                List<String> tags = new ArrayList<>();
                tags.add("[voice:" + candidate.characterId + "]");
                tags.add("[speaker:" + candidate.characterName + "]");
                tags.add(candidate.characterName + ":");
                rules.add(new CharacterVoiceRule(
                        candidate.characterId,
                        candidate.characterName,
                        candidate.characterName,
                        voiceAlias,
                        "dialogue",
                        true,
                        tags,
                        "artificial voice pitch; satisfying acoustic distortion",
                        "auto-ingested from " + candidate.sourceName + " via " + candidate.cueType + "; " + assignment));
                if (names.length() > 0) names.append(", ");
                names.append(candidate.characterName);
                added++;
            }
            return new MergeResult(added, names.length() == 0 ? "none" : names.toString());
        }

        boolean hasCharacter(String characterId) {
            String clean = CharacterVoiceRule.normalizeId(characterId);
            for (CharacterVoiceRule rule : rules) {
                if (rule.characterId.equals(clean)) return true;
            }
            return false;
        }

        String toMarkdown() {
            StringBuilder out = new StringBuilder();
            out.append("# ").append(DRIVE_CHARACTER_REGISTRY_TITLE).append("\n\n");
            out.append("## Precedence Rules\n\n");
            out.append("1. Explicit voice tags win: `[voice:id]` or registered `[speaker:name]` tags control a section.\n");
            out.append("2. Structured speaker cues encountered in documents are auto-ingested as durable cross-document profiles.\n");
            out.append("3. Cartesia is the default narrator provider; ElevenLabs is explicit render-only in speech settings.\n");
            out.append("4. Acoustic direction is a rendering directive, not a local PCM distortion requirement in v1.\n\n");
            out.append("| Character | Aliases | Voice Alias | Narration Role | Always Applies | Match Tags | Acoustic Direction | Notes |\n");
            out.append("|---|---|---|---|---|---|---|---|\n");
            for (CharacterVoiceRule rule : rules) {
                out.append("| ").append(mdCell(rule.characterName))
                        .append(" | ").append(mdCell(rule.aliases))
                        .append(" | ").append(mdCell(rule.voiceAlias))
                        .append(" | ").append(mdCell(rule.narrationRole))
                        .append(" | ").append(rule.alwaysApplies ? "yes" : "no")
                        .append(" | ").append(mdCell(joinTags(rule.matchTags)))
                        .append(" | ").append(mdCell(rule.acousticDirection))
                        .append(" | ").append(mdCell(rule.notes))
                        .append(" |\n");
            }
            return out.toString();
        }

        private static String joinTags(List<String> tags) {
            StringBuilder builder = new StringBuilder();
            if (tags != null) for (String tag : tags) {
                if (tag == null || tag.trim().isEmpty()) continue;
                if (builder.length() > 0) builder.append(", ");
                builder.append(tag.trim());
            }
            return builder.toString();
        }

        private static String mdCell(String value) {
            return value == null ? "" : value.replace("|", "/").replaceAll("\\s+", " ").trim();
        }

        static final class MergeResult {
            final int added;
            final String names;
            MergeResult(int added, String names) {
                this.added = added;
                this.names = names == null ? "" : names;
            }
        }

        JSONObject toJson() throws Exception {
            JSONArray array = new JSONArray();
            for (CharacterVoiceRule rule : rules) array.put(rule.toJson());
            return new JSONObject().put("title", DRIVE_CHARACTER_REGISTRY_TITLE).put("rules", array);
        }

        private static List<CharacterVoiceRule> defaultRules() {
            List<CharacterVoiceRule> defaults = new ArrayList<>();
            defaults.add(new CharacterVoiceRule("she-raw", "She-Raw", "She Raw", "", "narrator", true, listOf("[voice:she-raw]", "[voice:sheraw]"), "artificial voice pitch; satisfying acoustic distortion", "Narrator identity; provider voice defaults to Cartesia unless overridden."));
            return defaults;
        }

        private static List<String> listOf(String first, String second) {
            List<String> values = new ArrayList<>();
            values.add(first);
            values.add(second);
            return values;
        }

        private static List<String> listOf(String first) {
            List<String> values = new ArrayList<>();
            values.add(first);
            return values;
        }
    }

    private static final class CharacterVoiceRule {
        final String characterId;
        final String characterName;
        final String aliases;
        final String voiceAlias;
        final String narrationRole;
        final boolean alwaysApplies;
        final List<String> matchTags;
        final String acousticDirection;
        final String notes;

        CharacterVoiceRule(String characterId, String characterName, String aliases, String voiceAlias, String narrationRole, boolean alwaysApplies, List<String> matchTags, String acousticDirection, String notes) {
            this.characterId = firstNonEmptyStatic(characterId, normalizeId(characterName));
            this.characterName = firstNonEmptyStatic(characterName, this.characterId);
            this.aliases = aliases == null ? "" : aliases.trim();
            this.voiceAlias = voiceAlias == null ? "" : voiceAlias.trim();
            this.narrationRole = firstNonEmptyStatic(narrationRole, "narrator").toLowerCase(Locale.US);
            this.alwaysApplies = alwaysApplies;
            this.matchTags = matchTags == null || matchTags.isEmpty() ? new ArrayList<>() : matchTags;
            this.acousticDirection = firstNonEmptyStatic(acousticDirection, "artificial voice pitch; satisfying acoustic distortion");
            this.notes = notes == null ? "" : notes.trim();
        }

        static CharacterVoiceRule synthetic(String characterId, String characterName, String voiceAlias, String narrationRole, String notes) {
            List<String> tags = new ArrayList<>();
            tags.add("[voice:" + normalizeId(characterId) + "]");
            return new CharacterVoiceRule(normalizeId(characterId), characterName, characterName, voiceAlias, narrationRole, true, tags, "registry voice fallback lane", notes);
        }

        static CharacterVoiceRule fromCells(String[] cells) {
            String character = cell(cells, 1);
            if (character.isEmpty()) return null;
            String tags = cell(cells, 6);
            return new CharacterVoiceRule(
                    normalizeId(character),
                    character,
                    cell(cells, 2),
                    cell(cells, 3),
                    cell(cells, 4),
                    cell(cells, 5).toLowerCase(Locale.US).contains("yes") || cell(cells, 5).toLowerCase(Locale.US).contains("true"),
                    parseTags(tags),
                    cell(cells, 7),
                    cell(cells, 8));
        }

        static CharacterVoiceRule fromJson(JSONObject json) {
            if (json == null) return null;
            JSONArray tags = json.optJSONArray("matchTags");
            List<String> parsedTags = new ArrayList<>();
            if (tags != null) for (int i = 0; i < tags.length(); i++) parsedTags.add(tags.optString(i, ""));
            return new CharacterVoiceRule(
                    json.optString("characterId", ""),
                    json.optString("character", ""),
                    json.optString("aliases", ""),
                    json.optString("voiceAlias", ""),
                    json.optString("narrationRole", "narrator"),
                    json.optBoolean("alwaysApplies", false),
                    parsedTags,
                    json.optString("acousticDirection", ""),
                    json.optString("notes", ""));
        }

        JSONObject toJson() throws Exception {
            JSONArray tags = new JSONArray();
            for (String tag : matchTags) tags.put(tag);
            return new JSONObject()
                    .put("characterId", characterId)
                    .put("character", characterName)
                    .put("aliases", aliases)
                    .put("voiceAlias", voiceAlias)
                    .put("narrationRole", narrationRole)
                    .put("alwaysApplies", alwaysApplies)
                    .put("matchTags", tags)
                    .put("acousticDirection", acousticDirection)
                    .put("notes", notes);
        }

        private static String cell(String[] cells, int index) {
            return index >= 0 && index < cells.length ? cells[index].trim() : "";
        }

        List<String> searchAliases() {
            List<String> values = new ArrayList<>();
            addSearchAlias(values, characterName);
            addSearchAlias(values, characterId.replace('-', ' '));
            String[] parts = (aliases == null ? "" : aliases).split(",");
            for (String part : parts) addSearchAlias(values, part);
            return values;
        }

        private static void addSearchAlias(List<String> values, String value) {
            String clean = value == null ? "" : value.replaceAll("\\[[^\\]]+\\]", " ").replaceAll("[^A-Za-z0-9 .\'-]+", " ").replaceAll("\\s+", " ").trim();
            if (clean.length() < 2) return;
            for (String existing : values) if (existing.equalsIgnoreCase(clean)) return;
            values.add(clean);
        }

        private static List<String> parseTags(String text) {
            List<String> tags = new ArrayList<>();
            String[] parts = (text == null ? "" : text).split(",");
            for (String part : parts) {
                String clean = part == null ? "" : part.trim();
                if (!clean.isEmpty()) tags.add(clean);
            }
            return tags;
        }

        static String normalizeId(String value) {
            String clean = value == null ? "" : value.toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", "-").replaceAll("^-|-$", "");
            return clean.isEmpty() ? "character" : clean;
        }

        static String firstNonEmptyStatic(String value, String fallback) {
            return value == null || value.trim().isEmpty() ? fallback : value.trim();
        }
    }

    private static final class MarkdownNarrationDocument {
        static final String COMPILER_ID = "drive-markdown-narrator-v6-structural-quote-boundaries";
        private static final Pattern SPEAKER_CUE_PATTERN = Pattern.compile("^\\s*([A-Za-z][A-Za-z0-9 .\\'\\-]{1,48})\\s*:\\s+(.+)$");
        private static final Pattern SPEAKER_DASH_PATTERN = Pattern.compile("^\\s*([A-Za-z][A-Za-z0-9 .\\'\\-]{1,48})\\s*(?:[-–—]|\\|)\\s+(.+)$");
        private static final String DIALOGUE_VERBS = "said|says|asked|asks|replied|replies|answered|answers|called|calls|whispered|whispers|shouted|shouts|muttered|mutters|continued|continues|snapped|snaps|sighed|sighs|said softly|said quietly";
        private static final Pattern TRAILING_ATTRIBUTION_PATTERN = Pattern.compile("^\\s*[\\\"“](.+?)[\\\"”][,!?\\.]*\\s+([A-Z][A-Za-z0-9 .\\'\\-]{1,48})\\s+(?:" + DIALOGUE_VERBS + ")\\b.*$", Pattern.CASE_INSENSITIVE);
        private static final Pattern SAID_BEFORE_QUOTE_PATTERN = Pattern.compile("^\\s*([A-Z][A-Za-z0-9 .\\'\\-]{1,48})\\s+(?:" + DIALOGUE_VERBS + ")\\b[^\\\"“]*[\\\"“](.+?)[\\\"”].*$", Pattern.CASE_INSENSITIVE);
        private static final Pattern SAID_NAME_BEFORE_QUOTE_PATTERN = Pattern.compile("^\\s*(?:" + DIALOGUE_VERBS + ")\\s+([A-Z][A-Za-z0-9 .\\'\\-]{1,48})\\b[^\\\"“]*[\\\"“](.+?)[\\\"”].*$", Pattern.CASE_INSENSITIVE);
        private static final Pattern INLINE_TRAILING_ATTRIBUTION_PATTERN = Pattern.compile("^\\s*(.*?)\\s*[\\\"“](.+?)[\\\"”][,!?\\.]*\\s+([A-Z][A-Za-z0-9 .\\'\\-]{1,48})\\s+(?:" + DIALOGUE_VERBS + ")\\b(.*)$", Pattern.CASE_INSENSITIVE);
        private static final Pattern INLINE_SAID_BEFORE_QUOTE_PATTERN = Pattern.compile("^\\s*(.*?)\\b([A-Z][A-Za-z0-9 .\\'\\-]{1,48})\\s+(?:" + DIALOGUE_VERBS + ")\\b[^\\\"“]*[\\\"“](.+?)[\\\"”](.*)$", Pattern.CASE_INSENSITIVE);
        final String speechText;
        final List<String> chunks;
        final List<String> sectionLabels;
        final List<String> sectionHashes;
        final int semanticCueCount;

        MarkdownNarrationDocument(String speechText, List<String> chunks, List<String> sectionLabels, List<String> sectionHashes, int semanticCueCount) {
            this.speechText = speechText == null ? "" : speechText;
            this.chunks = chunks == null || chunks.isEmpty() ? Collections.singletonList(this.speechText) : chunks;
            this.sectionLabels = sectionLabels == null ? new ArrayList<>() : sectionLabels;
            this.sectionHashes = sectionHashes == null ? new ArrayList<>() : sectionHashes;
            this.semanticCueCount = Math.max(0, semanticCueCount);
        }

        static MarkdownNarrationDocument compile(String markdown, int firstChunkChars, int targetChars, int minChars) {
            String raw = markdown == null ? "" : markdown.replace("\r\n", "\n").replace('\r', '\n');
            List<String> speechBlocks = new ArrayList<>();
            int cues = 0;
            boolean inCode = false;
            String[] lines = raw.split("\n", -1);
            StringBuilder paragraph = new StringBuilder();
            for (String originalLine : lines) {
                String line = originalLine == null ? "" : originalLine;
                String trimmed = line.trim();
                if (trimmed.startsWith("```") || trimmed.startsWith("~~~")) {
                    flushParagraph(paragraph, speechBlocks);
                    inCode = !inCode;
                    if (inCode) {
                        speechBlocks.add("Code block.");
                        cues += 1;
                    }
                    continue;
                }
                if (trimmed.isEmpty()) {
                    flushParagraph(paragraph, speechBlocks);
                    continue;
                }
                if (inCode) {
                    String code = cleanInlineMarkdownForSpeech(trimmed);
                    if (!code.isEmpty()) speechBlocks.add("Code: " + code + ".");
                    continue;
                }
                Matcher heading = Pattern.compile("^\\s{0,3}(#{1,6})\\s+(.+?)\\s*#*\\s*$").matcher(line);
                if (heading.matches()) {
                    flushParagraph(paragraph, speechBlocks);
                    int level = heading.group(1).length();
                    String title = cleanInlineMarkdownForSpeech(heading.group(2));
                    if (!title.isEmpty()) {
                        speechBlocks.add((level <= 1 ? "Title: " : level == 2 ? "Section: " : "Subsection: ") + title + ".");
                        cues += 1;
                    }
                    continue;
                }
                if (trimmed.matches("^([-*_])\\s*(\\1\\s*){2,}$")) {
                    flushParagraph(paragraph, speechBlocks);
                    speechBlocks.add("Break.");
                    cues += 1;
                    continue;
                }
                Matcher bullet = Pattern.compile("^\\s*(?:[-*+]\\s+|\\d+[.)]\\s+)(.+)$").matcher(line);
                if (bullet.matches()) {
                    flushParagraph(paragraph, speechBlocks);
                    String item = cleanInlineMarkdownForSpeech(bullet.group(1));
                    if (!item.isEmpty()) {
                        speechBlocks.add("List item: " + item + ".");
                        cues += 1;
                    }
                    continue;
                }
                Matcher quote = Pattern.compile("^\\s*>+\\s*(.+)$").matcher(line);
                if (quote.matches()) {
                    flushParagraph(paragraph, speechBlocks);
                    String quoted = cleanInlineMarkdownForSpeech(quote.group(1));
                    if (!quoted.isEmpty()) {
                        speechBlocks.add("Quoted note: " + quoted + ".");
                        cues += 1;
                    }
                    continue;
                }
                Matcher explicitSpeaker = Pattern.compile("^\\s*\\[(?:speaker|voice):([^\\]]+)\\]\\s*(.*)$", Pattern.CASE_INSENSITIVE).matcher(line);
                if (explicitSpeaker.matches()) {
                    flushParagraph(paragraph, speechBlocks);
                    String speakerName = cleanSpeakerNameForTag(explicitSpeaker.group(1));
                    String utterance = cleanInlineMarkdownForSpeech(explicitSpeaker.group(2));
                    if (!speakerName.isEmpty() && !utterance.isEmpty()) {
                        speechBlocks.add("[speaker:" + speakerName + "] " + utterance);
                        cues += 1;
                    }
                    continue;
                }
                Matcher dashSpeaker = SPEAKER_DASH_PATTERN.matcher(line);
                if (dashSpeaker.matches()) {
                    flushParagraph(paragraph, speechBlocks);
                    String speakerName = cleanSpeakerNameForTag(dashSpeaker.group(1));
                    String utterance = cleanInlineMarkdownForSpeech(dashSpeaker.group(2));
                    if (!speakerName.isEmpty() && !utterance.isEmpty()) {
                        speechBlocks.add("[speaker:" + speakerName + "] " + utterance);
                        cues += 1;
                    }
                    continue;
                }
                Matcher speaker = SPEAKER_CUE_PATTERN.matcher(line);
                if (speaker.matches()) {
                    flushParagraph(paragraph, speechBlocks);
                    String speakerName = cleanSpeakerNameForTag(speaker.group(1));
                    String utterance = cleanInlineMarkdownForSpeech(speaker.group(2));
                    if (!speakerName.isEmpty() && !utterance.isEmpty()) {
                        speechBlocks.add("[speaker:" + speakerName + "] " + utterance);
                        cues += 1;
                    }
                    continue;
                }
                if (tryAppendAttributedDialogue(line, paragraph, speechBlocks)) {
                    cues += 1;
                    continue;
                }
                String clean = cleanInlineMarkdownForSpeech(trimmed);
                if (!clean.isEmpty()) {
                    if (paragraph.length() > 0) paragraph.append(' ');
                    paragraph.append(clean);
                }
            }
            flushParagraph(paragraph, speechBlocks);
            String speech = joinBlocks(speechBlocks);
            List<String> chunks = chunkSpeechBlocks(speechBlocks, firstChunkChars, targetChars, minChars);
            List<String> labels = new ArrayList<>();
            List<String> hashes = new ArrayList<>();
            for (int i = 0; i < chunks.size(); i++) {
                labels.add("section " + (i + 1));
                hashes.add(stableTextHash(chunks.get(i)));
            }
            return new MarkdownNarrationDocument(speech, chunks, labels, hashes, cues);
        }

        private static void flushParagraph(StringBuilder paragraph, List<String> speechBlocks) {
            if (paragraph.length() <= 0) return;
            String clean = paragraph.toString().replaceAll("\\s+", " ").trim();
            if (!clean.isEmpty()) speechBlocks.add(clean);
            paragraph.setLength(0);
        }
        private static boolean tryAppendAttributedDialogue(String line, StringBuilder paragraph, List<String> speechBlocks) {
            List<VoiceScriptPlanner.Segment> segments = VoiceScriptPlanner.splitQuotedLine(line);
            if (segments.isEmpty()) return false;
            for (VoiceScriptPlanner.Segment segment : segments) {
                if (segment.dialogue) {
                    appendDialogueTurn(segment.speakerId, segment.text, paragraph, speechBlocks);
                } else {
                    String narration = cleanInlineMarkdownForSpeech(segment.text);
                    if (!narration.isEmpty()) {
                        if (paragraph.length() > 0) paragraph.append(' ');
                        paragraph.append(narration);
                    }
                }
            }
            return true;
        }

        private static boolean appendInlineDialogueTurn(String prefix, String speaker, String utterance, String suffix, StringBuilder paragraph, List<String> speechBlocks) {
            String before = cleanInlineMarkdownForSpeech(prefix);
            if (!before.isEmpty()) {
                if (paragraph.length() > 0) paragraph.append(' ');
                paragraph.append(before);
            }
            if (!appendDialogueTurn(speaker, utterance, paragraph, speechBlocks)) return false;
            String after = cleanInlineMarkdownForSpeech(suffix);
            if (!after.isEmpty()) {
                if (paragraph.length() > 0) paragraph.append(' ');
                paragraph.append(after);
            }
            return true;
        }

        private static boolean appendDialogueTurn(String speaker, String utterance, StringBuilder paragraph, List<String> speechBlocks) {
            String speakerName = cleanSpeakerNameForTag(speaker);
            String spoken = cleanInlineMarkdownForSpeech(utterance);
            if (speakerName.isEmpty() || spoken.isEmpty()) return false;
            flushParagraph(paragraph, speechBlocks);
            speechBlocks.add("[speaker:" + speakerName + "] " + spoken);
            return true;
        }

        private static String cleanSpeakerNameForTag(String value) {
            String clean = cleanInlineMarkdownForSpeech(value);
            clean = clean.replaceAll("(?i)^(said|asked|replied|answered|called|whispered|shouted|muttered|continued)\\s+", "");
            clean = clean.replaceAll("(?i)\\b(said|asked|replied|answered|called|whispered|shouted|muttered|continued)$", "");
            clean = clean.replaceAll("\\s+", " ").trim();
            String id = CharacterVoiceRule.normalizeId(clean);
            if (id.equals("voice") || id.equals("speaker") || id.equals("narrator") || id.equals("section") || id.equals("title") || id.equals("note")) return "";
            return clean.length() < 2 || clean.length() > 48 ? "" : clean;
        }


        private static String joinBlocks(List<String> blocks) {
            StringBuilder out = new StringBuilder();
            for (String block : blocks) {
                String clean = block == null ? "" : block.replaceAll("\\s+", " ").trim();
                if (clean.isEmpty()) continue;
                if (out.length() > 0) out.append("\n\n");
                out.append(clean);
            }
            return out.toString().trim();
        }

        private static List<String> chunkSpeechBlocks(List<String> blocks, int firstChunkChars, int targetChars, int minChars) {
            List<String> chunks = new ArrayList<>();
            StringBuilder current = new StringBuilder();
            if (blocks != null) {
                for (String block : blocks) {
                    String clean = block == null ? "" : block.replaceAll("\\s+", " ").trim();
                    if (clean.isEmpty()) continue;
                    boolean speakerTurn = clean.toLowerCase(Locale.US).startsWith("[speaker:");
                    if (speakerTurn) {
                        flushChunk(current, chunks);
                        chunks.addAll(splitLongChunk(clean, chunks.isEmpty() ? firstChunkChars : targetChars, minChars));
                        continue;
                    }
                    int target = chunks.isEmpty() && current.length() == 0 ? firstChunkChars : targetChars;
                    if (current.length() > 0 && current.length() + 1 + clean.length() > target) {
                        flushChunk(current, chunks);
                    }
                    if (clean.length() > targetChars) {
                        flushChunk(current, chunks);
                        chunks.addAll(splitLongChunk(clean, chunks.isEmpty() ? firstChunkChars : targetChars, minChars));
                    } else {
                        if (current.length() > 0) current.append(' ');
                        current.append(clean);
                    }
                }
            }
            flushChunk(current, chunks);
            return chunks.isEmpty() ? Collections.singletonList("") : chunks;
        }

        private static void flushChunk(StringBuilder current, List<String> chunks) {
            String clean = current == null ? "" : current.toString().replaceAll("\\s+", " ").trim();
            if (!clean.isEmpty()) chunks.add(clean);
            if (current != null) current.setLength(0);
        }

        private static List<String> splitLongChunk(String speech, int targetChars, int minChars) {
            List<String> chunks = new ArrayList<>();
            String clean = speech == null ? "" : speech.replaceAll("\\s+", " ").trim();
            int index = 0;
            while (index < clean.length()) {
                int target = chunks.isEmpty() ? Math.max(180, targetChars) : targetChars;
                int minimum = chunks.isEmpty() ? Math.min(180, target) : minChars;
                int end = Math.min(clean.length(), index + target);
                if (end < clean.length()) {
                    int sentence = Math.max(clean.lastIndexOf(". ", end), Math.max(clean.lastIndexOf("! ", end), clean.lastIndexOf("? ", end)));
                    if (sentence > index + minimum) end = sentence + 1;
                }
                String chunk = clean.substring(index, end).trim();
                if (!chunk.isEmpty()) chunks.add(chunk);
                index = end;
                while (index < clean.length() && Character.isWhitespace(clean.charAt(index))) index++;
            }
            return chunks;
        }

        private static String cleanInlineMarkdownForSpeech(String text) {
            String clean = text == null ? "" : text;
            clean = clean.replaceAll("!\\[([^\\]]*)\\]\\([^)]*\\)", "$1");
            clean = clean.replaceAll("\\[([^\\]]+)\\]\\([^)]*\\)", "$1");
            clean = clean.replaceAll("`([^`]+)`", "$1");
            clean = clean.replaceAll("\\*\\*([^*]+)\\*\\*", "$1");
            clean = clean.replaceAll("__([^_]+)__", "$1");
            clean = clean.replaceAll("\\*([^*]+)\\*", "$1");
            clean = clean.replaceAll("_([^_]+)_", "$1");
            clean = clean.replaceAll("^\\s{0,3}#{1,6}\\s*", "");
            clean = clean.replaceAll("\\s+#+\\s*$", "");
            clean = clean.replaceAll("\\s+", " ").trim();
            return clean;
        }
    }

    private static String stableTextHash(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (int i = 0; i < Math.min(8, bytes.length); i++) {
                out.append(String.format(Locale.US, "%02x", bytes[i] & 0xff));
            }
            return out.toString();
        } catch (Exception ex) {
            return Integer.toHexString((value == null ? "" : value).hashCode());
        }
    }

    private static List<String> jsonStringArray(JSONArray array) {
        List<String> values = new ArrayList<>();
        if (array == null) return values;
        for (int i = 0; i < array.length(); i++) {
            String value = array.optString(i, "").trim();
            if (!value.isEmpty()) values.add(value);
        }
        return values;
    }

    private static String readerTitleSpeech(String name) {
        String clean = name == null ? "" : name.trim();
        return "Title. " + (clean.isEmpty() ? "Google Doc" : clean) + ".";
    }

    private static final class SectionVoiceAssignment {
        final CharacterVoiceRule rule;
        final String voiceName;
        final String voiceId;
        final String role;
        final boolean explicitCast;

        SectionVoiceAssignment(CharacterVoiceRule rule, String voiceName, String voiceId, String role, boolean explicitCast) {
            this.rule = rule;
            this.voiceName = voiceName == null ? "" : voiceName.trim();
            this.voiceId = voiceId == null ? "" : voiceId.trim();
            this.role = CharacterVoiceRule.firstNonEmptyStatic(role, "narrator").toLowerCase(Locale.US);
            this.explicitCast = explicitCast;
        }

        JSONObject toJson() throws Exception {
            return new JSONObject()
                    .put("speakerId", rule == null ? "" : rule.characterId)
                    .put("speaker", rule == null ? "" : rule.characterName)
                    .put("role", role)
                    .put("voiceName", voiceName)
                    .put("voiceId", voiceId)
                    .put("explicitCast", explicitCast)
                    .put("acousticDirection", rule == null ? "" : rule.acousticDirection);
        }
    }

    private static final class DocumentReaderState {
        final String fileId;
        final String name;
        final String modifiedTime;
        final String webViewLink;
        final int charCount;
        final String textHash;
        final List<String> chunks;
        int currentIndex;
        boolean paused;
        String status;
        String utteranceId = "";
        GoogleDocAudioLibrary.Entry audioEntry;
        boolean playbackRequested;
        boolean downloadRequested;
        boolean renderRequested;
        boolean previewOnlyPlayback;
        boolean cancelRequested;
        boolean playbackRestoredFromManifest;
        boolean playbackRetryScheduled;
        boolean playbackReconcileScheduled;
        long nextPlaybackReconcileAtMs;
        boolean titleIntroPlayed;
        int downloadedSections;
        String playbackTargetKind = "section";
        int playbackTargetIndex = 0;
        long playbackOffsetBytes = 0L;
        long activePlaybackStartOffsetBytes = 0L;
        long activePlaybackWrittenBytes = 0L;
        long activePlaybackPcmBytes = 0L;
        int activePlaybackSampleRate = GoogleDocAudioLibrary.DEFAULT_SAMPLE_RATE;
        String voiceProvider = DEFAULT_DRIVE_SPEECH_PROVIDER;
        String speechModelId = DEFAULT_DRIVE_SPEECH_MODEL;
        String narratorVoiceName = DEFAULT_DRIVE_NARRATOR_VOICE;
        String dialogueVoiceName = DEFAULT_DRIVE_NARRATOR_VOICE;
        String notesVoiceName = DEFAULT_DRIVE_NARRATOR_VOICE;
        String speechProfileKey = "default-cartesia";
        boolean voiceSplitRenderingMode = false;
        String activeCharacterId = "";
        String activeVoiceAlias = "";
        String activeAcousticDirection = "";
        String exportedWavPath = "";
        String narrationCompiler = "drive-markdown-narrator-v1";
        int semanticCueCount = 0;
        List<String> sectionLabels = new ArrayList<>();
        List<String> sectionHashes = new ArrayList<>();
        List<SectionVoiceAssignment> voiceSplitAssignments = new ArrayList<>();

        DocumentReaderState(JSONObject file, String content, MarkdownNarrationDocument narrationDocument) {
            this.fileId = file == null ? "" : file.optString("id", "").trim();
            this.name = file == null ? "Google Doc" : firstNonEmptyStatic(file.optString("name", ""), "Google Doc");
            this.modifiedTime = file == null ? "" : file.optString("modifiedTime", "").trim();
            this.webViewLink = file == null ? "" : file.optString("webViewLink", "").trim();
            String clean = content == null ? "" : content.trim();
            this.charCount = clean.length();
            this.textHash = stableTextHash(clean);
            MarkdownNarrationDocument compiled = narrationDocument == null ? MarkdownNarrationDocument.compile(clean, DOC_READER_FIRST_CHUNK_CHARS, DOC_READER_TARGET_CHARS, DOC_READER_MIN_CHARS) : narrationDocument;
            this.chunks = compiled.chunks == null || compiled.chunks.isEmpty() ? Collections.singletonList(compiled.speechText) : compiled.chunks;
            this.semanticCueCount = compiled.semanticCueCount;
            this.sectionLabels = compiled.sectionLabels == null ? new ArrayList<>() : compiled.sectionLabels;
            this.sectionHashes = compiled.sectionHashes == null ? new ArrayList<>() : compiled.sectionHashes;
            this.currentIndex = 0;
            this.paused = false;
            this.status = "ready";
            this.playbackRequested = false;
            this.downloadRequested = false;
            this.renderRequested = false;
            this.previewOnlyPlayback = false;
            this.cancelRequested = false;
            this.playbackRestoredFromManifest = false;
            this.playbackRetryScheduled = false;
            this.playbackReconcileScheduled = false;
            this.nextPlaybackReconcileAtMs = 0L;
            this.titleIntroPlayed = false;
            this.downloadedSections = 0;
            this.playbackTargetKind = "section";
            this.playbackTargetIndex = 0;
            this.playbackOffsetBytes = 0L;
        }

        void applySpeechProfile(String provider, String modelId, String narratorVoice, String dialogueVoice, String notesVoice, String profileKey) {
            applySpeechProfile(provider, modelId, narratorVoice, dialogueVoice, notesVoice, profileKey, false);
        }

        void applySpeechProfile(String provider, String modelId, String narratorVoice, String dialogueVoice, String notesVoice, String profileKey, boolean voiceSplitRendering) {
            this.voiceProvider = normalizeDriveSpeechProviderStatic(provider);
            this.speechModelId = firstNonEmptyStatic(modelId, DEFAULT_DRIVE_SPEECH_MODEL);
            this.narratorVoiceName = firstNonEmptyStatic(narratorVoice, DEFAULT_DRIVE_NARRATOR_VOICE);
            this.dialogueVoiceName = firstNonEmptyStatic(dialogueVoice, this.narratorVoiceName);
            this.notesVoiceName = firstNonEmptyStatic(notesVoice, this.narratorVoiceName);
            this.speechProfileKey = firstNonEmptyStatic(profileKey, "default-cartesia");
            this.voiceSplitRenderingMode = voiceSplitRendering;
        }

        String voiceProviderLabel() {
            return "elevenlabs".equals(voiceProvider) ? "ElevenLabs render-only" : "Cartesia";
        }

        String voiceSummary() {
            String base = "Narrator " + narratorVoiceName + ", Dialogue " + dialogueVoiceName + ", Notes " + notesVoiceName;
            return voiceSplitRenderingMode ? "Registry voices; fallback roles " + base : base;
        }

        private DocumentReaderState(String fileId, String name, String modifiedTime, String webViewLink, int charCount, String textHash, int chunkCount, int currentIndex, String status, JSONArray previews) {
            this.fileId = fileId == null ? "" : fileId;
            this.name = firstNonEmptyStatic(name, "Google Doc");
            this.modifiedTime = modifiedTime == null ? "" : modifiedTime;
            this.webViewLink = webViewLink == null ? "" : webViewLink;
            this.charCount = charCount;
            this.textHash = textHash == null ? "" : textHash;
            this.chunks = new ArrayList<>();
            for (int i = 0; i < Math.max(1, chunkCount); i++) {
                JSONObject preview = previews == null ? null : previews.optJSONObject(i);
                this.chunks.add(preview == null ? "Reopen this document to reload the full Drive text." : preview.optString("preview", "Reopen this document to reload the full Drive text."));
            }
            this.currentIndex = Math.max(0, Math.min(this.chunks.size() - 1, currentIndex));
            this.paused = true;
            this.status = firstNonEmptyStatic(status, "restored");
            this.playbackRequested = false;
            this.downloadRequested = false;
            this.renderRequested = false;
            this.previewOnlyPlayback = false;
            this.cancelRequested = false;
            this.playbackRestoredFromManifest = false;
            this.playbackRetryScheduled = false;
            this.playbackReconcileScheduled = false;
            this.nextPlaybackReconcileAtMs = 0L;
            this.titleIntroPlayed = false;
            this.downloadedSections = 0;
            this.playbackTargetKind = "section";
            this.playbackTargetIndex = 0;
            this.playbackOffsetBytes = 0L;
        }

        int chunkCount() {
            return chunks.size();
        }

        SectionVoiceAssignment voiceSplitAssignmentAt(int index) {
            return index >= 0 && index < voiceSplitAssignments.size() ? voiceSplitAssignments.get(index) : null;
        }

        String voiceSplitSpeakerSummary() {
            List<String> names = new ArrayList<>();
            for (SectionVoiceAssignment assignment : voiceSplitAssignments) {
                if (assignment == null || assignment.rule == null) continue;
                String value = assignment.rule.characterId + ":" + assignment.voiceName;
                boolean seen = false;
                for (String existing : names) if (existing.equals(value)) seen = true;
                if (!seen) names.add(value);
            }
            return TextUtils.join(",", names);
        }

        String sourceLine() {
            StringBuilder builder = new StringBuilder(name);
            if (!modifiedTime.isEmpty()) {
                builder.append(" | modified ").append(modifiedTime);
            }
            if (!fileId.isEmpty()) {
                builder.append(" | file ").append(fileId);
            }
            return builder.toString();
        }

        String previewText() {
            if (chunks.isEmpty()) {
                return "";
            }
            String text = chunks.get(Math.max(0, Math.min(chunks.size() - 1, currentIndex)));
            if (text.length() > DOC_READER_PREVIEW_CHARS) {
                return text.substring(0, DOC_READER_PREVIEW_CHARS) + "...";
            }
            return text;
        }

        String summaryText() {
            return "Google Doc reader: " + name
                    + "\nText version: Drive snapshot " + textHash + " (" + charCount + " chars)."
                    + "\nVoice version: " + voiceProviderLabel() + " role voices (" + voiceSummary() + "); full artifact saved by Render.";
        }

        DocumentReaderState withClearedAudioEntry() {
            audioEntry = null;
            downloadedSections = 0;
            renderRequested = false;
            downloadRequested = false;
            playbackRequested = false;
            paused = true;
            status = "speech profile changed";
            return this;
        }

        JSONObject toMetadata() {
            JSONObject json = new JSONObject();
            try {
                json.put("type", "doc_reader_pair");
                json.put("fileId", fileId);
                json.put("name", name);
                json.put("modifiedTime", modifiedTime);
                json.put("webViewLink", webViewLink);
                json.put("charCount", charCount);
                json.put("textHash", textHash);
                json.put("chunkCount", chunkCount());
                json.put("currentIndex", currentIndex);
                json.put("narrationCompiler", narrationCompiler);
                json.put("semanticCueCount", semanticCueCount);
                json.put("sectionLabels", new JSONArray(sectionLabels));
                json.put("sectionHashes", new JSONArray(sectionHashes));
                json.put("voiceProvider", voiceProvider);
                json.put("voiceName", narratorVoiceName);
                json.put("speechModelId", speechModelId);
                json.put("speechProfileKey", speechProfileKey);
                json.put("voiceSplitRenderingMode", voiceSplitRenderingMode);
                json.put("activeCharacterId", activeCharacterId);
                json.put("activeVoiceAlias", activeVoiceAlias);
                json.put("activeAcousticDirection", activeAcousticDirection);
                JSONArray splitPlan = new JSONArray();
                for (SectionVoiceAssignment assignment : voiceSplitAssignments) splitPlan.put(assignment.toJson());
                json.put("voiceSplitAssignments", splitPlan);
                json.put("exportedWavPath", exportedWavPath);
                json.put("voiceRoles", new JSONObject()
                        .put("narrator", narratorVoiceName)
                        .put("dialogue", dialogueVoiceName)
                        .put("notes", notesVoiceName));
                json.put("status", status);
                JSONArray previews = new JSONArray();
                int limit = Math.min(chunks.size(), 40);
                for (int i = 0; i < limit; i++) {
                    String chunk = chunks.get(i);
                    previews.put(new JSONObject()
                            .put("index", i)
                            .put("startLabel", "part " + (i + 1))
                            .put("preview", chunk.length() > 180 ? chunk.substring(0, 180) + "..." : chunk));
                }
                json.put("chunkPreviews", previews);
            } catch (Exception ignored) {
            }
            return json;
        }

        static DocumentReaderState fromMetadata(JSONObject json) {
            if (json == null) {
                return null;
            }
            DocumentReaderState state = new DocumentReaderState(
                    json.optString("fileId", ""),
                    json.optString("name", "Google Doc"),
                    json.optString("modifiedTime", ""),
                    json.optString("webViewLink", ""),
                    json.optInt("charCount", 0),
                    json.optString("textHash", ""),
                    json.optInt("chunkCount", 1),
                    json.optInt("currentIndex", 0),
                    json.optString("status", "restored"),
                    json.optJSONArray("chunkPreviews"));
            JSONObject roles = json.optJSONObject("voiceRoles");
            state.applySpeechProfile(
                    json.optString("voiceProvider", DEFAULT_DRIVE_SPEECH_PROVIDER),
                    json.optString("speechModelId", DEFAULT_DRIVE_SPEECH_MODEL),
                    roles == null ? json.optString("voiceName", DEFAULT_DRIVE_NARRATOR_VOICE) : roles.optString("narrator", DEFAULT_DRIVE_NARRATOR_VOICE),
                    roles == null ? json.optString("voiceName", DEFAULT_DRIVE_NARRATOR_VOICE) : roles.optString("dialogue", DEFAULT_DRIVE_NARRATOR_VOICE),
                    roles == null ? json.optString("voiceName", DEFAULT_DRIVE_NARRATOR_VOICE) : roles.optString("notes", DEFAULT_DRIVE_NARRATOR_VOICE),
                    json.optString("speechProfileKey", "default-cartesia"),
                    json.optBoolean("voiceSplitRenderingMode", false));
            state.narrationCompiler = json.optString("narrationCompiler", MarkdownNarrationDocument.COMPILER_ID);
            state.semanticCueCount = json.optInt("semanticCueCount", 0);
            state.sectionLabels = jsonStringArray(json.optJSONArray("sectionLabels"));
            state.sectionHashes = jsonStringArray(json.optJSONArray("sectionHashes"));
            state.exportedWavPath = json.optString("exportedWavPath", "");
            return state;
        }

        static String firstNonEmptyStatic(String value, String fallback) {
            return value == null || value.trim().isEmpty() ? fallback : value.trim();
        }
    }

    private static String normalizeDriveSpeechProviderStatic(String provider) {
        String clean = provider == null ? "" : provider.trim().toLowerCase(Locale.US);
        return "elevenlabs".equals(clean) ? "elevenlabs" : DEFAULT_DRIVE_SPEECH_PROVIDER;
    }

    private static final class ChatTurn {
        final String role;
        final String text;
        final JSONObject metadata;

        ChatTurn(String role, String text) {
            this(role, text, null);
        }

        ChatTurn(String role, String text, JSONObject metadata) {
            this.role = role;
            this.text = text;
            this.metadata = metadata;
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
        if (requestCode == REQUEST_FILE_ATTACH) {
            if (resultCode == RESULT_OK) {
                importAttachedFiles(data);
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
            scheduleDriveRefreshAfterHandoff("google_tool_permissions_complete");
            if (hasPendingTermuxPairing()) {
                appendStatus("Google tools approved. Approving Termux Codex through Shizuku.");
                continuePendingTermuxPairing("google_tool_permissions_complete");
                return;
            }
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
                scheduleDriveRefreshAfterHandoff("drive_auth_complete");
            } else {
                showAssistantMessage("Google Drive permission was not approved. Tap Refresh to retry.");
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
        stopDriveBrowserPolling();
        stopHostedSpeechPlayback("activity_destroy");
        stopService(new Intent(this, NarrationForegroundService.class));
        driveNarrationForegroundRunning = false;
        updateSpeechMediaSession(false);
        abandonSpeechFocus();
        if (deviceTextToSpeech != null) {
            deviceTextToSpeech.stop();
            deviceTextToSpeech.shutdown();
            deviceTextToSpeech = null;
            deviceTextToSpeechReady = false;
        }
        if (speechMediaSession != null) {
            speechMediaSession.release();
            speechMediaSession = null;
        }
        if (firebaseAuth != null && authStateListener != null) {
            firebaseAuth.removeAuthStateListener(authStateListener);
        }
        executor.shutdownNow();
        documentAudioExecutor.shutdownNow();
        documentRenderExecutor.shutdownNow();
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
