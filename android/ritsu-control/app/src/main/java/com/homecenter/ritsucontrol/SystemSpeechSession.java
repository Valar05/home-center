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

/** One BOUNDED, live-microphone Android recognizer session.
 *
 * Do not use EXTRA_AUDIO_SOURCE by default: a provider may ignore it.
 * Android's system recognizer handles its own speech-ending/silence detection.
 * Callbacks notify the foreground Ritsu service; it is responsible for
 * paced rearming after onResults or onError. This is not a guaranteed
 * continuous ASR facility and may use Google's network service.
 */
final class SystemSpeechSession {
    interface Observer {
        void status(String value);
        void partialTranscript(String text);
        void speechStarted();
        void speechEnded();
        void finalTranscript(String text);
        void failed(String reason);
    }

    private final Context app;
    private final Observer observer;
    private SpeechRecognizer recognizer;
    private int epoch;
    private boolean active;

    SystemSpeechSession(Context context, Observer observer) {
        this.app = context.getApplicationContext();
        this.observer = observer;
    }

    boolean isActive() { return active; }

    /** Must be called on Android main thread from an already-authorized
     * user-started microphone foreground service. */
    boolean begin() {
        if (active) return false;
        if (!SpeechRecognizer.isRecognitionAvailable(app)) {
            observer.failed("No Android speech recognition provider available");
            return false;
        }
        final int ticket = ++epoch;
        try {
            recognizer = SpeechRecognizer.createSpeechRecognizer(app);
            recognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) {
                    if (ticket == epoch && active) observer.status("Google recognizer ready; speak");
                }
                @Override public void onBeginningOfSpeech() {
                    if (ticket == epoch && active) {
                        observer.speechStarted();
                        observer.status("Speech detected");
                    }
                }
                @Override public void onRmsChanged(float rmsDb) {}
                @Override public void onBufferReceived(byte[] buffer) {}
                @Override public void onEndOfSpeech() {
                    if (ticket == epoch && active) {
                        observer.speechEnded();
                        observer.status("Silence detected; preparing words");
                    }
                }
                @Override public void onError(int error) {
                    if (ticket != epoch || !active) return;
                    finish();
                    observer.failed(explainError(error));
                }
                @Override public void onResults(Bundle results) {
                    if (ticket != epoch || !active) return;
                    ArrayList<String> alternatives = results == null ? null
                            : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    String candidate = alternatives == null || alternatives.isEmpty()
                            ? "" : String.valueOf(alternatives.get(0)).trim();
                    finish();
                    if (candidate.isEmpty()) observer.failed("No transcript returned by recognizer");
                    else observer.finalTranscript(candidate.substring(0, Math.min(5000, candidate.length())));
                }
                @Override public void onPartialResults(Bundle results) {
                    if (ticket != epoch || !active) return;
                    ArrayList<String> alternatives = results == null ? null
                            : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    if (alternatives != null && !alternatives.isEmpty()
                            && alternatives.get(0) != null) {
                        String result = alternatives.get(0).trim();
                        if (!result.isEmpty())
                            observer.partialTranscript(result.substring(0, Math.min(5000, result.length())));
                    }
                }
                @Override public void onEvent(int eventType, Bundle params) {}
            });
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
            // Endpointer *hints* only. Google may ignore these entirely.
            // Conservative values permit a natural thinking pause within
            // a single provider session if supported by the device.
            intent.putExtra(
                    RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS,
                    1350L);
            intent.putExtra(
                    RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS,
                    2300L);
            if (Build.VERSION.SDK_INT >= 33) {
                intent.putExtra(RecognizerIntent.EXTRA_ENABLE_BIASING_DEVICE_CONTEXT, true);
                intent.putStringArrayListExtra(RecognizerIntent.EXTRA_BIASING_STRINGS,
                        new ArrayList<>(Arrays.asList(
                                "Ritsu", "Serin", "She-Raw", "Imogen", "Cori",
                                "Chromium Throne", "Home Center", "THECAULDRON",
                                "Fleshpunk", "Vanguard", "Pose Lab")));
            }
            active = true;
            observer.status("Starting Android microphone recognition");
            recognizer.startListening(intent);
            return true;
        } catch (RuntimeException e) {
            active = false;
            cleanup();
            observer.failed("Recognizer failed to start: " + e.getClass().getSimpleName());
            return false;
        }
    }

    void cancel() {
        ++epoch;
        active = false;
        if (recognizer != null) {
            try { recognizer.cancel(); } catch (RuntimeException ignored) {}
        }
        cleanup();
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

    private static String explainError(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_NO_MATCH: return "No matching words heard";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "No speech detected before timeout";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "Google recognizer was busy";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "System recognizer microphone permission denied";
            case SpeechRecognizer.ERROR_NETWORK:
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "System recognition network unavailable";
            case SpeechRecognizer.ERROR_AUDIO: return "System recognizer audio error";
            case SpeechRecognizer.ERROR_CLIENT: return "System speech recognition client error";
            case SpeechRecognizer.ERROR_SERVER: return "System speech recognition service error";
            default: return "Google speech recognition error " + error;
        }
    }
}
