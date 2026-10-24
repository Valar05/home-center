package com.homecenter.ritsucontrol;

import android.content.Context;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Point;
import android.graphics.drawable.GradientDrawable;
import android.provider.Settings;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Optional user-authorized draggable overlay. No Shizuku or touch interception.
 * Collapsed 56dp floating button -> expanded local microphone controls. */
final class RitsuBubble {
    interface Actions {
        void toggleMute();
        void stopSession();
        void hideBubble();
        ListeningPolicy.Mode mode();
    }
    private final Context context;
    private final WindowManager windows;
    private final Actions actions;
    private LinearLayout root, controls;
    private TextView handle, indicator;
    private Button mute;
    private WindowManager.LayoutParams params;
    private boolean expanded;

    RitsuBubble(Context context, Actions actions) {
        this.context = context;
        this.actions = actions;
        this.windows = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
    }

    boolean isShowing() { return root != null; }

    boolean show() {
        if (root != null) { refresh(); return true; }
        if (!Settings.canDrawOverlays(context)) return false;
        LinearLayout panel = new LinearLayout(context);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setGravity(Gravity.CENTER_HORIZONTAL);
        TextView bubble = new TextView(context);
        bubble.setText("R");
        bubble.setTextSize(22);
        bubble.setTextColor(Color.WHITE);
        bubble.setGravity(Gravity.CENTER);
        bubble.setContentDescription("Ritsu microphone bubble. Tap to open mute controls; drag to move.");
        bubble.setMinimumWidth(dp(56));
        bubble.setMinimumHeight(dp(56));
        GradientDrawable badge = new GradientDrawable();
        badge.setShape(GradientDrawable.OVAL);
        badge.setColor(Color.rgb(85, 55, 132));
        badge.setStroke(dp(2), Color.WHITE);
        bubble.setBackground(badge);
        panel.addView(bubble, new LinearLayout.LayoutParams(dp(56), dp(56)));

        LinearLayout menu = new LinearLayout(context);
        menu.setOrientation(LinearLayout.VERTICAL);
        menu.setPadding(dp(8), dp(8), dp(8), dp(8));
        GradientDrawable backdrop = new GradientDrawable();
        backdrop.setColor(Color.rgb(30, 25, 45));
        backdrop.setCornerRadius(dp(15));
        menu.setBackground(backdrop);
        TextView label = new TextView(context);
        label.setTextColor(Color.WHITE);
        label.setTextSize(13);
        label.setGravity(Gravity.CENTER);
        label.setPadding(dp(4), dp(6), dp(4), dp(6));
        menu.addView(label);
        Button toggle = new Button(context);
        toggle.setMinHeight(dp(48));
        toggle.setTextSize(13);
        toggle.setAllCaps(false);
        toggle.setOnClickListener(v -> { actions.toggleMute(); refresh(); });
        menu.addView(toggle);
        Button stop = new Button(context);
        stop.setText("Stop session");
        stop.setAllCaps(false);
        stop.setMinHeight(dp(48));
        stop.setTextSize(13);
        stop.setOnClickListener(v -> actions.stopSession());
        menu.addView(stop);
        Button hide = new Button(context);
        hide.setText("Hide bubble");
        hide.setAllCaps(false);
        hide.setMinHeight(dp(48));
        hide.setTextSize(13);
        hide.setOnClickListener(v -> actions.hideBubble());
        menu.addView(hide);
        menu.setVisibility(View.GONE);
        panel.addView(menu);

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                        WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL |
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        lp.gravity = Gravity.TOP | Gravity.LEFT;
        Point size = new Point();
        windows.getDefaultDisplay().getSize(size);
        lp.x = Math.max(dp(8), size.x - dp(80));
        lp.y = Math.max(dp(64), size.y / 3);
        // A real click listener is required so TalkBack can expand/collapse
        // the controls through accessibility, not merely a raw touch gesture.
        bubble.setOnClickListener(v -> {
            expanded = !expanded;
            menu.setVisibility(expanded ? View.VISIBLE : View.GONE);
            if (expanded) {
                lp.x = Math.min(lp.x, Math.max(0, size.x - dp(210)));
                lp.y = Math.min(lp.y, Math.max(0, size.y - dp(285)));
            }
            refresh();
            try { windows.updateViewLayout(panel, lp); }
            catch (RuntimeException ignored) {}
        });
        bubble.setOnTouchListener(new View.OnTouchListener() {
            private float initialRawX, initialRawY;
            private int startingX, startingY;
            private boolean dragging;
            @Override public boolean onTouch(View v, MotionEvent event) {
                switch (event.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        initialRawX = event.getRawX(); initialRawY = event.getRawY();
                        startingX = lp.x; startingY = lp.y;
                        dragging = false;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        float dx = event.getRawX() - initialRawX;
                        float dy = event.getRawY() - initialRawY;
                        if (dragging || dx * dx + dy * dy > dp(8) * dp(8)) {
                            dragging = true;
                            lp.x = Math.max(0, Math.min(size.x - dp(56), startingX + Math.round(dx)));
                            lp.y = Math.max(0, Math.min(size.y - dp(56), startingY + Math.round(dy)));
                            try { windows.updateViewLayout(panel, lp); }
                            catch (RuntimeException ignored) {}
                        }
                        return true;
                    case MotionEvent.ACTION_UP:
                        if (!dragging) v.performClick();
                        return true;
                    default: return false;
                }
            }
        });
        try {
            windows.addView(panel, lp);
            root = panel; controls = menu; handle = bubble; indicator = label; mute = toggle;
            params = lp; expanded = false;
            refresh();
            return true;
        } catch (RuntimeException failure) {
            root = null; controls = null; handle = null; indicator = null; mute = null; params = null;
            return false;
        }
    }

    void refresh() {
        if (root == null) return;
        ListeningPolicy.Mode mode = actions.mode();
        indicator.setText(mode == ListeningPolicy.Mode.RECOGNIZING ? "Google speech recognition"
                : mode == ListeningPolicy.Mode.LISTENING ? "Mic listening"
                : mode == ListeningPolicy.Mode.MUTED ? "Mic muted"
                : mode == ListeningPolicy.Mode.ERROR ? "Mic error" : "Mic off");
        mute.setText(mode == ListeningPolicy.Mode.RECOGNIZING ? "Cancel speech and mute"
                : mode == ListeningPolicy.Mode.LISTENING ? "Mute microphone"
                : mode == ListeningPolicy.Mode.MUTED ? "Resume microphone" : "Open app to listen");
        handle.setText(mode == ListeningPolicy.Mode.RECOGNIZING ? "…" :
                mode == ListeningPolicy.Mode.LISTENING ? "●" :
                mode == ListeningPolicy.Mode.MUTED ? "×" : "R");
        mute.setContentDescription(mute.getText().toString());
    }

    void hide() {
        if (root == null) return;
        try { windows.removeView(root); } catch (RuntimeException ignored) {}
        root = null; controls = null; handle = null; indicator = null; mute = null; params = null;
        expanded = false;
    }
    private int dp(int value) { return Math.round(value * context.getResources().getDisplayMetrics().density); }
}
