package com.homecenter.ritsucontrol;

import android.Manifest;
import android.app.AlertDialog;
import android.app.Activity;
import android.app.StatusBarManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/** User-visible gate for Android 14+ microphone foreground service.
 * Bubble permission and RECORD_AUDIO permission are separate opt-ins.
 * No audio leaves the device at this stage. */
public final class MainActivity extends Activity {
    private static final int NOTIFICATION_PERMISSION_REQUEST = 19644;
    private static final int MIC_PERMISSION_REQUEST = 19645;
    private static final int OVERLAY_PERMISSION_REQUEST = 19646;
    private TextView status;
    private EditText transcriptEditor;
    private SpellingSuggestions spellchecker;
    private boolean pendingBubbleEnable;
    private boolean pendingRecognizeOnce;
    private long observedTranscriptRevision = 0;
    private long observedPartialRevision = 0;
    private final Handler displayHandler = new Handler(Looper.getMainLooper());
    private final Runnable liveRefresh = new Runnable() {
        @Override public void run() {
            if (status == null || transcriptEditor == null) return;
            refresh();
            displayHandler.postDelayed(this, 300);
        }
    };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(20), dp(24), dp(20), dp(24));
        TextView title = new TextView(this);
        title.setText("Ritsu | Listening control");
        title.setTextSize(22);
        layout.addView(title);
        status = new TextView(this);
        status.setTextSize(16);
        status.setPadding(0, dp(14), 0, dp(14));
        layout.addView(status);
        spellchecker = new SpellingSuggestions(this);
        transcriptEditor = new EditText(this);
        transcriptEditor.setHint("Optional transcript or Gboard dictation");
        transcriptEditor.setTextSize(17);
        transcriptEditor.setMinLines(2);
        transcriptEditor.setInputType(InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_FLAG_MULTI_LINE |
                InputType.TYPE_TEXT_FLAG_CAP_SENTENCES |
                InputType.TYPE_TEXT_FLAG_AUTO_CORRECT);
        transcriptEditor.setContentDescription("Editable transcript using your normal Gboard keyboard and suggestions");
        layout.addView(transcriptEditor);
        button(layout, "Talk to Google recognizer (one phrase)",
                "One tap starts permitted microphone capture and Google's system recognition, then shows the words automatically",
                v -> requestRecognition());
        button(layout, "Reload transcript", "Copy the latest recognized words into the editable Gboard text field",
                v -> {
                    transcriptEditor.setText(RitsuControlService.lastTranscript);
                    transcriptEditor.setSelection(transcriptEditor.length());
                });
        button(layout, "See Android spelling suggestions",
                "Show suggestions from the active Android system spellchecker without automatically rewriting words",
                v -> checkSpellings());

        button(layout, "Start local listening", "Grant microphone permission and start local voice activity detection",
                v -> requestListening());
        button(layout, "Mute microphone", "Physically stop microphone capture while keeping the session ready",
                v -> send(RitsuControlService.ACTION_MUTE));
        button(layout, "Resume microphone", "Restart local microphone capture in the active muted session",
                v -> send(RitsuControlService.ACTION_RESUME));
        button(layout, "Enable floating Ritsu bubble", "Grant display over other apps permission and show draggable mic mute bubble",
                v -> enableBubble());
        button(layout, "Hide floating bubble", "Remove floating bubble without changing microphone state",
                v -> send(RitsuControlService.ACTION_HIDE_BUBBLE));
        button(layout, "Show compact notification", "Open notification controls",
                v -> startNotification());
        button(layout, "Pin Ritsu Quick Settings tile", "Install a tile that can reopen Ritsu after the bubble is hidden",
                v -> addQuickTile());
        button(layout, "Stop entire session", "Stop microphone and release bubble and foreground notification",
                v -> send(RitsuControlService.ACTION_STOP));
        button(layout, "Refresh live status", "Read the in-process microphone hardware state",
                v -> refresh());

        TextView warning = new TextView(this);
        warning.setText("SPEECH RECOGNITION TEST ONLY. Tap Talk to Google recognizer and say one phrase. Results automatically appear above or a provider error appears in live status. The system provider MAY use cloud processing. This app cannot yet send words to ChatGPT or speak back in Ritsu's voice. Gboard editing and optional overlay remain available.");
        warning.setTextSize(14);
        warning.setPadding(0, dp(20), 0, dp(12));
        layout.addView(warning);

        ScrollView scrolling = new ScrollView(this);
        scrolling.addView(layout);
        setContentView(scrolling);
        refresh();
    }

    @Override public void onResume() {
        super.onResume();
        if (pendingBubbleEnable && Settings.canDrawOverlays(this)) {
            pendingBubbleEnable = false;
            send(RitsuControlService.ACTION_SHOW_BUBBLE);
        }
        if (status != null) refresh();
        displayHandler.removeCallbacks(liveRefresh);
        displayHandler.postDelayed(liveRefresh, 300);
    }

    @Override protected void onPause() {
        displayHandler.removeCallbacks(liveRefresh);
        super.onPause();
    }

    private void requestRecognition() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            pendingRecognizeOnce = true;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_PERMISSION_REQUEST);
            return;
        }
        pendingRecognizeOnce = false;
        send(RitsuControlService.ACTION_SPEAK_ONCE);
    }

    private void requestListening() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_PERMISSION_REQUEST);
            return;
        }
        // This call comes only from the visible Activity, never boot/background.
        send(RitsuControlService.ACTION_LISTEN);
    }

    private void checkSpellings() {
        if (spellchecker == null) return;
        String current = transcriptEditor.getText().toString();
        spellchecker.check(current, (source, choices) -> runOnUiThread(() -> {
            if (isFinishing() || isDestroyed()) return;
            if (!source.equals(transcriptEditor.getText().toString())) return;
            if (choices.length == 0) {
                Toast.makeText(this, "No system spelling suggestions available", Toast.LENGTH_LONG).show();
                return;
            }
            new AlertDialog.Builder(this)
                    .setTitle("Suggested corrections (not Gboard private data)")
                    .setItems(choices, (dialog, which) -> {
                        transcriptEditor.setText(choices[which]);
                        transcriptEditor.setSelection(transcriptEditor.length());
                    })
                    .setNegativeButton("Keep original", (dialog, which) -> dialog.dismiss())
                    .show();
        }));
    }

    @Override protected void onDestroy() {
        displayHandler.removeCallbacks(liveRefresh);
        if (spellchecker != null) spellchecker.close();
        super.onDestroy();
    }

    private void enableBubble() {
        if (!Settings.canDrawOverlays(this)) {
            pendingBubbleEnable = true;
            try {
                Intent permission = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:" + getPackageName()));
                startActivityForResult(permission, OVERLAY_PERMISSION_REQUEST);
            } catch (RuntimeException blocked) {
                pendingBubbleEnable = false;
                status.setText("Overlay settings unavailable; cannot show floating bubble.");
            }
            return;
        }
        send(RitsuControlService.ACTION_SHOW_BUBBLE);
    }

    private void startNotification() {
        if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    NOTIFICATION_PERMISSION_REQUEST);
        } else send(RitsuControlService.ACTION_START);
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(requestCode, permissions, grants);
        boolean allowed = grants.length > 0 && grants[0] == PackageManager.PERMISSION_GRANTED;
        if (requestCode == MIC_PERMISSION_REQUEST) {
            boolean recognize = pendingRecognizeOnce;
            pendingRecognizeOnce = false;
            if (allowed) send(recognize ? RitsuControlService.ACTION_SPEAK_ONCE
                    : RitsuControlService.ACTION_LISTEN);
            else status.setText("Microphone permission denied. Speech was NOT captured.");
        } else if (requestCode == NOTIFICATION_PERMISSION_REQUEST) {
            if (allowed) send(RitsuControlService.ACTION_START);
            else status.setText("Notification permission denied. Use Quick Settings or Ritsu app to reopen.");
        }
    }

    private void addQuickTile() {
        if (Build.VERSION.SDK_INT < 33) {
            status.setText("Open Quick Settings > Edit and drag Ritsu into the active tiles.");
            return;
        }
        StatusBarManager manager = getSystemService(StatusBarManager.class);
        if (manager == null) {
            status.setText("Add Ritsu manually via Quick Settings > Edit.");
            return;
        }
        manager.requestAddTileService(
                new ComponentName(this, RitsuQuickTileService.class),
                "Ritsu controls",
                Icon.createWithResource(this, android.R.drawable.ic_btn_speak_now),
                getMainExecutor(),
                result -> status.append("\nQuick Settings result: " + result));
    }

    private void send(String action) {
        try {
            Intent intent = new Intent(this, RitsuControlService.class).setAction(action);
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent);
            else startService(intent);
            refresh();
        } catch (RuntimeException error) {
            status.setText("Ritsu service request failed: " + error.getClass().getSimpleName());
        }
    }

    private void refresh() {
        long partial = RitsuControlService.partialRevision;
        if (partial != observedPartialRevision
                && RitsuControlService.liveMode == ListeningPolicy.Mode.RECOGNIZING) {
            observedPartialRevision = partial;
            transcriptEditor.setText(RitsuControlService.partialTranscript);
            transcriptEditor.setSelection(transcriptEditor.length());
        }
        long latest = RitsuControlService.transcriptRevision;
        if (latest != observedTranscriptRevision) {
            observedTranscriptRevision = latest;
            transcriptEditor.setText(RitsuControlService.lastTranscript);
            transcriptEditor.setSelection(transcriptEditor.length());
        }
        ListeningPolicy.Mode mode = RitsuControlService.liveMode;
        String microphone = mode == ListeningPolicy.Mode.LISTENING ? "ACTIVE: local energy detector"
                : mode == ListeningPolicy.Mode.RECOGNIZING ? "SYSTEM ASR: provider may be capturing"
                : mode == ListeningPolicy.Mode.MUTED ? "MUTED: audio capture released"
                : mode == ListeningPolicy.Mode.ERROR ? "ERROR" : "OFF";
        status.setText("Microphone: " + microphone
                + "\nLocal speech activity: " +
                    (mode == ListeningPolicy.Mode.LISTENING && RitsuControlService.voiceActivity
                        ? "Detected" : "No active speech")
                + "\nSpeech recognition: " + RitsuControlService.recognitionStatus
                + "\nInterim recognized text: " + RitsuControlService.partialTranscript
                + "\nLatest transcript (not sent): " + RitsuControlService.lastTranscript
                + "\nChatGPT turn submission: NOT CONNECTED"
                + "\nLast error: " + (RitsuControlService.lastProblem.isEmpty() ? "none" :
                    RitsuControlService.lastProblem)
                + "\nFloating overlay permission: " + (Settings.canDrawOverlays(this) ? "granted" : "not granted"));
    }

    private void button(LinearLayout layout, String title, String accessibility, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(title);
        button.setAllCaps(false);
        button.setContentDescription(accessibility);
        button.setMinHeight(dp(48));
        button.setOnClickListener(listener);
        layout.addView(button);
    }
    private int dp(int dp) { return Math.round(dp * getResources().getDisplayMetrics().density); }
}
