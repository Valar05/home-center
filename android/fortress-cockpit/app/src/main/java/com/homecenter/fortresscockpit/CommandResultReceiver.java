package com.homecenter.fortresscockpit;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;

public final class CommandResultReceiver extends BroadcastReceiver {
    public interface Listener { void onCommandResult(int requestId, String stdout, String stderr, int exitCode, String error); }
    private static volatile Listener listener;

    public static void setListener(Listener value) { listener = value; }

    @Override public void onReceive(Context context, Intent intent) {
        int requestId = intent.getIntExtra("request_id", -1);
        Bundle result = intent.getBundleExtra("result");
        Listener target = listener;
        if (target == null) return;
        if (result == null) {
            target.onCommandResult(requestId, "", "", -1, "Termux returned no result bundle");
            return;
        }
        target.onCommandResult(
            requestId,
            result.getString("stdout", ""),
            result.getString("stderr", ""),
            result.getInt("exitCode", -1),
            result.getString("errmsg", "")
        );
    }
}
