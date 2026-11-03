package com.homecenter.ritsucontrol;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;

/**
 * Voice-first foreground session: Android's default recognition provider
 * owns the microphone directly. No external prerecorded PCM injection.
 *
 * Google/Android recognition ends individual utterances. The service requests
 * a subsequent bounded session only after the previous onResults/onError
 * callback, with pacing and a finite failure circuit breaker.
 *
 * Phone speaker audio cannot reliably be identified as human voice. Reject
 * results when Android reports media active; do NOT use them as user commands.
 * The authenticated ChatGPT / TTS bridge is not wired in this APK.
 */
public final class RitsuControlService extends Service {
    static final String ACTION_START = "com.homecenter.ritsucontrol.START";
    static final String ACTION_LISTEN = "com.homecenter.ritsucontrol.LISTEN";
    static final String ACTION_TRANSCRIBE = "com.homecenter.ritsucontrol.TRANSCRIBE";
    static final String ACTION_SPEAK_ONCE = "com.homecenter.ritsucontrol.SPEAK_ONCE";
    static final String ACTION_MUTE = "com.homecenter.ritsucontrol.MUTE";
    static final String ACTION_RESUME = "com.homecenter.ritsucontrol.RESUME";
    static final String ACTION_SHOW_BUBBLE = "com.homecenter.ritsucontrol.SHOW_BUBBLE";
    static final String ACTION_HIDE_BUBBLE = "com.homecenter.ritsucontrol.HIDE_BUBBLE";
    static final String ACTION_SPEAKER_PREFERENCE = "com.homecenter.ritsucontrol.SPEAKER_PREFERENCE";
    static final String ACTION_MEDIA_TALK = "com.homecenter.ritsucontrol.MEDIA_TALK";
    static final String ACTION_STOP = "com.homecenter.ritsucontrol.STOP";
    static final String ACTION_SYNC_NOW = "com.homecenter.ritsucontrol.SYNC_NOW";
    static final String ACTION_PAUSE_WINDOW = "com.homecenter.ritsucontrol.PAUSE_WINDOW";
    static final String EXTRA_PAUSE_MS = "pauseMillis";
    private static final String CHANNEL = "ritsu_control_notification_v2";
    private static final int NOTIFICATION_ID = 19644;
    private static final int MAX_CONSECUTIVE_ERRORS = 4;

    static volatile ListeningPolicy.Mode liveMode = ListeningPolicy.Mode.OFF;
    static volatile boolean voiceActivity = false;
    static volatile String lastProblem = "";
    static volatile String lastTranscript = "";
    static volatile long transcriptRevision = 0;
    static volatile String partialTranscript = "";
    static volatile long partialRevision = 0;
    static volatile String recognitionStatus = "Not started";
    static volatile String mediaGuardStatus = "Playback source not verified";
    static volatile long feedRevision = 0;
    static volatile String pendingSpeechText = "";
    static volatile int speechPauseMs = SpokenTurnBuffer.DEFAULT_PAUSE_MS;

    private ListeningPolicy.Mode mode = ListeningPolicy.Mode.OFF;
    private Handler mainHandler;
    private SystemSpeechSession speechSession;
    private Runnable recognitionTimeout;
    private Runnable nextRecognition;
    private Runnable mediaFocusDeadline;
    private ControlReceipts receipts;
    private ConversationLedger ledger;
    private RitsuLocalSync homeCenterSync;
    private MediaPauseLease mediaPause;
    private RitsuBubble bubble;
    private int consecutiveErrors;
    private int sessionGeneration;
    private SpokenTurnBuffer pendingTurn;
    private Runnable pendingCommit;
    private boolean mediaObservedInSession;
    private final Runnable playbackProbe = new Runnable() {
        @Override public void run() {
            if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
            if (mediaPause.otherAudioMayBeActive()) mediaObservedInSession = true;
            mainHandler.postDelayed(this, 350);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        mainHandler = new Handler(Looper.getMainLooper());
        receipts = new ControlReceipts(this);
        ledger = new ConversationLedger(this);
        homeCenterSync = new RitsuLocalSync(this, ledger, () -> {
            feedRevision++;
            updateNotification();
        });
        mediaPause = new MediaPauseLease(this);
        // Upgrade existing v0.8 sessions once to the owner's requested
        // Thoughtful default, without clobbering any later explicit choice.
        android.content.SharedPreferences timing =
                getSharedPreferences("ritsu_voice_timing_v1", MODE_PRIVATE);
        if (!timing.getBoolean("thoughtful_migration_20261023", false)) {
            timing.edit().putInt("pauseMs", 5000)
                    .putBoolean("thoughtful_migration_20261023", true).apply();
        }
        int storedPause = timing.getInt("pauseMs", SpokenTurnBuffer.DEFAULT_PAUSE_MS);
        if (storedPause < SpokenTurnBuffer.MIN_PAUSE_MS ||
                storedPause > SpokenTurnBuffer.MAX_PAUSE_MS)
            storedPause = SpokenTurnBuffer.DEFAULT_PAUSE_MS;
        pendingTurn = new SpokenTurnBuffer(storedPause);
        speechPauseMs = storedPause;
        pendingSpeechText = "";
        ControlStore.transition(this, ControlPolicy.ACTION_START);
        liveMode = ListeningPolicy.Mode.OFF;
        voiceActivity = false;
        lastProblem = "";
        lastTranscript = "";
        partialTranscript = "";
        recognitionStatus = "Microphone off";
        mediaGuardStatus = "Results blocked while Android media is active";
        getSystemService(NotificationManager.class).createNotificationChannel(
                new NotificationChannel(CHANNEL, "Ritsu listening controls",
                        NotificationManager.IMPORTANCE_LOW));

        speechSession = new SystemSpeechSession(this, new SystemSpeechSession.Observer() {
            @Override public void status(String text) {
                recognitionStatus = text;
                updateNotification();
            }
            @Override public void speechStarted() {
                if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
                pendingTurn.speechStarted();
                cancelPendingCommit();
                updateSpeechPreview();
            }
            @Override public void speechEnded() {
                if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
                pendingTurn.speechEnded(SystemClock.elapsedRealtime());
                // Wait for provider final result before considering a send.
                updateSpeechPreview();
            }
            @Override public void partialTranscript(String text) {
                // Preview only. Never treat partial speech as an executable turn.
                if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
                if (mediaPause.otherAudioMayBeActive()) mediaObservedInSession = true;
                if (mediaObservedInSession) {
                    partialTranscript = "";
                    mediaGuardStatus = "Phone audio playing: provisional text suppressed";
                    return;
                }
                partialTranscript = text;
                partialRevision++;
                recognitionStatus = "Recognizing words";
            }
            @Override public void finalTranscript(String text) {
                if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
                if (mediaPause.otherAudioMayBeActive()) mediaObservedInSession = true;
                if (mediaObservedInSession) {
                    recognitionStatus = "Phone playback heard during utterance; text rejected";
                    mediaGuardStatus = "Source not verified. No user turn accepted.";
                    receipts.append("PHONE_PLAYBACK_REJECTED", mode, mode,
                            "cannot_identify_human_when_media_active");
                    partialTranscript = "";
                    partialRevision++;
                    // A rejected acoustic fragment must not strand a valid
                    // older draft whose countdown was canceled on speech start.
                    if (pendingTurn.hasText()) {
                        pendingTurn.speechEnded(SystemClock.elapsedRealtime());
                        schedulePendingCommit();
                        updateSpeechPreview();
                    }
                } else {
                    // Google's onResults finalizes a recognizer fragment,
                    // NOT necessarily the human's complete spoken message.
                    if (pendingTurn.wouldOverflow(text)) flushPendingTurn("size_limit");
                    pendingTurn.appendFinal(text, SystemClock.elapsedRealtime());
                    lastTranscript = text;
                    transcriptRevision++;
                    partialTranscript = "";
                    partialRevision++;
                    updateSpeechPreview();
                    schedulePendingCommit();
                    recognitionStatus = "Holding phrase for thinking pause, not sent yet";
                    mediaGuardStatus = "No active media reported (NOT proof of human origin)";
                    receipts.append("SPEECH_FRAGMENT", mode, mode,
                            "provider_final_buffered_waiting_for_user_pause");
                }
                consecutiveErrors = 0;
                mainHandler.post(() -> completeProviderSession(true));
            }
            @Override public void failed(String reason) {
                if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
                lastProblem = reason;
                recognitionStatus = reason;
                if (pendingTurn.hasText()) {
                    // No-match and timeout can follow a detected continuation.
                    // Keep earlier recognized words and restart their delay.
                    pendingTurn.speechEnded(SystemClock.elapsedRealtime());
                    schedulePendingCommit();
                    updateSpeechPreview();
                }
                receipts.append("RECOGNIZER_ERROR", mode, mode, "provider_error");
                mainHandler.post(() -> completeProviderSession(false));
            }
        });
        bubble = new RitsuBubble(this, new RitsuBubble.Actions() {
            @Override public void toggleMute() {
                if (mode == ListeningPolicy.Mode.RECOGNIZING) mute();
                else if (mode == ListeningPolicy.Mode.MUTED) resume();
                else openApp();
            }
            @Override public void stopSession() { endSession(); }
            @Override public void hideBubble() {
                bubble.hide();
                updateNotification();
            }
            @Override public ListeningPolicy.Mode mode() { return mode; }
        });
        setForeground(false);
        homeCenterSync.start();
        receipts.append("SERVICE_CREATED", ListeningPolicy.Mode.OFF, mode, "explicit");
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_LISTEN.equals(action) || ACTION_SPEAK_ONCE.equals(action)
                || ACTION_TRANSCRIBE.equals(action)) startListening();
        else if (ACTION_MUTE.equals(action)) mute();
        else if (ACTION_RESUME.equals(action)) resume();
        else if (ACTION_SHOW_BUBBLE.equals(action)) {
            if (!bubble.show()) lastProblem = "Android overlay permission not granted";
        } else if (ACTION_HIDE_BUBBLE.equals(action)) bubble.hide();
        else if (ACTION_MEDIA_TALK.equals(action)) requestMediaFocus();
        else if (ACTION_SYNC_NOW.equals(action)) homeCenterSync.requestNow();
        else if (ACTION_PAUSE_WINDOW.equals(action)) setPauseWindow(
                intent.getIntExtra(EXTRA_PAUSE_MS, SpokenTurnBuffer.DEFAULT_PAUSE_MS));
        else if (ACTION_SPEAKER_PREFERENCE.equals(action))
            ControlStore.transition(this, ControlPolicy.ACTION_SPEAKER_PREFERENCE);
        else if (ACTION_STOP.equals(action)) {
            endSession();
            return START_NOT_STICKY;
        } else if (!ACTION_START.equals(action)) {
            receipts.append("UNKNOWN_ACTION", mode, mode, "rejected");
        }
        updateNotification();
        return START_NOT_STICKY;
    }

    private void setPauseWindow(int millis) {
        if (millis < SpokenTurnBuffer.MIN_PAUSE_MS ||
                millis > SpokenTurnBuffer.MAX_PAUSE_MS) {
            receipts.append("PAUSE_WINDOW_REJECTED", mode, mode, "invalid_duration");
            return;
        }
        pendingTurn.setPauseMs(millis);
        speechPauseMs = millis;
        getSharedPreferences("ritsu_voice_timing_v1", MODE_PRIVATE)
                .edit().putInt("pauseMs", millis).apply();
        // A changed preference must not instantly send the existing draft.
        if (pendingTurn.hasText() && !pendingTurn.isInSpeech()) {
            pendingTurn.speechEnded(SystemClock.elapsedRealtime());
            schedulePendingCommit();
        }
        receipts.append("PAUSE_WINDOW_SET", mode, mode, "user_preference");
        updateSpeechPreview();
    }

    private void cancelPendingCommit() {
        if (pendingCommit != null) mainHandler.removeCallbacks(pendingCommit);
        pendingCommit = null;
    }

    private void updateSpeechPreview() {
        pendingSpeechText = pendingTurn.preview();
        partialRevision++;
    }

    /** Wait beyond the provider's end-of-speech event. Restarting Google
     * recognition quickly lets the next thought cancel this pending send. */
    private void schedulePendingCommit() {
        cancelPendingCommit();
        if (!pendingTurn.hasText() || pendingTurn.isInSpeech()) return;
        long remaining = pendingTurn.remainingMs(SystemClock.elapsedRealtime());
        if (remaining < 0) return;
        final int generation = sessionGeneration;
        pendingCommit = () -> {
            pendingCommit = null;
            if (generation != sessionGeneration) return;
            if (pendingTurn.ready(SystemClock.elapsedRealtime())) {
                flushPendingTurn("thought_pause_expired");
            } else schedulePendingCommit();
        };
        mainHandler.postDelayed(pendingCommit, Math.max(1, remaining));
    }

    private void flushPendingTurn(String reason) {
        cancelPendingCommit();
        if (!pendingTurn.hasText()) return;
        String complete = pendingTurn.flush();
        updateSpeechPreview();
        // Speech belongs to the currently selected conversation tab.
        // A tab's machine preset is captured when the spoken turn commits,
        // not assumed at the moment a remote worker eventually sees it.
        RitsuWorkspace.Tab active=new RitsuWorkspace(this).active();
        try {
            String sticky=new StickySnippets(this).forTab(active.id);
            // Freeze context in the durable outbox at speech commitment.
            // Network retries replay these exact bytes without appending twice.
            String outgoing=StickyText.compose(complete,sticky);
            ledger.addInTab(active.id,active.machineId,"control","You",
                    outgoing,"LOCAL_QUEUED");
            feedRevision++;
            homeCenterSync.requestNow();
            recognitionStatus = "Spoken message queued with tab sticky context";
        }catch(RuntimeException error){
            // Fail closed rather than silently omit owner-required context.
            recognitionStatus = "Spoken turn NOT sent: sticky context error";
            receipts.append("LOCAL_SPOKEN_STICKY_FAILED",mode,mode,
                    error.getClass().getSimpleName());
            updateNotification();
            return;
        }
        receipts.append("LOCAL_SPOKEN_MESSAGE", mode, mode, reason);
        updateNotification();
    }

    private void startListening() {
        if (mode == ListeningPolicy.Mode.RECOGNIZING) return;
        if (mode == ListeningPolicy.Mode.MUTED) {
            resume();
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            failCapture("Microphone permission not granted");
            return;
        }
        ++sessionGeneration;
        consecutiveErrors = 0;
        clearCallbacks();
        try {
            setForeground(true);
            if (!speechSession.begin()) {
                failCapture("No active Android speech recognizer");
                return;
            }
            applyTransition(ListeningPolicy.Event.PROVIDER_STARTED,
                    "system_recognizer_owns_microphone");
            beginPlaybackWatch();
            recognitionStatus = "Google/system recognizer listening";
            scheduleTimeout(sessionGeneration);
            if (Settings.canDrawOverlays(this)) bubble.show();
        } catch (RuntimeException exception) {
            failCapture("Unable to start foreground Google recognition");
        }
    }

    /** Recognizer uses its own end-of-speech detector; Android does not provide
     * a guaranteed always-open transcription API. Pace bounded new sessions. */
    private void completeProviderSession(boolean success) {
        if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
        if (recognitionTimeout != null) mainHandler.removeCallbacks(recognitionTimeout);
        recognitionTimeout = null;
        // Silence/no-match is an expected idle condition, not provider failure.
        // Re-arm it slowly, without tripping the hardware-failure circuit breaker.
        boolean expectedIdle = !success && ("No matching words heard".equals(lastProblem)
                || "No speech detected before timeout".equals(lastProblem)
                || "No transcript returned by recognizer".equals(lastProblem)
                || lastProblem.startsWith("Speech session timed out"));
        if (success) { consecutiveErrors = 0; lastProblem = ""; }
        else if (!expectedIdle) ++consecutiveErrors;
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            failCapture("Recognition failed repeatedly; reopen Ritsu to try again. "
                    + lastProblem);
            return;
        }
        final int epoch = sessionGeneration;
        final int delay = success ? 450 : (expectedIdle ? 1500 : 2300);
        recognitionStatus = success ? "Rearming microphone for next phrase"
                : "Recognition paused; retrying after provider error";
        nextRecognition = () -> {
            nextRecognition = null;
            if (epoch != sessionGeneration || mode != ListeningPolicy.Mode.RECOGNIZING)
                return;
            mediaObservedInSession = mediaPause.otherAudioMayBeActive();
            if (!speechSession.begin()) {
                failCapture("Recognizer did not restart; " + lastProblem);
                return;
            }
            recognitionStatus = "Listening for next spoken phrase";
            scheduleTimeout(epoch);
            updateNotification();
        };
        mainHandler.postDelayed(nextRecognition, delay);
        updateNotification();
    }

    private void scheduleTimeout(int epoch) {
        recognitionTimeout = () -> {
            recognitionTimeout = null;
            if (epoch != sessionGeneration ||
                    mode != ListeningPolicy.Mode.RECOGNIZING) return;
            speechSession.cancel();
            lastProblem = "Speech session timed out, trying another bounded session";
            completeProviderSession(false);
        };
        mainHandler.postDelayed(recognitionTimeout, 45000);
    }

    private void beginPlaybackWatch() {
        mainHandler.removeCallbacks(playbackProbe);
        mediaObservedInSession = mediaPause.otherAudioMayBeActive();
        mainHandler.postDelayed(playbackProbe, 350);
    }

    private void clearCallbacks() {
        if (mainHandler != null) mainHandler.removeCallbacks(playbackProbe);
        if (recognitionTimeout != null) mainHandler.removeCallbacks(recognitionTimeout);
        if (nextRecognition != null) mainHandler.removeCallbacks(nextRecognition);
        recognitionTimeout = null;
        nextRecognition = null;
    }

    private void mute() {
        if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
        ++sessionGeneration;
        clearCallbacks();
        speechSession.cancel();
        flushPendingTurn("explicit_mute");
        mediaPause.release();
        voiceActivity = false;
        partialTranscript = "";
        partialRevision++;
        recognitionStatus = "Microphone muted";
        applyTransition(ListeningPolicy.Event.RECOGNITION_FINISHED,
                "system_recognizer_cancelled_on_mute");
    }

    private void resume() {
        if (mode != ListeningPolicy.Mode.MUTED) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            failCapture("Microphone permission revoked");
            return;
        }
        ++sessionGeneration;
        clearCallbacks();
        try {
            setForeground(true);
            if (!speechSession.begin()) {
                failCapture("Recognizer unavailable while resuming");
                return;
            }
            applyTransition(ListeningPolicy.Event.PROVIDER_STARTED,
                    "system_recognizer_resumed");
            beginPlaybackWatch();
            consecutiveErrors = 0;
            scheduleTimeout(sessionGeneration);
        } catch (RuntimeException e) {
            failCapture("Microphone resume rejected");
        }
    }

    private void requestMediaFocus() {
        boolean granted = mediaPause.requestPauseForVerifiedSpeech();
        mediaGuardStatus = granted
                ? "Android requested media pause; player compliance unverified"
                : "Media pause denied; media may continue";
        if (mediaFocusDeadline != null) mainHandler.removeCallbacks(mediaFocusDeadline);
        mediaFocusDeadline = null;
        if (granted) {
            mediaFocusDeadline = () -> {
                mediaPause.release();
                mediaGuardStatus = "Cooperative media pause lease expired";
                mediaFocusDeadline = null;
            };
            mainHandler.postDelayed(mediaFocusDeadline, 30000);
        }
    }

    private void failCapture(String reason) {
        ++sessionGeneration;
        clearCallbacks();
        speechSession.cancel();
        mediaPause.release();
        lastProblem = reason;
        recognitionStatus = reason;
        voiceActivity = false;
        partialTranscript = "";
        ListeningPolicy.Mode previous = mode;
        mode = ListeningPolicy.Mode.ERROR;
        liveMode = mode;
        receipts.append("FAILED", previous, mode, "recognizer_unavailable");
        updateNotification();
        if (bubble != null) bubble.refresh();
        try { setForeground(false); } catch (RuntimeException ignored) {}
    }

    private void applyTransition(ListeningPolicy.Event event, String reason) {
        ListeningPolicy.Mode previous = mode;
        mode = ListeningPolicy.next(mode, event);
        liveMode = mode;
        receipts.append(event.name(), previous, mode, reason);
        updateNotification();
        if (bubble != null) bubble.refresh();
    }

    private void openApp() {
        Intent i = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        startActivity(i);
    }

    private void endSession() {
        ++sessionGeneration;
        clearCallbacks();
        speechSession.cancel();
        flushPendingTurn("explicit_stop");
        mediaPause.release();
        if (mediaFocusDeadline != null) mainHandler.removeCallbacks(mediaFocusDeadline);
        mediaFocusDeadline = null;
        voiceActivity = false;
        ListeningPolicy.Mode previous = mode;
        mode = ListeningPolicy.next(mode, ListeningPolicy.Event.STOPPED);
        liveMode = mode;
        receipts.append("SESSION_STOPPED", previous, mode, "explicit_stop");
        bubble.hide();
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    private void setForeground(boolean microphone) {
        if (Build.VERSION.SDK_INT >= 34) {
            int types = ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE;
            if (microphone) types |= ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;
            startForeground(NOTIFICATION_ID, notification(), types);
        } else if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, notification(),
                    microphone ? ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE : 0);
        } else {
            startForeground(NOTIFICATION_ID, notification());
        }
    }

    private void updateNotification() {
        getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, notification());
    }

    private Notification notification() {
        PendingIntent open = PendingIntent.getActivity(this, 41,
                new Intent(this, MainActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        String detail = mode == ListeningPolicy.Mode.RECOGNIZING ? recognitionStatus
                : mode == ListeningPolicy.Mode.MUTED ? "Mic muted"
                : mode == ListeningPolicy.Mode.ERROR ? "Recognizer error · open app"
                : "Mic off";
        Notification.Builder builder = new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentTitle("Ritsu")
                .setContentText(detail + " · " + RitsuLocalSync.status)
                .setCategory(Notification.CATEGORY_SERVICE)
                .setContentIntent(open)
                .setShowWhen(false)
                .setOngoing(true)
                .setOnlyAlertOnce(true);
        if (mode == ListeningPolicy.Mode.RECOGNIZING) {
            builder.addAction(new Notification.Action.Builder(null, "Mute mic",
                    serviceAction(ACTION_MUTE, 47)).build());
        } else if (mode == ListeningPolicy.Mode.MUTED) {
            builder.addAction(new Notification.Action.Builder(null, "Resume mic",
                    serviceAction(ACTION_RESUME, 48)).build());
        } else {
            builder.addAction(new Notification.Action.Builder(null, "Open controls",
                    open).build());
        }
        builder.addAction(new Notification.Action.Builder(null, "Stop",
                serviceAction(ACTION_STOP, 49)).build());
        return builder.build();
    }

    private PendingIntent serviceAction(String action, int id) {
        return PendingIntent.getService(this, id,
                new Intent(this, RitsuControlService.class).setAction(action),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    @Override public void onDestroy() {
        ++sessionGeneration;
        clearCallbacks();
        cancelPendingCommit();
        if (speechSession != null) speechSession.cancel();
        if (homeCenterSync != null) homeCenterSync.close();
        if (mediaPause != null) mediaPause.release();
        if (bubble != null) bubble.hide();
        voiceActivity = false;
        ListeningPolicy.Mode previous = mode;
        mode = ListeningPolicy.Mode.OFF;
        liveMode = mode;
        if (receipts != null)
            receipts.append("SERVICE_DESTROYED", previous, mode, "service_stop");
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent i) { return null; }
}
