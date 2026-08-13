package com.homecenter.fortresscockpit;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;

public final class FortressNotification {
    public static final String CHANNEL = "fortress-command-center";
    public static final int ID = 6701;

    private FortressNotification() {}

    private static PendingIntent action(Context c, String action, int requestCode) {
        Intent i = new Intent(c, FortressCommandReceiver.class).setAction(action);
        return PendingIntent.getBroadcast(c, requestCode, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    public static void post(Context context, String status) {
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        NotificationChannel ch = new NotificationChannel(CHANNEL, "Fortress Command Center", NotificationManager.IMPORTANCE_LOW);
        ch.setDescription("Persistent recovery controls for Fortress, SSH, and the Home Center relay");
        ch.setShowBadge(false);
        nm.createNotificationChannel(ch);

        Intent open = new Intent(context, MainActivity.class);
        PendingIntent openPi = PendingIntent.getActivity(context, 6700, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        String text = (status == null || status.trim().isEmpty())
                ? "SSH + relay recovery available without opening Termux"
                : status.trim();

        android.app.Notification.Builder b = new android.app.Notification.Builder(context, CHANNEL)
                .setSmallIcon(android.R.drawable.stat_sys_warning)
                .setContentTitle("Fortress Command Center")
                .setContentText(text)
                .setStyle(new android.app.Notification.BigTextStyle().bigText(text))
                .setContentIntent(openPi)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setColor(Color.DKGRAY)
                .setCategory(android.app.Notification.CATEGORY_SERVICE)
                .addAction(new android.app.Notification.Action.Builder(null, "SSH Repair", action(context, FortressCommandReceiver.ACTION_SSH, 6702)).build())
                .addAction(new android.app.Notification.Action.Builder(null, "Relay Repair", action(context, FortressCommandReceiver.ACTION_RELAY, 6703)).build())
                .addAction(new android.app.Notification.Action.Builder(null, "Fortress Status", action(context, FortressCommandReceiver.ACTION_STATUS, 6704)).build());
        nm.notify(ID, b.build());
    }
}
