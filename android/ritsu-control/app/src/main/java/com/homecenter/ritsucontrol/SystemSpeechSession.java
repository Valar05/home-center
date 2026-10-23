package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.Intent;
import android.media.AudioFormat;
import android.os.Build;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
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
        void partialTranscript(String text);
        void finalTranscript(String text);
        void failed(String reason);
    }
    private final Context app;
    private final Observer observer;
    private SpeechRecognizer recognizer;
    private int epoch;
    private ParcelFileDescriptor readPipe;
    private ParcelFileDescriptor writePipe;
    private Thread pcmWriter;
    private boolean active;

    SystemSpeechSession(Context context, Observer observer) {
        app = context.getApplicationContext();
        this.observer = observer;
    }
    boolean isActive() { return active; }

    boolean begin() { return beginWithPcm(null); }

    /** Android 13+ optional external PCM recognizer source.
     * The system provider may ignore EXTRA_AUDIO_SOURCE. We do not substitute
     * live input silently if pipe playback is not supported. */
    boolean beginCaptured(short[] pcm) {
        if (pcm == null || pcm.length == 0) {
            observer.failed("No recorded utterance");
            return false;
        }
        if (Build.VERSION.SDK_INT < 33) {
            observer.failed("This recognizer needs Android 13+ external audio support");
            return false;
        }
        return beginWithPcm(pcm);
    }

    private boolean beginWithPcm(short[] pcm) {
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
                    observer.failed(explainError(error));
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
                    // Partials are display-only, never a command or final turn.
                    ArrayList<String> options = partial == null ? null :
                            partial.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    if (options != null && !options.isEmpty() && options.get(0) != null
                            && !options.get(0).trim().isEmpty()) {
                        String text = options.get(0).trim();
                        observer.partialTranscript(text.substring(0, Math.min(5000, text.length())));
                    } else {
                        observer.status("Listening for complete utterance");
                    }
                }
                @Override public void onEvent(int eventType, Bundle params) {}
            });
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
            if (pcm != null) {
                ParcelFileDescriptor[] pipe = ParcelFileDescriptor.createPipe();
                readPipe = pipe[0];
                writePipe = pipe[1];
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE, readPipe);
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_CHANNEL_COUNT, 1);
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_ENCODING,
                        AudioFormat.ENCODING_PCM_16BIT);
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_SAMPLING_RATE, 16000);
            }
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
            if (pcm != null) startPcmWriter(pcm, ticket);
            return true;
        } catch (RuntimeException | IOException error) {
            active = false;
            observer.failed("Recognition start rejected: " + error.getClass().getSimpleName());
            cleanup();
            return false;
        }
    }
    private static String explainError(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_NO_MATCH: return "Google recognizer heard no matching words";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "No speech detected before timeout";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "System recognizer is busy";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "Microphone permission rejected by recognizer";
            case SpeechRecognizer.ERROR_NETWORK:
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "System recognition network error";
            case SpeechRecognizer.ERROR_AUDIO: return "System recognizer microphone error";
            case SpeechRecognizer.ERROR_CLIENT: return "System recognizer client error";
            case SpeechRecognizer.ERROR_SERVER: return "System recognizer service error";
            default: return "Speech recognizer error code " + error;
        }
    }
    private void startPcmWriter(short[] pcm, int ticket) {
        final ParcelFileDescriptor target = writePipe;
        pcmWriter = new Thread(() -> {
            try (FileOutputStream output = new FileOutputStream(target.getFileDescriptor())) {
                byte[] chunk = new byte[UtteranceAccumulator.FRAME_SAMPLES * 2];
                for (int pos = 0; pos < pcm.length && ticket == epoch && active;
                     pos += UtteranceAccumulator.FRAME_SAMPLES) {
                    int n = Math.min(UtteranceAccumulator.FRAME_SAMPLES, pcm.length-pos);
                    for (int i=0; i<n; i++) {
                        int v=pcm[pos+i];
                        chunk[i*2]=(byte)(v&255);
                        chunk[i*2+1]=(byte)((v>>>8)&255);
                    }
                    output.write(chunk,0,n*2);
                    // Replay at real-time cadence; avoids overrunning providers
                    // which interpret the supplied file descriptor as live PCM.
                    Thread.sleep(20);
                }
            } catch (IOException | InterruptedException ignored) {
                Thread.currentThread().interrupt();
            } finally {
                try { target.close(); } catch (IOException ignored) {}
            }
        }, "ritsu-asr-pcm-feeder");
        pcmWriter.start();
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
        if (readPipe != null) {
            try { readPipe.close(); } catch (IOException ignored) {}
            readPipe = null;
        }
        if (writePipe != null) {
            try { writePipe.close(); } catch (IOException ignored) {}
            writePipe = null;
        }
        if (pcmWriter != null) {
            pcmWriter.interrupt();
            pcmWriter = null;
        }
        if (recognizer != null) {
            try { recognizer.destroy(); } catch (RuntimeException ignored) {}
            recognizer = null;
        }
    }
}
