package com.homecenter.ritsucontrol;

import android.content.Context;
import android.content.SharedPreferences;

/** Local-only durable requested state. Audio transports are NOT wired in Stage A. */
final class ControlStore {
    private static final String PREFS = "ritsu_control_v1";
    private static final String MIC_REQUESTED = "mic_requested";
    private static final String SPEAKER_MUTED = "speaker_muted";

    static synchronized ControlPolicy.State read(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        return new ControlPolicy.State(
                prefs.getBoolean(MIC_REQUESTED, false),
                prefs.getBoolean(SPEAKER_MUTED, false));
    }

    static synchronized ControlPolicy.State transition(Context context, int action) {
        ControlPolicy.State after = ControlPolicy.transition(read(context), action);
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        boolean stored = prefs.edit()
                .putBoolean(MIC_REQUESTED, after.microphoneRequested)
                .putBoolean(SPEAKER_MUTED, after.speakerMuted)
                .commit();
        if (!stored) throw new IllegalStateException("Ritsu control state could not be persisted");
        return after;
    }
    private ControlStore() {}
}
