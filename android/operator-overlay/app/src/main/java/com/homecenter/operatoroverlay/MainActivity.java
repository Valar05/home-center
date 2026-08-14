package com.homecenter.operatoroverlay;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * Exported only as the launcher entry. Merely opening this Activity never
 * changes overlay visibility, control, or capture state.
 */
public class MainActivity extends Activity {
    private static final int OVERLAY_REQUEST = 4107;
    private static final int CAPTURE_REQUEST = 4108;

    private TextView status;
    private Button overlayPermissionButton;
    private Button restoreButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildLocalControls());
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshLocalControls();
    }

    private View buildLocalControls() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(dp(24), dp(32), dp(24), dp(32));

        TextView title = new TextView(this);
        title.setText("Home Center Operator");
        title.setTextSize(24f);
        title.setTextColor(Color.rgb(22, 24, 29));
        title.setGravity(Gravity.CENTER);
        root.addView(title, matchWidth());

        status = new TextView(this);
        status.setTextSize(16f);
        status.setTextColor(Color.rgb(50, 55, 65));
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, dp(12), 0, dp(20));
        root.addView(status, matchWidth());

        overlayPermissionButton = localButton("Grant overlay access");
        overlayPermissionButton.setContentDescription(
                "Open Android settings to grant Home Center Operator overlay access");
        overlayPermissionButton.setOnClickListener(v -> requestOverlayPermission());
        root.addView(overlayPermissionButton, matchWidth());

        restoreButton = localButton("Restore overlay");
        restoreButton.setContentDescription(
                "Locally restore the Home Center overlay with remote control off");
        restoreButton.setOnClickListener(v -> confirmLocalRestore());
        root.addView(restoreButton, matchWidth());

        Button captureButton = localButton("Start screen and audio capture");
        captureButton.setContentDescription(
                "Open Android's screen capture confirmation; capture never starts automatically");
        captureButton.setOnClickListener(v -> requestCapture());
        root.addView(captureButton, matchWidth());

        return root;
    }

    private void refreshLocalControls() {
        boolean overlayAllowed = Settings.canDrawOverlays(this);
        boolean hidden = OperatorState.overlayHidden(this);
        status.setText(overlayAllowed
                ? hidden
                        ? "Overlay hidden. Local restore keeps remote control off."
                        : "Overlay visible. Remote control state is unchanged."
                : "Overlay access is not granted.");
        overlayPermissionButton.setVisibility(overlayAllowed ? View.GONE : View.VISIBLE);
        restoreButton.setEnabled(overlayAllowed);
    }

    private void requestOverlayPermission() {
        Intent settings = new Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName()));
        startActivityForResult(settings, OVERLAY_REQUEST);
    }

    private void confirmLocalRestore() {
        if (!Settings.canDrawOverlays(this)) {
            refreshLocalControls();
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Restore Home Center overlay?")
                .setMessage("The overlay will become visible. Remote control will remain off.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Restore", (dialog, which) -> {
                    LocalRestoreReceiver.restoreFromLocalConfirmation(this);
                    refreshLocalControls();
                })
                .show();
    }

    private void requestCapture() {
        MediaProjectionManager manager =
                (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
        startActivityForResult(manager.createScreenCaptureIntent(), CAPTURE_REQUEST);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == OVERLAY_REQUEST) {
            refreshLocalControls();
            return;
        }
        if (requestCode != CAPTURE_REQUEST || resultCode != RESULT_OK || data == null) return;

        Intent capture = new Intent(this, VeniceAudioCaptureService.class)
                .putExtra(VeniceAudioCaptureService.EXTRA_RESULT_CODE, resultCode)
                .putExtra(VeniceAudioCaptureService.EXTRA_RESULT_DATA, data);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(capture);
        } else {
            startService(capture);
        }
    }

    private Button localButton(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setMinHeight(dp(48));
        button.setMinimumHeight(dp(48));
        return button;
    }

    private LinearLayout.LayoutParams matchWidth() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, dp(6), 0, dp(6));
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
