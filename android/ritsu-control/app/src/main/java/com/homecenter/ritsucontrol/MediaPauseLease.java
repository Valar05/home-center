package com.homecenter.ritsucontrol;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;

/** Cooperative Android media pause request when human speech is independently
 * verified. Requests transient focus, never adjusts global media volume.
 * Focus may be denied; another app might not pause. */
final class MediaPauseLease {
    private final AudioManager audio;
    private AudioFocusRequest request;
    private boolean held;
    private final AudioManager.OnAudioFocusChangeListener listener = change -> {};

    MediaPauseLease(Context ctx) {
        audio=(AudioManager)ctx.getSystemService(Context.AUDIO_SERVICE);
    }
    boolean otherAudioMayBeActive() {
        return audio != null && audio.isMusicActive();
    }
    boolean requestPauseForVerifiedSpeech() {
        if(held) return true;
        if(audio==null) return false;
        AudioAttributes attrs=new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANT)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build();
        request=new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                .setAudioAttributes(attrs).setOnAudioFocusChangeListener(listener).build();
        held=audio.requestAudioFocus(request)==AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
        if(!held)request=null;
        return held;
    }
    void release() {
        if(held && request!=null) audio.abandonAudioFocusRequest(request);
        held=false;
        request=null;
    }
}
