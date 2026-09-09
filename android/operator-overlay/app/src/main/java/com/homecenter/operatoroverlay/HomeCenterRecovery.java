package com.homecenter.operatoroverlay;

import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;

/** Bounded recovery owned by the overlay: the operator never transports shell commands. */
public final class HomeCenterRecovery {
    public static final String ACTION_RECOVER = "com.homecenter.operatoroverlay.RECOVER_HOME_CENTER";
    private static final long VERIFY_DELAY_MS = 2500L;
    private HomeCenterRecovery() {}

    public static void request(Context context) {
        long requestedAt = System.currentTimeMillis();
        OperatorState.updateLatestText(context,
                "Recovery requested • Home Center", requestedAt);

        // Existing receiver/service implementations can bind this stable action to the
        // proven local recovery body. The overlay owns request + verification UX.
        Intent recover = new Intent(ACTION_RECOVER);
        recover.setPackage(context.getPackageName());
        recover.putExtra("requestedAt", requestedAt);
        context.sendBroadcast(recover);

        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            long now = System.currentTimeMillis();
            long age = now - OperatorState.lastHeartbeatMs(context);
            boolean online = OperatorState.controlEnabled(context)
                    && age >= 0L && age <= 30000L;
            OperatorState.updateLatestText(context,
                    online ? "Recovery verified • Home Center online"
                           : "Recovery attempted • still offline",
                    now);
        }, VERIFY_DELAY_MS);
    }
}
