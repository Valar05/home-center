package com.homecenter.operatoroverlay;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;

public class MainActivity extends Activity {
    private static final int OVERLAY_REQUEST = 4107;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ensureOverlay();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (Settings.canDrawOverlays(this)) startOverlay();
    }

    private void ensureOverlay() {
        if (Settings.canDrawOverlays(this)) {
            startOverlay();
            return;
        }
        Intent intent = new Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName()));
        startActivityForResult(intent, OVERLAY_REQUEST);
    }

    private void startOverlay() {
        // Launcher/notification restore is intentionally local and fail-closed:
        // visibility returns, but control remains disabled until the user enables it.
        OperatorState.setControlEnabled(this, false);
        OperatorState.setOverlayHidden(this, false);
        Intent service = new Intent(this, OperatorOverlayService.class)
                .setAction(OperatorOverlayService.ACTION_RESTORE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(service);
        } else {
            startService(service);
        }
        finish();
    }
}
