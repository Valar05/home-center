package com.dclar.homecenter;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

public final class NarrationForegroundService extends Service {
    static final String ACTION_START = "com.dclar.homecenter.action.NARRATION_START";
    static final String ACTION_STOP = "com.dclar.homecenter.action.NARRATION_STOP";
    static final String EXTRA_TITLE = "title";
    private static final String CHANNEL_ID = "drive_narration_playback";
    private static final int NOTIFICATION_ID = 1042;
    private PowerManager.WakeLock wakeLock;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }
        String title = intent == null ? "Drive Narrate" : intent.getStringExtra(EXTRA_TITLE);
        startForeground(NOTIFICATION_ID, notification(firstNonEmpty(title, "Drive Narrate")));
        acquireWakeLock();
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        releaseWakeLock();
        super.onDestroy();
    }

    private Notification notification(String title) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && manager != null) {
            NotificationChannel channel = new NotificationChannel(CHANNEL_ID, "Drive Narrate", NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("Keeps Google Doc narration playing while Home Center is minimized.");
            manager.createNotificationChannel(channel);
        }
        Intent open = new Intent(this, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent contentIntent = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        return builder
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle("Drive Narrate is reading")
                .setContentText(title)
                .setContentIntent(contentIntent)
                .setOngoing(true)
                .setShowWhen(false)
                .build();
    }

    private void acquireWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) return;
        PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (powerManager == null) return;
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "HomeCenter:DriveNarrate");
        wakeLock.setReferenceCounted(false);
        wakeLock.acquire(6L * 60L * 60L * 1000L);
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        wakeLock = null;
    }

    private static String firstNonEmpty(String value, String fallback) {
        return value == null || value.trim().isEmpty() ? fallback : value.trim();
    }
}
