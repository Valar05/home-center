package com.homecenter.ritsucontrol;

/** Deterministic energy-based VAD. Not speech recognition or a wake word engine.
 * Input is PCM16 mono at 16 kHz, 320 samples/frame (20 ms). */
final class VoiceActivityGate {
    static final int SAMPLE_RATE = 16000;
    static final int FRAME_SAMPLES = 320;
    static final int START_FRAMES = 3;
    static final int END_FRAMES = 35;
    static final int MIN_ENERGY = 1200;
    private int above = 0;
    private int below = 0;
    private boolean speaking = false;

    boolean accept(short[] samples, int count) {
        if (count <= 0 || count > samples.length) throw new IllegalArgumentException("invalid frame size");
        long sum = 0;
        for (int i = 0; i < count; i++) sum += Math.abs((int) samples[i]);
        long energy = sum / count;
        if (energy >= MIN_ENERGY) {
            above = Math.min(START_FRAMES, above + 1);
            below = 0;
            if (!speaking && above >= START_FRAMES) speaking = true;
        } else {
            above = 0;
            below = Math.min(END_FRAMES, below + 1);
            if (speaking && below >= END_FRAMES) speaking = false;
        }
        return speaking;
    }
    boolean isSpeaking() { return speaking; }
}
