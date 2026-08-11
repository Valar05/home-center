package com.homecenter.operatoroverlay;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.text.TextUtils;
import android.text.method.ScrollingMovementMethod;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public class OperatorOverlayService extends Service {
    public static final String ACTION_SCREEN_ACTIVITY = "com.homecenter.operatoroverlay.SCREEN_ACTIVITY";

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
    private TextView status;
    private TextView screenBadge;
    private TextView meta;
    private TextView latest;
    private Button collapseButton;
    private Button muteButton;
    private Button controlButton;
    private boolean expanded = false;
    private boolean confirmDisable = false;
    private float downRawX;
    private float downRawY;
    private int downX;
    private int downY;

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
        if (!Settings.canDrawOverlays(this)) {
            stopSelf();
            return;
        }
        createOverlay();
        handler.post(refresh);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_SCREEN_ACTIVITY.equals(intent.getAction())) {
            long now = System.currentTimeMillis();
            int leaseMs = clamp(intent.getIntExtra("leaseMs", 2500), MIN_SCREEN_LEASE_MS, MAX_SCREEN_LEASE_MS);
            int yieldMs = clamp(intent.getIntExtra("yieldMs", 0), 0, MAX_SCREEN_YIELD_MS);
            if (OperatorState.controlEnabled(this)) {
                long activeUntil = now + leaseMs;
                long yieldUntil = Math.min(activeUntil, now + yieldMs);
                OperatorState.setScreenActivity(this, activeUntil, yieldUntil);
            } else {
                OperatorState.clearScreenActivity(this);
            }
            refreshUi();
        }
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (windowManager != null && root != null) {
            try {
                windowManager.removeView(root);
            } catch (RuntimeException ignored) {
            }
        }
        if (windowManager != null && touchGuard != null) {
            try {
                windowManager.removeView(touchGuard);
            } catch (RuntimeException ignored) {
            }
        }
        super.onDestroy();
    }

    private void createNotificationChannel() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Home Center operator control",
                NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Keeps the visible Home Center operator control overlay alive.");
        manager.createNotificationChannel(channel);
    }

    private Notification buildNotification() {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pending = PendingIntent.getActivity(
                this,
                0,
                open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_sync_noanim)
                .setContentTitle("Home Center operator control")
                .setContentText("Visible control toggle is active")
                .setOngoing(true)
                .setContentIntent(pending)
                .build();
    }

    private void createOverlay() {
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        // Full-screen input guard is present but touch-pass-through by default.
        // It may consume local touches only during a short active-screen lease.
        touchGuard = new View(this);
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
        root.setPadding(dp(10), dp(7), dp(10), dp(7));
        root.setBackground(background(Color.rgb(31, 31, 31)));

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        status = textView(14f, true);
        status.setText("HOME CENTER • OFFLINE");
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        header.addView(status, statusParams);

        collapseButton = button("Hide");
        collapseButton.setOnClickListener(v -> {
            boolean next = !OperatorState.panelCollapsed(this);
            OperatorState.setPanelCollapsed(this, next);
            applyCollapsedState();
            refreshUi();
        });
        header.addView(collapseButton);

        controlButton = button("Disable control");
        controlButton.setOnClickListener(v -> handleControlButton());
        header.addView(controlButton);

        muteButton = button("Mute");
        muteButton.setOnClickListener(v -> {
            OperatorState.setMuted(this, !OperatorState.muted(this));
            refreshUi();
        });

        screenBadge = textView(11f, true);
        screenBadge.setPadding(0, dp(4), 0, dp(2));
        screenBadge.setVisibility(View.GONE);

        meta = textView(11f, false);
        meta.setPadding(0, dp(4), 0, dp(2));

        latest = textView(13f, false);
        latest.setText(OperatorState.latestText(this));
        latest.setMaxLines(2);
        latest.setEllipsize(TextUtils.TruncateAt.END);
        latest.setPadding(0, dp(2), 0, dp(2));
        latest.setVerticalScrollBarEnabled(true);
        latest.setMovementMethod(ScrollingMovementMethod.getInstance());
        latest.setOnClickListener(v -> {
            expanded = !expanded;
            applyExpandedState();
        });

        root.addView(header);
        root.addView(muteButton);
        root.addView(screenBadge);
        root.addView(meta);
        root.addView(latest);

        int screenWidth = getResources().getDisplayMetrics().widthPixels;
        int overlayWidth = Math.min(screenWidth - dp(16), dp(440));
        windowParams = new WindowManager.LayoutParams(
                overlayWidth,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        windowParams.gravity = Gravity.TOP | Gravity.START;
        windowParams.x = dp(8);
        windowParams.y = dp(28);

        status.setOnTouchListener((view, event) -> {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downRawX = event.getRawX();
                    downRawY = event.getRawY();
                    downX = windowParams.x;
                    downY = windowParams.y;
                    return true;
                case MotionEvent.ACTION_MOVE:
                    int proposedX = downX + (int) (event.getRawX() - downRawX);
                    int proposedY = downY + (int) (event.getRawY() - downRawY);
                    int displayWidth = getResources().getDisplayMetrics().widthPixels;
                    int displayHeight = getResources().getDisplayMetrics().heightPixels;
                    int viewWidth = windowParams.width > 0 ? windowParams.width : Math.max(root.getWidth(), dp(120));
                    int viewHeight = Math.max(root.getHeight(), dp(52));
                    int maxX = Math.max(0, displayWidth - viewWidth);
                    int maxY = Math.max(0, displayHeight - viewHeight);
                    windowParams.x = Math.max(0, Math.min(proposedX, maxX));
                    windowParams.y = Math.max(0, Math.min(proposedY, maxY));
                    windowManager.updateViewLayout(root, windowParams);
                    return true;
                default:
                    return true;
            }
        });

        windowManager.addView(root, windowParams);
        applyCollapsedState();
        refreshUi();
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
            controlButton.setText("Confirm disable");
            handler.postDelayed(() -> {
                confirmDisable = false;
                refreshUi();
            }, CONFIRM_WINDOW_MS);
            return;
        }
        confirmDisable = false;
        OperatorState.setControlEnabled(this, false);
        refreshUi();
    }

    private void applyExpandedState() {
        if (expanded) {
            latest.setMaxLines(30);
            latest.setMaxHeight(dp(560));
            latest.setEllipsize(null);
        } else {
            latest.scrollTo(0, 0);
            latest.setMaxLines(2);
            latest.setMaxHeight(Integer.MAX_VALUE);
            latest.setEllipsize(TextUtils.TruncateAt.END);
        }
        latest.requestLayout();
        refreshUi();
    }

    private void applyCollapsedState() {
        if (root == null) return;
        boolean collapsed = OperatorState.panelCollapsed(this);
        collapseButton.setText(collapsed ? "Show" : "Hide");
        muteButton.setVisibility(collapsed ? View.GONE : View.VISIBLE);
        screenBadge.setVisibility(View.GONE);
        meta.setVisibility(collapsed ? View.GONE : View.VISIBLE);
        latest.setVisibility(collapsed ? View.GONE : View.VISIBLE);
        root.requestLayout();
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
        touchGuard.setBackgroundColor(active ? Color.argb(8, 0, 0, 0) : Color.TRANSPARENT);
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

        // Permission + liveness are necessary but not sufficient. Local input is
        // blocked only while an explicit active-screen lease exists. During the
        // short remote-input yield pulse the guard is temporarily pass-through
        // so injected Android input reaches the target app rather than this guard.
        syncTouchGuard(enabled && online && screenActive && !screenYield);

        String state;
        int stateColor;
        if (!enabled) {
            state = "CONTROL OFF";
            stateColor = Color.rgb(255, 130, 130);
        } else if (!online) {
            state = "HOME CENTER • OFFLINE";
            stateColor = Color.rgb(255, 210, 130);
        } else if (screenActive) {
            state = "REMOTE INPUT • ACTIVE";
            stateColor = Color.rgb(150, 220, 255);
        } else {
            state = "HOME CENTER • ON";
            stateColor = Color.rgb(150, 255, 170);
        }
        if (muted) state += " • MUTED";
        status.setText(state);
        status.setTextColor(stateColor);

        if (!OperatorState.panelCollapsed(this) && screenActive) {
            screenBadge.setVisibility(View.VISIBLE);
            screenBadge.setText(screenYield
                    ? "REMOTE INPUT • action pulse"
                    : "REMOTE INPUT • local input blocked");
        } else {
            screenBadge.setVisibility(View.GONE);
        }

        muteButton.setText(muted ? "Unmute" : "Mute");
        if (!enabled) {
            controlButton.setText("Enable control");
        } else if (confirmDisable) {
            controlButton.setText("Confirm disable");
        } else {
            controlButton.setText("Disable control");
        }

        String source = OperatorState.latestSource(this);
        long lastUpdate = OperatorState.lastUpdateMs(this);
        String activeText = screenActive
                ? " • screen lease " + Math.max(1L, (screenActiveUntil - now + 999L) / 1000L) + "s"
                : " • screen idle";
        meta.setText(source + " • " + age(now, lastUpdate) + activeText +
                (expanded ? " • tap text to collapse" : " • tap text to expand"));
        latest.setText(OperatorState.latestText(this));
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
        button.setMinHeight(dp(36));
        button.setMinimumHeight(dp(36));
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setPadding(dp(8), 0, dp(8), 0);
        return button;
    }

    private GradientDrawable background(int color) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(12));
        drawable.setStroke(dp(1), Color.rgb(90, 90, 90));
        return drawable;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(value, max));
    }
}
