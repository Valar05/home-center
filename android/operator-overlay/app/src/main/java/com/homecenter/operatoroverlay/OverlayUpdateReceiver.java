package com.homecenter.operatoroverlay;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public class OverlayUpdateReceiver extends BroadcastReceiver {
    private static final String TAG = "HomeCenterHeartbeat";
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
            HeartbeatIngressPolicy.Result result = HeartbeatIngressPolicy.apply(
                    heartbeatLightsJson,
                    new HeartbeatIngressPolicy.Sink() {
                        @Override
                        public void persistHeartbeatLights(String payloadJson) {
                            OperatorState.updateHeartbeatLights(context, payloadJson, now);
                        }

                        @Override
                        public void heartbeat() {
                            OperatorState.heartbeat(context, now);
                        }
                    });
            if (result.payloadPresent && !result.payloadAccepted && !result.boundary.isEmpty()) {
                Log.w(TAG, result.boundary);
            }
        }
    }
}
