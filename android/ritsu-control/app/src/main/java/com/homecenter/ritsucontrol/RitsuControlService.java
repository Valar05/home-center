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
import android.provider.Settings;

/**
 * Home Center Ritsu local control layer.
 * Real microphone, local-only VAD; no audio stream, transcript, wake-word,
 * or remote ChatGPT command is implemented here.
 *
 * Starts listening ONLY after a user-visible Activity requests RECORD_AUDIO
 * permission. No BOOT_COMPLETED receiver and no restart-on-kill behavior.
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
    static final String ACTION_STOP = "com.homecenter.ritsucontrol.STOP";
    // Deliberately do not handle Stage A's misleading MIC_REQUEST action.
    private static final String CHANNEL = "ritsu_control_notification_v2";
    private static final int NOTIFICATION_ID = 19644;
    static volatile ListeningPolicy.Mode liveMode = ListeningPolicy.Mode.OFF;
    static volatile boolean voiceActivity = false;
    static volatile String lastProblem = "";
    static volatile String lastTranscript = "";
    static volatile long transcriptRevision = 0;
    static volatile String partialTranscript = "";
    static volatile long partialRevision = 0;
    static volatile String recognitionStatus = "Not started";

    private ListeningPolicy.Mode mode = ListeningPolicy.Mode.OFF;
    private MicrophoneCapture capture;
    private ControlReceipts receipts;
    private RitsuBubble bubble;
    private Handler mainHandler;
    private SystemSpeechSession speechSession;
    private Runnable recognitionTimeout;
    private MediaPauseLease mediaPause;
    private ConversationLedger chatLedger;
    static volatile long feedRevision = 0;

    @Override public void onCreate() {
        super.onCreate();
        mainHandler = new Handler(Looper.getMainLooper());
        receipts = new ControlReceipts(this);
        mediaPause = new MediaPauseLease(this);
        chatLedger = new ConversationLedger(this);
        liveMode = ListeningPolicy.Mode.OFF;
        voiceActivity = false;
        lastProblem = "";
        lastTranscript = "";
        transcriptRevision = 0;
        partialTranscript = "";
        partialRevision = 0;
        recognitionStatus = "Not started";
        // Clear Stage A's stale "mic requested" marker.
        ControlStore.transition(this, ControlPolicy.ACTION_START);
        getSystemService(NotificationManager.class).createNotificationChannel(
                new NotificationChannel(CHANNEL, "Ritsu listening controls", NotificationManager.IMPORTANCE_LOW));
        capture = new MicrophoneCapture(this, new MicrophoneCapture.Observer() {
            @Override public void onSpeechChanged(boolean speaking) {
                mainHandler.post(() -> {
                    if (mode != ListeningPolicy.Mode.LISTENING) return;
                    if (voiceActivity == speaking) return;
                    voiceActivity = speaking;
                    receipts.append(speaking ? "SPEECH_BEGIN" : "SPEECH_END", mode, mode, "local_energy_gate");
                    if (bubble != null) bubble.refresh();
                });
            }
            @Override public void onUtterance(short[] pcm) {
                mainHandler.post(() -> automaticUtterance(pcm));
            }
            @Override public void onFailure(String reason) {
                mainHandler.post(() -> failCapture(reason));
            }
        });
        speechSession = new SystemSpeechSession(this, new SystemSpeechSession.Observer() {
            @Override public void partialTranscript(String text) {
                partialTranscript = text;
                partialRevision++;
                recognitionStatus = "Interim speech recognized (not yet final)";
            }
            @Override public void status(String message) {
                recognitionStatus = message;
                updateNotification();
            }
            @Override public void finalTranscript(String text) {
                lastTranscript = text;
                transcriptRevision++;
                if (chatLedger != null) {
                    chatLedger.add("dialogue", "You", text,
                            ConversationLedger.OUTBOX);
                    feedRevision++;
                }
                partialTranscript = "";
                recognitionStatus = "Recognized words received; NOT sent";
                receipts.append("ASR_TEXT_READY", mode, mode, "private_transcript_not_logged");
                // Finish only after the recognizer releases the microphone.
                mainHandler.post(() -> completeRecognition());
            }
            @Override public void failed(String reason) {
                recognitionStatus = reason;
                lastProblem = reason;
                receipts.append("ASR_FAILED", mode, mode, "provider_error_no_text");
                mainHandler.post(() -> completeRecognition());
            }
        });
        bubble = new RitsuBubble(this, new RitsuBubble.Actions() {
            @Override public void toggleMute() {
                if (mode == ListeningPolicy.Mode.LISTENING ||
                    mode == ListeningPolicy.Mode.RECOGNIZING) mute();
                else if (mode == ListeningPolicy.Mode.MUTED) resume();
                else openApp();
            }
            @Override public void stopSession() { endSession(); }
            @Override public void hideBubble() { bubble.hide(); updateNotification(); }
            @Override public ListeningPolicy.Mode mode() { return mode; }
        });
        // An idle foreground service does not obtain the microphone service type.
        setForeground(false);
        receipts.append("SERVICE_CREATED", ListeningPolicy.Mode.OFF, mode, "explicit_control");
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_LISTEN.equals(action)) startListening();
        else if (ACTION_TRANSCRIBE.equals(action)) recognizeOnce();
        else if (ACTION_SPEAK_ONCE.equals(action)) startAndRecognizeOnce();
        else if (ACTION_MUTE.equals(action)) mute();
        else if (ACTION_RESUME.equals(action)) resume();
        else if (ACTION_SHOW_BUBBLE.equals(action)) {
            if (!bubble.show()) lastProblem = "Bubble requires Android display-over-other-apps permission";
        } else if (ACTION_HIDE_BUBBLE.equals(action)) bubble.hide();
        else if (ACTION_SPEAKER_PREFERENCE.equals(action))
            ControlStore.transition(this, ControlPolicy.ACTION_SPEAKER_PREFERENCE);
        else if (ACTION_STOP.equals(action)) { endSession(); return START_NOT_STICKY; }
        else if (!ACTION_START.equals(action)) {
            receipts.append("UNKNOWN_ACTION_IGNORED", mode, mode, "not_allowed");
        }
        updateNotification();
        return START_NOT_STICKY;
    }

    private void startListening() {
        if (mode == ListeningPolicy.Mode.LISTENING || mode == ListeningPolicy.Mode.MUTED) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            failCapture("microphone_permission_not_granted"); return;
        }
        try {
            setForeground(true);
            if (!capture.start()) { failCapture("audio_device_unavailable"); return; }
            applyTransition(ListeningPolicy.Event.CAPTURE_STARTED, "audio_record_started");
            if (Settings.canDrawOverlays(this)) bubble.show();
        } catch (RuntimeException exception) {
            failCapture("microphone_foreground_start_rejected");
        }
    }

    private void mute() {
        if (mode == ListeningPolicy.Mode.RECOGNIZING) {
            cancelRecognition("User muted during Google recognition");
            applyTransition(ListeningPolicy.Event.RECOGNITION_FINISHED,
                    "recognizer_cancelled_audio_released");
            return;
        }
        if (mode != ListeningPolicy.Mode.LISTENING) return;
        capture.stop(); // Actual audio hardware capture is stopped BEFORE reporting MUTED.
        voiceActivity = false;
        applyTransition(ListeningPolicy.Event.MUTED_RELEASED, "audio_record_released");
        // Keep existing foreground microphone service, so user can resume from
        // a notification or floating bubble without starting a new background FGS.
    }


    /** Explicit one-shot speech-to-text. This is NOT a continuous
     * SpeechRecognizer loop: Android's service may limit session duration
     * and use Google's cloud. AudioRecord is released BEFORE ASR starts. */
    /** One visible-user-triggered action, not a second hidden mode button.
     * Starts an authorized FGS, then immediately hands the microphone to
     * Android's default speech provider for exactly one utterance. */
    private void startAndRecognizeOnce() {
        if (mode == ListeningPolicy.Mode.RECOGNIZING) {
            recognitionStatus = "Recognition already in progress";
            return;
        }
        if (mode == ListeningPolicy.Mode.MUTED) {
            recognitionStatus = "Mic muted: resume before recognition";
            return;
        }
        if (mode == ListeningPolicy.Mode.OFF || mode == ListeningPolicy.Mode.ERROR) {
            startListening();
        }
        if (mode == ListeningPolicy.Mode.LISTENING) recognizeOnce();
    }

    /** Automatic on local VAD silence after capturing the *whole* utterance.
     * This is never called with media playing, because VAD cannot prove
     * whether a nearby speaker or human supplied the waveform. */
    private void automaticUtterance(short[] pcm) {
        if (mode != ListeningPolicy.Mode.LISTENING) return;
        // Conservative self-audio guard: no ambient media transcripts can be
        // interpreted as user commands. Near-end verification while media plays
        // is still an unimplemented full-duplex acceptance requirement.
        if (mediaPause.otherAudioMayBeActive()) {
            receipts.append("AUDIO_PLAYBACK_BLOCKED", mode, mode,
                    "untrusted_phone_playback_no_human_proof");
            recognitionStatus = "Phone media detected: rejected ambiguous speech";
            capture.stop();
            if (!capture.start()) failCapture("audio_recorder_could_not_rearm");
            updateNotification();
            return;
        }
        capture.stop();
        voiceActivity = false;
        applyTransition(ListeningPolicy.Event.RECOGNITION_STARTED,
                "silence_finalized_utterance_vad_released");
        lastTranscript = "";
        partialTranscript = "";
        partialRevision++;
        recognitionStatus = "Silence detected; sending captured PCM to Android recognizer";
        if (!speechSession.beginCaptured(pcm)) {
            applyTransition(ListeningPolicy.Event.RECOGNITION_FINISHED,
                    "external_audio_recognizer_unavailable");
            resume();
            return;
        }
        scheduleRecognitionTimeout();
        updateNotification();
    }

    private void scheduleRecognitionTimeout() {
        recognitionTimeout = () -> {
            if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
            cancelRecognition("Recognition timeout (45s)");
            applyTransition(ListeningPolicy.Event.RECOGNITION_FINISHED, "asr_timeout");
            resume();
        };
        mainHandler.postDelayed(recognitionTimeout, 45000);
    }

    private void recognizeOnce() {
        if (mode != ListeningPolicy.Mode.LISTENING || speechSession.isActive()) return;
        capture.stop();
        voiceActivity = false;
        applyTransition(ListeningPolicy.Event.RECOGNITION_STARTED, "vad_released_for_google_asr");
        lastTranscript = "";
        partialTranscript = "";
        partialRevision++;
        recognitionStatus = "Requesting system speech recognizer";
        if (!speechSession.begin()) {
            applyTransition(ListeningPolicy.Event.RECOGNITION_FINISHED, "recognizer_unavailable");
            resume();
            return;
        }
        scheduleRecognitionTimeout();
        updateNotification();
    }
    private void completeRecognition() {
        if (mode != ListeningPolicy.Mode.RECOGNIZING) return;
        if (recognitionTimeout != null) mainHandler.removeCallbacks(recognitionTimeout);
        recognitionTimeout = null;
        applyTransition(ListeningPolicy.Event.RECOGNITION_FINISHED,
                "system_recognizer_released");
        mediaPause.release();
        resume(); // Re-arm VAD; do not auto-run another recognition session.
    }
    private void cancelRecognition(String reason) {
        if (recognitionTimeout != null) mainHandler.removeCallbacks(recognitionTimeout);
        recognitionTimeout = null;
        if (speechSession != null) speechSession.cancel();
        recognitionStatus = reason;
    }

    private void resume() {
        if (mode != ListeningPolicy.Mode.MUTED) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            failCapture("microphone_permission_revoked"); return;
        }
        try {
            setForeground(true);
            if (!capture.start()) { failCapture("audio_device_unavailable"); return; }
            applyTransition(ListeningPolicy.Event.RESUMED_CAPTURE, "audio_record_resumed");
        } catch (RuntimeException exception) {
            failCapture("microphone_restart_rejected");
        }
    }

    private void failCapture(String reason) {
        cancelRecognition("Recording stopped after error");
        mediaPause.release();
        capture.stop();
        voiceActivity = false;
        lastProblem = reason;
        applyTransition(ListeningPolicy.Event.FAILED, reason);
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
        startActivity(i); // Only user-initiated from the visible floating bubble.
    }

    private void endSession() {
        cancelRecognition("Session stopped");
        mediaPause.release();
        if (capture != null) capture.stop();
        voiceActivity = false;
        ListeningPolicy.Mode previous = mode;
        mode = ListeningPolicy.next(mode, ListeningPolicy.Event.STOPPED);
        liveMode = mode;
        receipts.append("SESSION_STOPPED", previous, mode, "explicit_user_stop");
        if (bubble != null) bubble.hide();
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
        String detail = mode == ListeningPolicy.Mode.LISTENING ? "Listening locally"
                : mode == ListeningPolicy.Mode.RECOGNIZING ? "Google speech recognition"
                : mode == ListeningPolicy.Mode.MUTED ? "Mic muted (hardware released)"
                : mode == ListeningPolicy.Mode.ERROR ? "Mic error · open to inspect" : "Mic off";
        Notification.Builder builder = new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentTitle("Ritsu")
                .setContentText(detail + " · No ChatGPT submission")
                .setCategory(Notification.CATEGORY_SERVICE)
                .setContentIntent(open)
                .setShowWhen(false)
                .setOngoing(true)
                .setOnlyAlertOnce(true);
        if (mode == ListeningPolicy.Mode.LISTENING) {
            builder.addAction(new Notification.Action.Builder(null, "Mute mic",
                    serviceAction(ACTION_MUTE, 47)).build());
        } else if (mode == ListeningPolicy.Mode.RECOGNIZING) {
            builder.addAction(new Notification.Action.Builder(null, "Cancel recognition",
                    serviceAction(ACTION_MUTE, 47)).build());
        } else if (mode == ListeningPolicy.Mode.MUTED) {
            builder.addAction(new Notification.Action.Builder(null, "Resume mic",
                    serviceAction(ACTION_RESUME, 48)).build());
        } else {
            // Opening a visible Activity is necessary for the first microphone start.
            builder.addAction(new Notification.Action.Builder(null, "Open controls", open).build());
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
        cancelRecognition("Service destroyed");
        if (mediaPause != null) mediaPause.release();
        if (capture != null) capture.stop();
        if (bubble != null) bubble.hide();
        voiceActivity = false;
        ListeningPolicy.Mode previous = mode;
        mode = ListeningPolicy.Mode.OFF;
        liveMode = mode;
        if (receipts != null) receipts.append("SERVICE_DESTROYED", previous, mode, "system_or_explicit");
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
