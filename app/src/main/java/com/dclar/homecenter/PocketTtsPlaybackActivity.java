package com.dclar.homecenter;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.SystemClock;
import android.util.Log;

import java.io.File;
import java.io.IOException;

public final class PocketTtsPlaybackActivity extends Activity {
    public static final String EXTRA_FILE = "file";
    private static final String TAG = "PocketTtsDuck";
    private AudioManager audioManager;
    private AudioFocusRequest focusRequest;
    private MediaPlayer player;
    private MediaSession mediaSession;
    private boolean focusHeld;
    private boolean prepared;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        playFromIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        cleanup("superseded");
        playFromIntent(intent);
    }

    private void createMediaSession() {
        mediaSession = new MediaSession(this, "PocketTtsPlayback");
        mediaSession.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
        mediaSession.setCallback(new MediaSession.Callback() {
            @Override
            public void onPlay() {
                if (player != null && prepared && !player.isPlaying()) {
                    player.start();
                    updatePlaybackState(PlaybackState.STATE_PLAYING);
                    Log.i(TAG, "media_control=play");
                }
            }

            @Override
            public void onPause() {
                if (player != null && prepared && player.isPlaying()) {
                    player.pause();
                    updatePlaybackState(PlaybackState.STATE_PAUSED);
                    Log.i(TAG, "media_control=pause");
                }
            }

            @Override
            public void onStop() {
                Log.i(TAG, "media_control=stop");
                cleanupAndFinish("media_stop");
            }
        });
        mediaSession.setActive(true);
        updatePlaybackState(PlaybackState.STATE_CONNECTING);
    }

    private void updatePlaybackState(int state) {
        if (mediaSession == null) return;
        long position = 0L;
        if (player != null && prepared) {
            try { position = player.getCurrentPosition(); } catch (Exception ignored) { }
        }
        PlaybackState playbackState = new PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY | PlaybackState.ACTION_PAUSE | PlaybackState.ACTION_PLAY_PAUSE | PlaybackState.ACTION_STOP)
                .setState(state, position, state == PlaybackState.STATE_PLAYING ? 1.0f : 0.0f, SystemClock.elapsedRealtime())
                .build();
        mediaSession.setPlaybackState(playbackState);
    }

    private void playFromIntent(Intent intent) {
        String supplied = intent == null ? "" : intent.getStringExtra(EXTRA_FILE);
        try {
            File root = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS), "FortressAudio").getCanonicalFile();
            File wav = new File(supplied == null ? "" : supplied).getCanonicalFile();
            if (!wav.getPath().startsWith(root.getPath() + File.separator) || !wav.getName().toLowerCase().endsWith(".wav")) {
                throw new IOException("PocketTTS path must be a WAV beneath Documents/FortressAudio");
            }
            if (!wav.isFile() || wav.length() <= 44L) {
                throw new IOException("PocketTTS WAV missing or empty");
            }
            if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.READ_MEDIA_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                throw new IOException("READ_MEDIA_AUDIO is not granted");
            }

            audioManager = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
            AudioAttributes attributes = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build();
            focusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                    .setAudioAttributes(attributes)
                    .setAcceptsDelayedFocusGain(false)
                    .setWillPauseWhenDucked(false)
                    .setOnAudioFocusChangeListener(change -> Log.i(TAG, "focus_change=" + change))
                    .build();
            focusHeld = audioManager.requestAudioFocus(focusRequest) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
            if (!focusHeld) {
                throw new IOException("transient ducking audio focus denied");
            }

            createMediaSession();
            prepared = false;
            player = new MediaPlayer();
            player.setAudioAttributes(attributes);
            player.setDataSource(wav.getAbsolutePath());
            player.setOnPreparedListener(mp -> {
                prepared = true;
                Log.i(TAG, "play_start file=" + wav.getAbsolutePath() + " bytes=" + wav.length());
                mp.start();
                updatePlaybackState(PlaybackState.STATE_PLAYING);
            });
            player.setOnCompletionListener(mp -> {
                updatePlaybackState(PlaybackState.STATE_STOPPED);
                cleanupAndFinish("completed");
            });
            player.setOnErrorListener((mp, what, extra) -> {
                Log.e(TAG, "play_error what=" + what + " extra=" + extra);
                updatePlaybackState(PlaybackState.STATE_ERROR);
                cleanupAndFinish("error");
                return true;
            });
            player.prepareAsync();
        } catch (Exception error) {
            Log.e(TAG, "play_rejected " + error.getMessage());
            cleanupAndFinish("rejected");
        }
    }

    private void cleanupAndFinish(String reason) {
        cleanup(reason);
        finishAndRemoveTask();
    }

    private void cleanup(String reason) {
        prepared = false;
        if (player != null) {
            try { player.stop(); } catch (Exception ignored) { }
            player.release();
            player = null;
        }
        if (mediaSession != null) {
            try {
                updatePlaybackState(PlaybackState.STATE_STOPPED);
                mediaSession.setActive(false);
                mediaSession.release();
            } catch (Exception ignored) { }
            mediaSession = null;
        }
        if (focusHeld && audioManager != null && focusRequest != null) {
            audioManager.abandonAudioFocusRequest(focusRequest);
        }
        focusHeld = false;
        Log.i(TAG, "play_finish reason=" + reason + " focus_abandoned=true");
    }

    @Override
    protected void onDestroy() {
        cleanup("destroyed");
        super.onDestroy();
    }
}
