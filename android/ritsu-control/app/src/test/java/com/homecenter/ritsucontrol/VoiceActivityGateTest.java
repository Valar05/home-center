package com.homecenter.ritsucontrol;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import org.junit.Test;

public final class VoiceActivityGateTest {
    private static short[] frame(int amplitude) {
        short[] out = new short[VoiceActivityGate.FRAME_SAMPLES];
        for (int i=0; i<out.length; i++) out[i] = (short)(i%2 == 0 ? amplitude : -amplitude);
        return out;
    }
    @Test public void silenceNeverStartsSpeech() {
        VoiceActivityGate gate = new VoiceActivityGate();
        for (int i=0;i<100;i++) assertFalse(gate.accept(frame(0), VoiceActivityGate.FRAME_SAMPLES));
    }
    @Test public void threeLoudFramesStartOneSpeechWindow() {
        VoiceActivityGate gate = new VoiceActivityGate();
        assertFalse(gate.accept(frame(1600), 320));
        assertFalse(gate.accept(frame(1600), 320));
        assertTrue(gate.accept(frame(1600), 320));
        assertTrue(gate.accept(frame(1600), 320));
    }
    @Test public void hangoverAvoidsRapidSpeechJitter() {
        VoiceActivityGate gate = new VoiceActivityGate();
        for (int i=0;i<3;i++) gate.accept(frame(2000),320);
        for (int i=0;i<VoiceActivityGate.END_FRAMES-1;i++)
            assertTrue(gate.accept(frame(0),320));
        assertFalse(gate.accept(frame(0),320));
        assertFalse(gate.isSpeaking());
    }
    @Test public void belowThresholdEnergyDoesNotArm() {
        VoiceActivityGate gate = new VoiceActivityGate();
        for (int i=0;i<10;i++) assertFalse(gate.accept(frame(400),320));
    }
    @Test(expected=IllegalArgumentException.class)
    public void malformedFrameIsRejected() {
        new VoiceActivityGate().accept(frame(0), 500);
    }
}
