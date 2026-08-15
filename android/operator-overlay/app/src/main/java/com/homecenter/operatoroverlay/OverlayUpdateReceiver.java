package com.homecenter.operatoroverlay;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class OverlayUpdateReceiver extends BroadcastReceiver {
    public static final String ACTION_UPDATE = "com.homecenter.operatoroverlay.UPDATE";
    public static final String ACTION_HEARTBEAT = "com.homecenter.operatoroverlay.HEARTBEAT";
    public static final String EXTRA_HEARTBEAT_LIGHTS_JSON = "heartbeatLightsJson";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) return;
        long now = System.currentTimeMillis();
        if (ACTION_UPDATE.equals(intent.getAction())) {
            String text = intent.getStringExtra("latestText");
            String source = intent.getStringExtra("source");
            OperatorState.updateText(context, source, text, now);
        } else if (ACTION_HEARTBEAT.equals(intent.getAction())) {
            String heartbeatLightsJson = intent.getStringExtra(EXTRA_HEARTBEAT_LIGHTS_JSON);
            if (heartbeatLightsJson != null && !heartbeatLightsJson.trim().isEmpty()) {
                OperatorState.updateHeartbeatLights(context, heartbeatLightsJson, now);
            }
            OperatorState.heartbeat(context, now);
        }
    }
}
