package com.homecenter.operatoroverlay;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * App-private restore endpoint used only by the immutable notification
 * PendingIntent and the launcher's explicit local confirmation.
 */
public final class LocalRestoreReceiver extends BroadcastReceiver {
    private static final String ACTION_LOCAL_RESTORE =
            "com.homecenter.operatoroverlay.LOCAL_RESTORE";
    private static final int REQUEST_CODE = 4110;

    static PendingIntent notificationRestoreIntent(Context context) {
        Intent localRestore = new Intent(context, LocalRestoreReceiver.class)
                .setAction(ACTION_LOCAL_RESTORE)
                .setPackage(context.getPackageName());
        return PendingIntent.getBroadcast(
                context,
                REQUEST_CODE,
                localRestore,
                PendingIntent.FLAG_CANCEL_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    static void restoreFromLocalConfirmation(Context context) {
        OperatorState.setControlEnabled(context, false);
        OperatorState.clearScreenActivity(context);
        OperatorState.setOverlayHidden(
                context,
                OverlayUiPolicy.nextHidden(
                        true,
                        OverlayUiPolicy.VisibilityAction.RESTORE));

        Intent service = new Intent(context, OperatorOverlayService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(service);
        } else {
            context.startService(service);
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !ACTION_LOCAL_RESTORE.equals(intent.getAction())) return;
        restoreFromLocalConfirmation(context);
    }
}
