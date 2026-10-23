package com.homecenter.ritsucontrol;

import java.util.ArrayDeque;
import java.util.ArrayList;

/** Bounded PCM16 16kHz utterance segmenter. No remote calls or disk writes.
 * 400ms pre-roll, 700ms end silence, hard 20s maximum. */
final class UtteranceAccumulator {
    static final int SAMPLE_RATE = 16000;
    static final int FRAME_SAMPLES = 320;
    static final int PRE_ROLL_FRAMES = 20;
    static final int END_SILENCE_FRAMES = 35;
    static final int MAX_FRAMES = 1000;
    static final int MIN_SPEECH_FRAMES = 3;
    static final int VOICE_THRESHOLD = 1200;
    private final ArrayDeque<short[]> preRoll = new ArrayDeque<>();
    private final ArrayList<short[]> captured = new ArrayList<>();
    private int high, quiet;
    private boolean active;

    boolean inSpeech() { return active; }

    /** Returns complete PCM utterance exactly once, or null. */
    short[] accept(short[] input, int count) {
        if (count <= 0 || count > FRAME_SAMPLES || count > input.length)
            throw new IllegalArgumentException("invalid PCM frame");
        short[] frame = new short[count];
        System.arraycopy(input, 0, frame, 0, count);
        long sum = 0;
        for (int i = 0; i < count; i++) sum += Math.abs((int) frame[i]);
        boolean loud = sum / count >= VOICE_THRESHOLD;
        if (!active) {
            preRoll.addLast(frame);
            if (preRoll.size() > PRE_ROLL_FRAMES) preRoll.removeFirst();
            high = loud ? high + 1 : 0;
            if (high >= MIN_SPEECH_FRAMES) {
                active = true;
                quiet = 0;
                captured.addAll(preRoll);
                preRoll.clear();
            }
            return null;
        }
        captured.add(frame);
        quiet = loud ? 0 : quiet + 1;
        if (quiet >= END_SILENCE_FRAMES || captured.size() >= MAX_FRAMES) {
            int length = 0;
            for (short[] part : captured) length += part.length;
            short[] all = new short[length];
            int offset = 0;
            for (short[] part : captured) {
                System.arraycopy(part, 0, all, offset, part.length);
                offset += part.length;
            }
            reset();
            return all;
        }
        return null;
    }

    void reset() {
        preRoll.clear();
        captured.clear();
        high = 0;
        quiet = 0;
        active = false;
    }
}
