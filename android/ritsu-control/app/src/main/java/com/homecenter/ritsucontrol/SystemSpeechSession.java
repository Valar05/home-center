package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import java.util.ArrayList;
import java.util.Arrays;

/**
 * One explicitly requested bounded spoken utterance via the system's
 * default recognition service. Google recognition can be the provider
 * but the app cannot assume or read Gboard's private correction model.
 *
 * No continuous recognition loop and no app-initiated network upload.
 * A recognition provider MAY process audio online: the UI says so.
 * Android main thread only.
 */
final class SystemSpeechSession {
    interface Observer {
        void status(String value);
        void finalTranscript(String text);
        void failed(String reason);
    }
    private final Context app;
    private final Observer observer;
    private SpeechRecognizer recognizer;
    private int epoch;
    private boolean active;

    SystemSpeechSession(Context context, Observer observer) {
        app = context.getApplicationContext();
        this.observer = observer;
    }
    boolean isActive() { return active; }

    boolean begin() {
        if (active) return false;
        if (!SpeechRecognizer.isRecognitionAvailable(app)) {
            observer.failed("No Android recognition service available");
            return false;
        }
        final int ticket = ++epoch;
        try {
            recognizer = SpeechRecognizer.createSpeechRecognizer(app);
            recognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) {
                    if (ticket == epoch && active) observer.status("Speak now");
                }
                @Override public void onBeginningOfSpeech() {
                    if (ticket == epoch && active) observer.status("Recognizing speech");
                }
                @Override public void onRmsChanged(float rmsDb) {}
                @Override public void onBufferReceived(byte[] buffer) {}
                @Override public void onEndOfSpeech() {
                    if (ticket == epoch && active) observer.status("Finishing transcription");
                }
                @Override public void onError(int error) {
                    if (ticket != epoch || !active) return;
                    observer.failed("Recognition provider error " + error);
                    finish();
                }
                @Override public void onResults(Bundle results) {
                    if (ticket != epoch || !active) return;
                    ArrayList<String> options = results == null ? null
                            : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    String candidate = options == null || options.isEmpty() ? ""
                            : String.valueOf(options.get(0)).trim();
                    if (!candidate.isEmpty())
                        observer.finalTranscript(candidate.substring(0, Math.min(5000, candidate.length())));
                    else observer.failed("Recognition returned no words");
                    finish();
                }
                @Override public void onPartialResults(Bundle partial) {
                    if (ticket != epoch || !active) return;
                    // Keep private partials ephemeral. Never enqueue them as commands.
                    observer.status("Listening for complete utterance");
                }
                @Override public void onEvent(int eventType, Bundle params) {}
            });
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
            if (Build.VERSION.SDK_INT >= 33) {
                intent.putExtra(RecognizerIntent.EXTRA_ENABLE_BIASING_DEVICE_CONTEXT, true);
                intent.putStringArrayListExtra(RecognizerIntent.EXTRA_BIASING_STRINGS,
                        new ArrayList<>(Arrays.asList(
                                "Ritsu", "Serin", "She-Raw", "Imogen", "Cori",
                                "Chromium Throne", "Home Center", "THECAULDRON",
                                "Fleshpunk", "Vanguard", "Pose Lab")));
                // The provider may ignore vocabulary hints. Never promise otherwise.
            }
            active = true;
            observer.status("Starting default Android speech recognition");
            recognizer.startListening(intent);
            return true;
        } catch (RuntimeException error) {
            active = false;
            observer.failed("Recognition start rejected: " + error.getClass().getSimpleName());
            cleanup();
            return false;
        }
    }
    void cancel() {
        ++epoch;
        active = false;
        if (recognizer != null) {
            try { recognizer.cancel(); } catch (RuntimeException ignored) {}
            cleanup();
        }
    }
    private void finish() {
        active = false;
        cleanup();
    }
    private void cleanup() {
        if (recognizer != null) {
            try { recognizer.destroy(); } catch (RuntimeException ignored) {}
            recognizer = null;
        }
    }
}
