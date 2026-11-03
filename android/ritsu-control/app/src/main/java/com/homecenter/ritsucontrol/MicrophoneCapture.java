package com.homecenter.ritsucontrol;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.audiofx.AcousticEchoCanceler;
import android.media.MediaRecorder;
import java.util.concurrent.atomic.AtomicBoolean;

/** Local-only always-on audio energy monitor; owns and releases AudioRecord.
 * No file, ASR, socket, persistent audio buffer or upload.
 * stop() is synchronous about capture shutdown and is called before UI says MUTED. */
final class MicrophoneCapture {
    interface Observer {
        void onSpeechChanged(boolean speaking);
        void onUtterance(short[] pcm);
        void onFailure(String reason);
    }
    private final Context context;
    private final Observer observer;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private AudioRecord recorder;
    private AcousticEchoCanceler echoCanceler;
    private volatile boolean echoEnabled;
    private Thread worker;
    private int generation;

    MicrophoneCapture(Context context, Observer observer) {
        this.context = context; this.observer = observer;
    }

    synchronized boolean start() {
        if (running.get()) return true;
        if (context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED)
            return false;
        int minimum = AudioRecord.getMinBufferSize(VoiceActivityGate.SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        if (minimum <= 0) return false;
        AudioRecord record = null;
        try {
            record = new AudioRecord(MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                    VoiceActivityGate.SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    Math.max(minimum, VoiceActivityGate.FRAME_SAMPLES * 2 * 8));
            if (record.getState() != AudioRecord.STATE_INITIALIZED) { record.release(); return false; }
            if (AcousticEchoCanceler.isAvailable()) {
                try {
                    echoCanceler = AcousticEchoCanceler.create(record.getAudioSessionId());
                    if (echoCanceler != null) {
                        echoCanceler.setEnabled(true);
                        echoEnabled = echoCanceler.getEnabled();
                    }
                } catch (RuntimeException ignored) { echoEnabled = false; }
            }
            record.startRecording();
            if (record.getRecordingState() != AudioRecord.RECORDSTATE_RECORDING) {
                record.release(); return false;
            }
            final int epoch = ++generation;
            recorder = record;
            running.set(true);
            final AudioRecord capture = record;
            worker = new Thread(() -> captureLoop(capture, epoch), "ritsu-microphone-vad");
            worker.start();
            return true;
        } catch (RuntimeException failure) {
            if (record != null) try { record.release(); } catch (Exception ignored) {}
            return false;
        }
    }

    private void captureLoop(AudioRecord record, int epoch) {
        VoiceActivityGate gate = new VoiceActivityGate();
        UtteranceAccumulator utterances = new UtteranceAccumulator();
        short[] frame = new short[VoiceActivityGate.FRAME_SAMPLES];
        boolean announced = false;
        String failure = null;
        try {
            while (running.get() && epoch == generation) {
                int n = record.read(frame, 0, frame.length, AudioRecord.READ_BLOCKING);
                if (!running.get() || epoch != generation) break;
                if (n <= 0) { failure = "audio_read_failed"; break; }
                boolean speech = gate.accept(frame, n);
                short[] completed = utterances.accept(frame, n);
                if (completed != null) {
                    observer.onUtterance(completed);
                    // Only one utterance may own the microphone before ASR.
                    // Stop the worker from making additional submissions.
                    break;
                }
                if (speech != announced) {
                    announced = speech;
                    observer.onSpeechChanged(speech);
                }
            }
        } catch (RuntimeException error) { if (running.get()) failure = "audio_capture_exception"; }
        finally {
            if (announced) observer.onSpeechChanged(false);
            if (failure != null && running.get() && epoch == generation)
                observer.onFailure(failure);
        }
    }

    synchronized void stop() {
        running.set(false);
        generation++;
        AudioRecord current = recorder;
        recorder = null;
        AcousticEchoCanceler effect = echoCanceler;
        echoCanceler = null;
        echoEnabled = false;
        if (effect != null) {
            try { effect.release(); } catch (RuntimeException ignored) {}
        }
        if (current != null) {
            try { current.stop(); } catch (RuntimeException ignored) {}
            try { current.release(); } catch (RuntimeException ignored) {}
        }
        Thread t = worker;
        worker = null;
        if (t != null && t != Thread.currentThread()) {
            try { t.join(400); } catch (InterruptedException interrupt) {
                Thread.currentThread().interrupt();
            }
        }
    }

    boolean isRecording() { return running.get() && recorder != null; }
    boolean echoCancellationEnabled() { return echoEnabled; }
}
