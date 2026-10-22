package com.homecenter.ritsucontrol;

import android.Manifest;
import android.app.Activity;
import android.app.StatusBarManager;
import android.content.Intent;
import android.content.ComponentName;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.graphics.drawable.Icon;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Clear, accessible activity. Does not claim or acquire microphone access. */
public final class MainActivity extends Activity {
    private static final int NOTIFICATION_PERMISSION_REQUEST = 19644;
    private TextView status;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(20), dp(24), dp(20), dp(24));
        TextView title = new TextView(this);
        title.setText("Ritsu Command Control");
        title.setTextSize(24);
        title.setContentDescription("Ritsu command control prototype");
        layout.addView(title);
        status = new TextView(this);
        status.setTextSize(17);
        status.setPadding(0, dp(18), 0, dp(18));
        layout.addView(status);

        button(layout, "Show compact notification", "Show Ritsu compact controls; Android may still allow swipe dismissal",
                v -> startPanel());
        button(layout, "Pin Ritsu in Quick Settings", "Add a lasting Ritsu tile to Quick Settings",
                v -> addQuickTile());
        button(layout, "Request microphone mode", "Toggle requested microphone mode; recording is not implemented",
                v -> send(RitsuControlService.ACTION_MIC_REQUEST));
        button(layout, "Request speaker mute", "Toggle requested output mute; live audio is not connected",
                v -> send(RitsuControlService.ACTION_SPEAKER_PREFERENCE));
        button(layout, "Close controls", "Stop Ritsu's local notification controls",
                v -> send(RitsuControlService.ACTION_STOP));
        button(layout, "Refresh state", "Read saved requested microphone and speaker state",
                v -> refresh());

        TextView warning = new TextView(this);
        warning.setPadding(0, dp(24), 0, 0);
        warning.setText("Stage A control prototype. Android 14+ allows swiping away ongoing notifications. Pin the Ritsu Quick Settings tile to reopen controls at any time. Mic and mute requests are NOT connected to real audio. The old operator overlay remains retired.");
        warning.setTextSize(15);
        layout.addView(warning);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(layout);
        setContentView(scroll);
        refresh();
    }

    private void addQuickTile() {
        if (Build.VERSION.SDK_INT < 33) {
            status.setText("Open Quick Settings, choose Edit, and drag Ritsu controls into the active tiles.");
            return;
        }
        StatusBarManager manager = getSystemService(StatusBarManager.class);
        if (manager == null) {
            status.setText("Quick Settings installer unavailable. Add Ritsu manually from Quick Settings > Edit.");
            return;
        }
        manager.requestAddTileService(
                new ComponentName(this, RitsuQuickTileService.class),
                "Ritsu controls",
                Icon.createWithResource(this, android.R.drawable.ic_btn_speak_now),
                getMainExecutor(),
                result -> {
                    refresh();
                    status.append("\\nTile request returned " + result
                            + ". If Ritsu isn't visible, add it from Quick Settings > Edit.");
                });
    }

    private void startPanel() {
        if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, NOTIFICATION_PERMISSION_REQUEST);
            return;
        }
        send(RitsuControlService.ACTION_START);
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != NOTIFICATION_PERMISSION_REQUEST) return;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            send(RitsuControlService.ACTION_START);
        } else {
            status.setText("Notification permission denied. Controls were not started.");
        }
    }

    private void send(String action) {
        Intent intent = new Intent(this, RitsuControlService.class).setAction(action);
        try {
            // User-initiated from visible activity; never start the service at boot.
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent);
            else startService(intent);
            refresh();
        } catch (RuntimeException error) {
            status.setText("Service request blocked: " + error.getClass().getSimpleName());
        }
    }

    private void refresh() {
        ControlPolicy.State state = ControlStore.read(this);
        status.setText(
                "Microphone: " + (state.microphoneRequested ? "requested, NOT recording" : "OFF") +
                "\nSpeaker: " + (state.speakerMuted ? "mute requested, NOT applied" : "normal requested") +
                "\nAudio bridge: NOT CONNECTED");
    }

    private void button(LinearLayout layout, String label, String description, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setContentDescription(description);
        button.setMinHeight(dp(48)); // salvaged from OverlayUiPolicy.MIN_TOUCH_TARGET_DP
        button.setOnClickListener(listener);
        layout.addView(button);
    }
    private int dp(int d) { return Math.round(d * getResources().getDisplayMetrics().density); }
}
