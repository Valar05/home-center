package com.homecenter.ritsucontrol;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.IBinder;

/**
 * Salvaged from the old operator overlay's notification/foreground pattern.
 * Stage A only persists local requests. It neither records a microphone nor
 * stops existing Termux playback. UI explicitly says that audio is unwired.
 */
public final class RitsuControlService extends Service {
    static final String ACTION_START = "com.homecenter.ritsucontrol.START";
    static final String ACTION_MIC_REQUEST = "com.homecenter.ritsucontrol.MIC_REQUEST";
    static final String ACTION_SPEAKER_PREFERENCE = "com.homecenter.ritsucontrol.SPEAKER_PREFERENCE";
    static final String ACTION_STOP = "com.homecenter.ritsucontrol.STOP";
    private static final String CHANNEL = "ritsu_control_notification";
    private static final int NOTIFICATION_ID = 19644;

    @Override public void onCreate() {
        super.onCreate();
        getSystemService(NotificationManager.class).createNotificationChannel(
                new NotificationChannel(CHANNEL, "Ritsu control", NotificationManager.IMPORTANCE_LOW));
        // On a new service lifetime, a prior mic request must never carry over.
        ControlStore.transition(this, ControlPolicy.ACTION_START);
        startForeground(NOTIFICATION_ID, notification(ControlStore.read(this)));
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_START : intent.getAction();
        int operation;
        if (ACTION_MIC_REQUEST.equals(action)) operation = ControlPolicy.ACTION_MIC_REQUEST;
        else if (ACTION_SPEAKER_PREFERENCE.equals(action)) operation = ControlPolicy.ACTION_SPEAKER_PREFERENCE;
        else if (ACTION_STOP.equals(action)) {
            ControlStore.transition(this, ControlPolicy.ACTION_STOP);
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
            return START_NOT_STICKY;
        } else if (ACTION_START.equals(action)) {
            // Ignore duplicate launches; onCreate already established fail-closed state.
            operation = -1;
        } else {
            // No untrusted arbitrary commands.
            return START_NOT_STICKY;
        }
        ControlPolicy.State state = operation < 0 ? ControlStore.read(this) : ControlStore.transition(this, operation);
        getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, notification(state));
        return START_NOT_STICKY;
    }

    private Notification notification(ControlPolicy.State state) {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent openIntent = PendingIntent.getActivity(this, 41, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        String mic = state.microphoneRequested ? "MIC REQUESTED" : "MIC OFF";
        String speaker = state.speakerMuted ? "OUTPUT MUTE REQUESTED" : "OUTPUT NORMAL REQUESTED";
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentTitle("Ritsu | Command Control")
                .setContentText(mic + " · " + speaker + " · Audio bridge NOT CONNECTED")
                .setStyle(new Notification.BigTextStyle().bigText(
                        mic + " · " + speaker + "\nThis is a control prototype: no microphone capture, no live output mute. Tap to inspect."))
                .setContentIntent(openIntent)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .addAction(new Notification.Action.Builder(null,
                        state.microphoneRequested ? "Cancel mic request" : "Request mic",
                        serviceAction(ACTION_MIC_REQUEST, 42)).build())
                .addAction(new Notification.Action.Builder(null,
                        state.speakerMuted ? "Unrequest mute" : "Request mute",
                        serviceAction(ACTION_SPEAKER_PREFERENCE, 43)).build())
                .addAction(new Notification.Action.Builder(null,
                        "Close", serviceAction(ACTION_STOP, 44)).build())
                .build();
    }

    private PendingIntent serviceAction(String action, int id) {
        Intent intent = new Intent(this, RitsuControlService.class).setAction(action);
        return PendingIntent.getService(this, id, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
