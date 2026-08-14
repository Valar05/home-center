package com.homecenter.operatoroverlay;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.text.TextUtils;
import android.text.method.ScrollingMovementMethod;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.WindowMetrics;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONObject;

public class OperatorOverlayService extends Service {
    public static final String ACTION_SCREEN_ACTIVITY = "com.homecenter.operatoroverlay.SCREEN_ACTIVITY";
    public static final String ACTION_RESTORE = "com.homecenter.operatoroverlay.RESTORE";
    public static final String ACTION_SPOTIFY_COMMAND = "com.homecenter.operatoroverlay.SPOTIFY_COMMAND";
    public static final String EXTRA_SPOTIFY_COMMAND = "spotify_command";
    public static final String EXTRA_SPOTIFY_ARGUMENT = "spotify_argument";
    public static final String EXTRA_SPOTIFY_REQUEST_ID = "spotify_request_id";

    private static final String CHANNEL_ID = "home_center_operator";
    private static final int NOTIFICATION_ID = 4107;
    private static final long ONLINE_WINDOW_MS = 30000L;
    private static final long CONFIRM_WINDOW_MS = 6000L;
    private static final long REFRESH_MS = 200L;
    private static final int MIN_SCREEN_LEASE_MS = 250;
    private static final int MAX_SCREEN_LEASE_MS = 15000;
    private static final int MAX_SCREEN_YIELD_MS = 12000;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private WindowManager windowManager;
    private WindowManager.LayoutParams windowParams;
    private WindowManager.LayoutParams guardParams;
    private View touchGuard;
    private LinearLayout root;
    private LinearLayout details;
    private TextView dragHandle;
    private TextView status;
    private TextView screenBadge;
    private TextView meta;
    private TextView latest;
    private TextView spotifyStatus;
    private SpotifyShizukuClient spotifyClient;
    private Button collapseButton;
    private Button hideButton;
    private Button compactControlButton;
    private Button muteButton;
    private Button controlButton;
    private EditText adamInput;
    private String adamMode = "auto";
    private boolean expandedText;
    private boolean confirmDisable;
    private float downRawX;
    private float downRawY;
    private int downX;
    private int downY;
    private boolean dragging;
    private int dragThresholdPx;
    private int expandedWidthPx;
    private int lastMeasuredWidth;
    private int lastMeasuredHeight;

    private final Runnable refresh = new Runnable() {
        @Override
        public void run() {
            refreshUi();
            handler.postDelayed(this, REFRESH_MS);
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, buildNotification());
        spotifyClient = new SpotifyShizukuClient();
        submitSpotifyCommand(0L, "status", "");
        if (!Settings.canDrawOverlays(this)) {
            stopSelf();
            return;
        }
        createOverlay();
        handler.post(refresh);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_SPOTIFY_COMMAND.equals(intent.getAction())) {
            String command = intent.getStringExtra(EXTRA_SPOTIFY_COMMAND);
            String argument = intent.getStringExtra(EXTRA_SPOTIFY_ARGUMENT);
            long requestId = intent.getLongExtra(EXTRA_SPOTIFY_REQUEST_ID, 0L);
            submitSpotifyCommand(requestId, command, argument);
        } else if (intent != null && ACTION_SCREEN_ACTIVITY.equals(intent.getAction())) {
            long now = System.currentTimeMillis();
            int leaseMs = clamp(intent.getIntExtra("leaseMs", 2500), MIN_SCREEN_LEASE_MS, MAX_SCREEN_LEASE_MS);
            int yieldMs = clamp(intent.getIntExtra("yieldMs", 0), 0, MAX_SCREEN_YIELD_MS);
            if (OperatorState.controlEnabled(this) && !OperatorState.overlayHidden(this)) {
                long activeUntil = now + leaseMs;
                OperatorState.setScreenActivity(this, activeUntil, Math.min(activeUntil, now + yieldMs));
            } else {
                OperatorState.clearScreenActivity(this);
            }
        } else if (intent != null && ACTION_RESTORE.equals(intent.getAction())) {
            restoreOverlay();
        }
        refreshUi();
        return START_STICKY;
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        recomputeExpandedWidth();
        handler.post(this::applyPresentationState);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (spotifyClient != null) spotifyClient.close();
        removeView(root);
        removeView(touchGuard);
        super.onDestroy();
    }

    private void submitSpotifyCommand(long requestId, String command, String argument) {
        if (spotifyClient == null) return;
        String boundedCommand = command == null ? "" : command.trim();
        String boundedArgument = argument == null ? "" : argument;
        if (boundedCommand.length() > 32 || boundedArgument.length() > 512 || requestId < 0L) {
            handleSpotifyReceipt(requestId, "{\"ok\":false,\"error\":\"SPOTIFY_REQUEST_INVALID\"}");
            return;
        }
        spotifyClient.execute(requestId, boundedCommand, boundedArgument, this::handleSpotifyReceipt);
    }

    private void handleSpotifyReceipt(long requestId, String receiptJson) {
        String exactReceipt = receiptJson == null ? "{}" : receiptJson;
        String summary;
        try {
            JSONObject receipt = new JSONObject(exactReceipt);
            String error = receipt.optString("error", "").trim();
            if (!error.isEmpty()) {
                summary = "Spotify • " + error;
            } else {
                JSONObject after = receipt.optJSONObject("after");
                if (after == null) after = receipt;
                String artist = after.optString("artist", "").trim();
                String title = after.optString("title", "").trim();
                String track = artist.isEmpty() ? title
                        : title.isEmpty() ? artist : artist + " — " + title;
                String state = after.optBoolean("playing", false) ? "playing" : "paused";
                summary = track.isEmpty() ? "Spotify • " + state
                        : "Spotify • " + track + " • " + state;
            }
        } catch (Exception error) {
            summary = "Spotify • invalid receipt";
        }
        long now = System.currentTimeMillis();
        if (requestId > 0L) {
            OperatorState.updateSpotifyReceipt(this, requestId, exactReceipt, summary, now);
        } else {
            OperatorState.updateSpotifySummary(this, summary, now);
        }
        if (spotifyStatus != null) spotifyStatus.setText(summary);
        if (requestId > 0L && spotifyStatus != null) {
            String announcement = summary.length() > 160 ? summary.substring(0, 160) : summary;
            spotifyStatus.announceForAccessibility(announcement);
        }
    }

    private void removeView(View view) {
        if (windowManager == null || view == null) return;
        try {
            windowManager.removeView(view);
        } catch (RuntimeException ignored) {
        }
    }

    private void createNotificationChannel() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Home Center operator control",
                NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Local restore and safety controls for Home Center Phone Hands.");
        manager.createNotificationChannel(channel);
    }

    private Notification buildNotification() {
        Intent open = new Intent(this, MainActivity.class);
        open.setAction(ACTION_RESTORE);
        PendingIntent pending = PendingIntent.getActivity(
                this,
                0,
                open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        String content = OperatorState.overlayHidden(this)
                ? "Overlay hidden and control off — tap to restore"
                : "Tap to restore or bring the local controls forward";
        return new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_sync_noanim)
                .setContentTitle("Home Center operator control")
                .setContentText(content)
                .setOngoing(true)
                .setContentIntent(pending)
                .build();
    }

    private void updateNotification() {
        getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, buildNotification());
    }

    private void createOverlay() {
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        dragThresholdPx = Math.max(
                dp(OverlayUiPolicy.DRAG_THRESHOLD_DP),
                ViewConfiguration.get(this).getScaledTouchSlop());
        recomputeExpandedWidth();

        // This separate guard is inert by default and becomes touchable only for
        // a bounded, explicit visible-screen operation lease.
        touchGuard = new View(this);
        touchGuard.setContentDescription("Remote input active");
        touchGuard.setOnTouchListener((view, event) -> true);
        guardParams = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                        WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE |
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        guardParams.gravity = Gravity.TOP | Gravity.START;
        windowManager.addView(touchGuard, guardParams);

        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(8), dp(6), dp(8), dp(8));
        root.setBackground(background(Color.rgb(27, 29, 34), Color.rgb(95, 104, 120)));
        root.setElevation(dp(10));

        LinearLayout titleRow = new LinearLayout(this);
        titleRow.setOrientation(LinearLayout.HORIZONTAL);
        titleRow.setGravity(Gravity.CENTER_VERTICAL);

        dragHandle = textView(14f, true);
        dragHandle.setText("☰  HOME CENTER");
        dragHandle.setContentDescription("Drag Home Center overlay. Tap to shrink or expand.");
        dragHandle.setGravity(Gravity.CENTER_VERTICAL);
        dragHandle.setMinWidth(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        dragHandle.setMinHeight(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        dragHandle.setPadding(dp(8), 0, dp(10), 0);
        dragHandle.setOnClickListener(v -> setCollapsed(!OperatorState.panelCollapsed(this)));
        dragHandle.setOnTouchListener(this::handleDrag);
        titleRow.addView(dragHandle, new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f));

        collapseButton = iconButton("−", "Shrink overlay");
        collapseButton.setOnClickListener(v -> setCollapsed(!OperatorState.panelCollapsed(this)));
        titleRow.addView(collapseButton);

        compactControlButton = button("STOP");
        compactControlButton.setContentDescription("Disable or enable Home Center control");
        compactControlButton.setOnClickListener(v -> handleControlButton());
        titleRow.addView(compactControlButton);

        hideButton = iconButton("×", "Hide overlay and disable control; restore from notification");
        hideButton.setOnClickListener(v -> hideOverlay());
        titleRow.addView(hideButton);

        LinearLayout spotifyRow = new LinearLayout(this);
        spotifyRow.setOrientation(LinearLayout.HORIZONTAL);
        spotifyRow.setGravity(Gravity.CENTER_VERTICAL);

        spotifyStatus = textView(12f, false);
        spotifyStatus.setText(OperatorState.spotifySummary(this));
        spotifyStatus.setContentDescription("Current Spotify playback status");
        spotifyStatus.setSingleLine(true);
        spotifyStatus.setEllipsize(TextUtils.TruncateAt.END);
        spotifyStatus.setPadding(dp(4), 0, dp(4), 0);
        spotifyRow.addView(spotifyStatus, new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f));

        Button spotifyPreviousButton = button("Previous");
        spotifyPreviousButton.setContentDescription("Play the previous Spotify track");
        spotifyPreviousButton.setOnClickListener(v -> submitSpotifyCommand(
                System.currentTimeMillis(), "previous", ""));
        spotifyRow.addView(spotifyPreviousButton);

        Button spotifyPlayPauseButton = button("Play or pause");
        spotifyPlayPauseButton.setContentDescription("Play or pause Spotify playback");
        spotifyPlayPauseButton.setOnClickListener(v -> submitSpotifyCommand(
                System.currentTimeMillis(), "play_pause", ""));
        spotifyRow.addView(spotifyPlayPauseButton);

        Button spotifyNextButton = button("Next");
        spotifyNextButton.setContentDescription("Play the next Spotify track");
        spotifyNextButton.setOnClickListener(v -> submitSpotifyCommand(
                System.currentTimeMillis(), "next", ""));
        spotifyRow.addView(spotifyNextButton);

        Button spotifyStatusButton = button("Status");
        spotifyStatusButton.setContentDescription("Refresh the current Spotify playback status");
        spotifyStatusButton.setOnClickListener(v -> submitSpotifyCommand(
                System.currentTimeMillis(), "status", ""));
        spotifyRow.addView(spotifyStatusButton);

        details = new LinearLayout(this);
        details.setOrientation(LinearLayout.VERTICAL);

        LinearLayout statusRow = new LinearLayout(this);
        statusRow.setOrientation(LinearLayout.HORIZONTAL);
        statusRow.setGravity(Gravity.CENTER_VERTICAL);

        status = textView(14f, true);
        status.setText("HOME CENTER • OFFLINE");
        status.setContentDescription("Home Center connection and control state");
        statusRow.addView(status, new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f));

        controlButton = button("Disable control");
        controlButton.setContentDescription("Disable or enable Home Center control");
        controlButton.setOnClickListener(v -> handleControlButton());
        statusRow.addView(controlButton);

        screenBadge = textView(12f, true);
        screenBadge.setPadding(dp(8), dp(5), dp(8), dp(5));
        screenBadge.setBackground(background(Color.rgb(42, 73, 96), Color.rgb(89, 163, 211)));
        screenBadge.setVisibility(View.GONE);

        meta = textView(11f, false);
        meta.setTextColor(Color.rgb(190, 198, 212));
        meta.setPadding(0, dp(6), 0, dp(2));

        latest = textView(14f, false);
        latest.setText(OperatorState.latestText(this));
        latest.setMaxLines(2);
        latest.setEllipsize(TextUtils.TruncateAt.END);
        latest.setPadding(dp(8), dp(7), dp(8), dp(7));
        latest.setBackground(background(Color.rgb(39, 42, 49), Color.rgb(67, 73, 86)));
        latest.setVerticalScrollBarEnabled(true);
        latest.setMovementMethod(ScrollingMovementMethod.getInstance());
        latest.setContentDescription("Latest Home Center or Adam message. Tap to expand or collapse text.");
        latest.setOnClickListener(v -> {
            expandedText = !expandedText;
            applyExpandedTextState();
        });

        LinearLayout adamModeRow = new LinearLayout(this);
        adamModeRow.setOrientation(LinearLayout.HORIZONTAL);
        adamModeRow.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        adamModeRow.setPadding(0, dp(6), 0, dp(2));
        adamModeRow.addView(adamModeButton("TERM", "terminal", "Adam terminal executor mode"));
        adamModeRow.addView(adamModeButton("CHAT", "chat", "Adam local chatbot mode"));
        adamModeRow.addView(adamModeButton("CONT", "continue", "Adam Continue consumer mode"));
        adamModeRow.addView(adamModeButton("VLAD", "vlad", "Ask Vlad for a bounded consultation"));
        adamModeRow.addView(adamModeButton(
                "RADIO", "radio", "Adam mode for bounded background Spotify prompts"));

        LinearLayout adamInputRow = new LinearLayout(this);
        adamInputRow.setOrientation(LinearLayout.HORIZONTAL);
        adamInputRow.setGravity(Gravity.CENTER_VERTICAL);

        adamInput = new EditText(this);
        adamInput.setTextColor(Color.WHITE);
        adamInput.setHintTextColor(Color.rgb(155, 165, 182));
        adamInput.setHint("Talk to Adam…");
        adamInput.setTextSize(14f);
        adamInput.setSingleLine(false);
        adamInput.setMaxLines(4);
        adamInput.setMinHeight(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        adamInput.setPadding(dp(8), dp(4), dp(8), dp(4));
        adamInput.setBackground(background(Color.rgb(32, 35, 42), Color.rgb(78, 88, 105)));
        adamInput.setContentDescription("Talk to Adam naturally. Routing is automatic; fixed phone commands stay deterministic.");
        adamInputRow.addView(adamInput, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        Button adamSendButton = button("Ask");
        adamSendButton.setContentDescription("Send a natural-language request to Adam using automatic routing");
        adamSendButton.setOnClickListener(v -> submitAdamRequest());
        adamInputRow.addView(adamSendButton);

        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setOrientation(LinearLayout.HORIZONTAL);
        actionRow.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
        actionRow.setPadding(0, dp(4), 0, 0);

        muteButton = button("Mute speech");
        muteButton.setContentDescription("Mute or unmute Home Center status speech");
        muteButton.setOnClickListener(v -> {
            OperatorState.setMuted(this, !OperatorState.muted(this));
            refreshUi();
        });
        actionRow.addView(muteButton);

        Button hideFullButton = button("Hide overlay");
        hideFullButton.setContentDescription("Hide overlay and disable control; restore from notification");
        hideFullButton.setOnClickListener(v -> hideOverlay());
        actionRow.addView(hideFullButton);

        LinearLayout quickActionRow = new LinearLayout(this);
        quickActionRow.setOrientation(LinearLayout.HORIZONTAL);
        quickActionRow.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        quickActionRow.setPadding(0, dp(4), 0, dp(2));
        quickActionRow.addView(quickRequestButton("Restart", "restart", "Restart or repair Home Center overlay"));
        quickActionRow.addView(quickRequestButton("Night", "night", "Read cheap Night Core battery and relay status"));
        quickActionRow.addView(quickRequestButton("Chrome", "chrome", "Open Chromium through the deterministic phone controller"));
        quickActionRow.addView(quickRequestButton("Canary", "canary", "Run the physical phone acceptance canary"));

        details.addView(statusRow);
        details.addView(quickActionRow);
        details.addView(screenBadge);
        details.addView(meta);
        details.addView(latest);
        details.addView(adamInputRow);
        details.addView(actionRow);
        root.addView(titleRow);
        root.addView(details);

        windowParams = new WindowManager.LayoutParams(
                expandedWidthPx,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        windowParams.gravity = Gravity.TOP | Gravity.START;
        windowParams.x = OperatorState.overlayX(this);
        windowParams.y = OperatorState.overlayY(this);

        windowManager.addView(root, windowParams);
        root.addOnLayoutChangeListener((view, left, top, right, bottom,
                oldLeft, oldTop, oldRight, oldBottom) -> {
            int width = right - left;
            int height = bottom - top;
            if (width != lastMeasuredWidth || height != lastMeasuredHeight) {
                lastMeasuredWidth = width;
                lastMeasuredHeight = height;
                handler.post(this::clampAndPersistPosition);
            }
        });
        root.setVisibility(OperatorState.overlayHidden(this) ? View.GONE : View.VISIBLE);
        applyPresentationState();
        refreshUi();
    }

    private boolean handleDrag(View view, MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                downRawX = event.getRawX();
                downRawY = event.getRawY();
                downX = windowParams.x;
                downY = windowParams.y;
                dragging = false;
                return true;
            case MotionEvent.ACTION_MOVE:
                float deltaX = event.getRawX() - downRawX;
                float deltaY = event.getRawY() - downRawY;
                if (!dragging) {
                    dragging = OverlayUiPolicy.isDrag(deltaX, deltaY, dragThresholdPx);
                }
                if (dragging) applyPosition(downX + (int) deltaX, downY + (int) deltaY);
                return true;
            case MotionEvent.ACTION_UP:
                float upDeltaX = event.getRawX() - downRawX;
                float upDeltaY = event.getRawY() - downRawY;
                if (OverlayUiPolicy.isClick(upDeltaX, upDeltaY, dragThresholdPx)) {
                    view.performClick();
                }
                clampAndPersistPosition();
                dragging = false;
                return true;
            case MotionEvent.ACTION_CANCEL:
                dragging = false;
                clampAndPersistPosition();
                return true;
            default:
                return false;
        }
    }

    private void applyPosition(int proposedX, int proposedY) {
        if (root == null || windowParams == null || windowManager == null) return;
        Rect visible = visibleBounds();
        int[] position = OverlayUiPolicy.clampPosition(
                proposedX,
                proposedY,
                visible.left,
                visible.top,
                visible.right,
                visible.bottom,
                Math.max(root.getWidth(), dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP)),
                Math.max(root.getHeight(), dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP)),
                dp(8));
        windowParams.x = position[0];
        windowParams.y = position[1];
        windowManager.updateViewLayout(root, windowParams);
    }

    private Rect visibleBounds() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowMetrics metrics = windowManager.getCurrentWindowMetrics();
            Rect bounds = new Rect(metrics.getBounds());
            Insets insets = metrics.getWindowInsets().getInsetsIgnoringVisibility(
                    WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            bounds.left += insets.left;
            bounds.top += insets.top;
            bounds.right -= insets.right;
            bounds.bottom -= insets.bottom;
            return bounds;
        }
        return new Rect(
                0,
                0,
                getResources().getDisplayMetrics().widthPixels,
                getResources().getDisplayMetrics().heightPixels);
    }

    private void clampAndPersistPosition() {
        if (root == null || windowParams == null || windowManager == null || root.getVisibility() != View.VISIBLE) return;
        applyPosition(windowParams.x, windowParams.y);
        OperatorState.setOverlayPosition(this, windowParams.x, windowParams.y);
    }

    private void setCollapsed(boolean collapsed) {
        OperatorState.setPanelCollapsed(this, collapsed);
        expandedText = false;
        applyExpandedTextState();
        applyPresentationState();
    }

    private void applyPresentationState() {
        if (root == null || windowParams == null) return;
        boolean collapsed = OperatorState.panelCollapsed(this);
        details.setVisibility(collapsed ? View.GONE : View.VISIBLE);
        hideButton.setVisibility(collapsed ? View.GONE : View.VISIBLE);
        compactControlButton.setVisibility(collapsed ? View.VISIBLE : View.GONE);
        collapseButton.setText(collapsed ? "+" : "−");
        collapseButton.setContentDescription(collapsed ? "Expand overlay" : "Shrink overlay");
        windowParams.width = collapsed ? WindowManager.LayoutParams.WRAP_CONTENT : expandedWidthPx;
        int focusFlags = WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL;
        if (collapsed) focusFlags |= WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE;
        windowParams.flags = focusFlags;
        if (collapsed && adamInput != null) adamInput.clearFocus();
        windowManager.updateViewLayout(root, windowParams);
        root.requestLayout();
        root.post(this::clampAndPersistPosition);
        refreshUi();
    }

    private void hideOverlay() {
        if (root == null) return;
        confirmDisable = false;
        // Commit the fail-closed state before removing the user's visible escape.
        OperatorState.setControlEnabled(this, false);
        OperatorState.setOverlayHidden(this, OverlayUiPolicy.nextHidden(
                false,
                OverlayUiPolicy.VisibilityAction.HIDE));
        syncTouchGuard(false);
        root.setVisibility(View.GONE);
        updateNotification();
    }

    private void restoreOverlay() {
        OperatorState.setControlEnabled(this, false);
        OperatorState.setOverlayHidden(this, OverlayUiPolicy.nextHidden(
                true,
                OverlayUiPolicy.VisibilityAction.RESTORE));
        if (root != null) {
            root.setVisibility(View.VISIBLE);
            applyPresentationState();
        }
        updateNotification();
    }

    private void handleControlButton() {
        boolean enabled = OperatorState.controlEnabled(this);
        if (!enabled) {
            confirmDisable = false;
            OperatorState.setControlEnabled(this, true);
            refreshUi();
            return;
        }
        if (!confirmDisable) {
            confirmDisable = true;
            refreshUi();
            handler.postDelayed(() -> {
                confirmDisable = false;
                refreshUi();
            }, CONFIRM_WINDOW_MS);
            return;
        }
        confirmDisable = false;
        OperatorState.setControlEnabled(this, false);
        syncTouchGuard(false);
        refreshUi();
    }

    private void applyExpandedTextState() {
        if (latest == null) return;
        if (expandedText) {
            latest.setMaxLines(30);
            latest.setMaxHeight(dp(520));
            latest.setEllipsize(null);
        } else {
            latest.scrollTo(0, 0);
            latest.setMaxLines(2);
            latest.setMaxHeight(Integer.MAX_VALUE);
            latest.setEllipsize(TextUtils.TruncateAt.END);
        }
        latest.requestLayout();
        latest.post(this::clampAndPersistPosition);
    }

    private void syncTouchGuard(boolean active) {
        if (windowManager == null || touchGuard == null || guardParams == null) return;
        int flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN;
        if (!active) flags |= WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE;
        if (guardParams.flags != flags) {
            guardParams.flags = flags;
            windowManager.updateViewLayout(touchGuard, guardParams);
        }
        touchGuard.setBackgroundColor(active ? Color.argb(10, 12, 32, 52) : Color.TRANSPARENT);
    }

    private void refreshUi() {
        if (root == null) return;
        long now = System.currentTimeMillis();
        boolean enabled = OperatorState.controlEnabled(this);
        boolean muted = OperatorState.muted(this);
        long heartbeat = OperatorState.lastHeartbeatMs(this);
        long screenActiveUntil = OperatorState.screenActiveUntilMs(this);
        long screenYieldUntil = OperatorState.screenYieldUntilMs(this);
        boolean online = heartbeat > 0 && now - heartbeat <= ONLINE_WINDOW_MS;
        boolean screenActive = screenActiveUntil > now;
        boolean screenYield = screenYieldUntil > now;
        boolean hidden = OperatorState.overlayHidden(this);

        boolean guardActive = OverlayUiPolicy.touchGuardActive(
                enabled,
                online,
                screenActive,
                screenYield) && !hidden;
        syncTouchGuard(guardActive);

        String state;
        String compactState;
        int stateColor;
        if (!enabled) {
            state = "CONTROL OFF";
            compactState = "HC • OFF";
            stateColor = Color.rgb(255, 145, 145);
        } else if (!online) {
            state = "HOME CENTER • OFFLINE";
            compactState = "HC • OFFLINE";
            stateColor = Color.rgb(255, 211, 132);
        } else if (screenActive) {
            state = "REMOTE INPUT • ACTIVE";
            compactState = "HC • ACTIVE";
            stateColor = Color.rgb(132, 211, 255);
        } else {
            state = "HOME CENTER • ON";
            compactState = "HC • ON";
            stateColor = Color.rgb(151, 255, 178);
        }
        if (muted) state += " • MUTED";
        status.setText(state);
        status.setTextColor(stateColor);
        dragHandle.setText(OperatorState.panelCollapsed(this)
                ? "☰  " + compactState
                : "☰  HOME CENTER");
        dragHandle.setTextColor(stateColor);

        if (!OperatorState.panelCollapsed(this) && screenActive) {
            screenBadge.setVisibility(View.VISIBLE);
            screenBadge.setText(screenYield
                    ? "REMOTE INPUT • action pulse — your touch remains available"
                    : "REMOTE INPUT • local screen input temporarily reserved");
        } else {
            screenBadge.setVisibility(View.GONE);
        }

        muteButton.setText(muted ? "Unmute speech" : "Mute speech");
        String fullControlLabel;
        String compactControlLabel;
        if (!enabled) {
            fullControlLabel = "Enable control";
            compactControlLabel = "ENABLE";
        } else if (confirmDisable) {
            fullControlLabel = "Confirm disable";
            compactControlLabel = "CONFIRM";
        } else {
            fullControlLabel = "Disable control";
            compactControlLabel = "STOP";
        }
        controlButton.setText(fullControlLabel);
        compactControlButton.setText(compactControlLabel);

        String source = OperatorState.latestSource(this);
        long lastUpdate = OperatorState.lastUpdateMs(this);
        String lease = screenActive
                ? " • screen lease " + Math.max(1L, (screenActiveUntil - now + 999L) / 1000L) + "s"
                : " • screen idle";
        meta.setText(source + " • " + age(now, lastUpdate) + lease +
                (expandedText ? " • tap message to collapse" : " • tap message to expand"));
        latest.setText(OperatorState.latestText(this));
        String spotifySummary = OperatorState.spotifySummary(this);
        if (spotifyStatus != null && !TextUtils.equals(spotifyStatus.getText(), spotifySummary)) {
            spotifyStatus.setText(spotifySummary);
        }
    }

    private Button quickRequestButton(String label, String request, String description) {
        Button value = button(label);
        value.setContentDescription(description);
        value.setOnClickListener(v -> {
            OperatorState.submitAdamRequest(this, "auto", request, System.currentTimeMillis());
            if (adamInput != null) {
                adamInput.setHint("Talk to Adam…");
                adamInput.announceForAccessibility(label + " sent to Adam");
            }
        });
        return value;
    }

    private Button adamModeButton(String label, String mode, String description) {
        Button value = button(label);
        value.setContentDescription(description);
        value.setOnClickListener(v -> {
            adamMode = mode;
            if (adamInput != null) {
                adamInput.setHint("Adam — " + mode);
                adamInput.setContentDescription("Adam input. Current mode " + mode + ".");
                adamInput.requestFocus();
            }
        });
        return value;
    }

    private void submitAdamRequest() {
        if (adamInput == null) return;
        String text = adamInput.getText().toString().trim();
        if (text.isEmpty()) return;
        OperatorState.submitAdamRequest(this, adamMode, text, System.currentTimeMillis());
        adamInput.setText("");
        adamInput.setHint("Talk to Adam…");
        adamInput.announceForAccessibility("Sent to Adam");
    }

    private void recomputeExpandedWidth() {
        Rect visible = windowManager == null
                ? new Rect(0, 0,
                        getResources().getDisplayMetrics().widthPixels,
                        getResources().getDisplayMetrics().heightPixels)
                : visibleBounds();
        expandedWidthPx = Math.max(dp(280), Math.min(visible.width() - dp(16), dp(420)));
    }

    private String age(long now, long then) {
        if (then <= 0) return "waiting for update";
        long seconds = Math.max(0L, (now - then) / 1000L);
        if (seconds < 5) return "now";
        if (seconds < 60) return seconds + "s ago";
        long minutes = seconds / 60L;
        if (minutes < 60) return minutes + "m ago";
        return (minutes / 60L) + "h ago";
    }

    private TextView textView(float sp, boolean bold) {
        TextView view = new TextView(this);
        view.setTextColor(Color.WHITE);
        view.setTextSize(sp);
        if (bold) view.setTypeface(view.getTypeface(), android.graphics.Typeface.BOLD);
        return view;
    }

    private Button button(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(11f);
        button.setAllCaps(false);
        button.setMinHeight(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        button.setMinimumHeight(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        button.setMinWidth(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        button.setMinimumWidth(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        button.setPadding(dp(8), 0, dp(8), 0);
        return button;
    }

    private Button iconButton(String label, String description) {
        Button button = button(label);
        button.setContentDescription(description);
        button.setTextSize(18f);
        button.setPadding(0, 0, 0, 0);
        return button;
    }

    private GradientDrawable background(int color, int strokeColor) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(14));
        drawable.setStroke(dp(1), strokeColor);
        return drawable;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(value, max));
    }
}
