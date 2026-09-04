package com.homecenter.operatoroverlay;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class OverlayUpdateReceiver extends BroadcastReceiver {
    public static final String ACTION_UPDATE = "com.homecenter.operatoroverlay.UPDATE";
    // Legacy worker heartbeat remains accepted as a no-op so older local workers do not
    // falsely mark Home Center online merely because the overlay/worker process is alive.
    public static final String ACTION_HEARTBEAT = "com.homecenter.operatoroverlay.HEARTBEAT";
    public static final String ACTION_HOME_CENTER_HEARTBEAT = "com.homecenter.operatoroverlay.HOME_CENTER_HEARTBEAT";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) return;
        long now = System.currentTimeMillis();
        if (ACTION_UPDATE.equals(intent.getAction())) {
            String text = intent.getStringExtra("latestText");
            String source = intent.getStringExtra("source");
            OperatorState.updateText(context, source, text, now);
        } else if (ACTION_HOME_CENTER_HEARTBEAT.equals(intent.getAction())) {
            OperatorState.heartbeat(context, now);
        } else if (ACTION_HEARTBEAT.equals(intent.getAction())) {
            // Deliberately no-op: process/worker liveness is not Home Center relay liveness.
        }
    }
}
