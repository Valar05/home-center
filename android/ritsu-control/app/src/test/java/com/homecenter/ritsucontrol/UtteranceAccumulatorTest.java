package com.homecenter.ritsucontrol;

import static org.junit.Assert.*;
import org.junit.Test;

public final class UtteranceAccumulatorTest {
    private static short[] frame(int amplitude) {
        short[] s=new short[320];
        for(int i=0;i<s.length;i++)s[i]=(short)(i%2==0?amplitude:-amplitude);
        return s;
    }
    @Test public void onlySilenceCannotStartOrSubmitUtterance() {
        UtteranceAccumulator gate=new UtteranceAccumulator();
        for(int i=0;i<400;i++){
            assertNull(gate.accept(frame(0),320));
            assertFalse(gate.inSpeech());
        }
    }
    @Test public void waitsForEnoughSpeechThenSilenceBeforeOneResult() {
        UtteranceAccumulator gate=new UtteranceAccumulator();
        for(int i=0;i<16;i++)assertNull(gate.accept(frame(0),320));
        for(int i=0;i<2;i++)assertNull(gate.accept(frame(2000),320));
        assertFalse(gate.inSpeech());
        assertNull(gate.accept(frame(2000),320));
        assertTrue(gate.inSpeech());
        for(int i=0;i<34;i++)assertNull(gate.accept(frame(0),320));
        short[] audio=gate.accept(frame(0),320);
        assertNotNull(audio);
        assertTrue(audio.length>=320*(16+3+35));
        assertFalse(gate.inSpeech());
        assertNull(gate.accept(frame(0),320));
    }
    @Test public void hardCapCompletesEvenWithUninterruptedSpeech() {
        UtteranceAccumulator gate=new UtteranceAccumulator();
        short[] audio=null;
        for(int i=0;i<1200;i++){
            audio=gate.accept(frame(2200),320);
            if(audio!=null)break;
        }
        assertNotNull(audio);
        assertTrue(audio.length<=UtteranceAccumulator.MAX_FRAMES*320);
    }
    @Test(expected=IllegalArgumentException.class)
    public void invalidLengthFailsClosed() {
        new UtteranceAccumulator().accept(new short[320],321);
    }
    @Test public void oldUnsubmittedAudioIsDiscardedOnReset() {
        UtteranceAccumulator gate=new UtteranceAccumulator();
        for(int i=0;i<4;i++)gate.accept(frame(2200),320);
        gate.reset();
        assertFalse(gate.inSpeech());
        for(int i=0;i<40;i++)assertNull(gate.accept(frame(0),320));
    }
}
