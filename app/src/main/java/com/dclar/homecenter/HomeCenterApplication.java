package com.dclar.homecenter;

import android.app.Activity;
import android.app.Application;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.graphics.Color;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * Application-level ingress bridge for the current MainActivity monolith.
 *
 * MainActivity historically disables its composer while a model/tool turn is active. That makes
 * every new operator thought an interruption decision. This bridge adds a small second composer
 * only while the ordinary composer is unavailable, persists those messages, and drains them FIFO
 * through MainActivity's normal submission path after the current turn or confirmation barrier.
 *
 * The reflection seam is intentionally tiny and fail-closed. It exists so the queue can ship
 * without rewriting the very large MainActivity in the same repair. A contract test pins the
 * four private seams used here; a future MainActivity refactor can replace this adapter with a
 * typed interface without changing OperatorIngressQueue.
 */
public final class HomeCenterApplication extends Application {
    private OperatorIngressQueue ingressQueue;

    @Override
    public void onCreate() {
        super.onCreate();
        ingressQueue = new OperatorIngressQueue(this);
        ingressQueue.recoverInflight();
        registerActivityLifecycleCallbacks(new QueueBridge());
    }

    private final class QueueBridge implements ActivityLifecycleCallbacks {
        private static final long POLL_MS = 300L;
        private final Handler main = new Handler(Looper.getMainLooper());

        private Activity active;
        private FrameLayout host;
        private LinearLayout panel;
        private TextView status;
        private EditText input;
        private Button queueButton;

        private Field busyField;
        private Field pendingConfirmationField;
        private Field pendingReconnectField;
        private Field activeConversationField;
        private Method submitMessageMethod;
        private boolean seamResolved;
        private boolean seamFailed;

        private final Runnable pulse = new Runnable() {
            @Override
            public void run() {
                if (active == null) return;
                try {
                    tick();
                } catch (Exception ex) {
                    android.util.Log.w("HomeCenterQueue", "queue tick failed", ex);
                }
                if (active != null) main.postDelayed(this, POLL_MS);
            }
        };

        @Override
        public void onActivityResumed(Activity activity) {
            if (!isMainActivity(activity)) return;
            active = activity;
            if (!resolveSeam(activity)) return;
            installPanel(activity);
            main.removeCallbacks(pulse);
            main.post(pulse);
        }

        @Override
        public void onActivityPaused(Activity activity) {
            if (activity != active) return;
            main.removeCallbacks(pulse);
            removePanel();
            active = null;
        }

        @Override
        public void onActivityDestroyed(Activity activity) {
            if (activity != active) return;
            main.removeCallbacks(pulse);
            removePanel();
            active = null;
        }

        @Override public void onActivityCreated(Activity activity, Bundle state) {}
        @Override public void onActivityStarted(Activity activity) {}
        @Override public void onActivityStopped(Activity activity) {}
        @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) {}

        private boolean isMainActivity(Activity activity) {
            return activity != null && "com.dclar.homecenter.MainActivity".equals(activity.getClass().getName());
        }

        private boolean resolveSeam(Activity activity) {
            if (seamResolved) return true;
            if (seamFailed || activity == null) return false;
            try {
                Class<?> type = activity.getClass();
                busyField = declaredField(type, "busy");
                pendingConfirmationField = declaredField(type, "pendingToolConfirmation");
                pendingReconnectField = declaredField(type, "pendingAgentTurnAfterGoogleReconnect");
                activeConversationField = declaredField(type, "activeConversationId");
                submitMessageMethod = type.getDeclaredMethod("submitMessage", String.class, boolean.class);
                submitMessageMethod.setAccessible(true);
                seamResolved = true;
                android.util.Log.i("HomeCenterQueue", "operator ingress seam ready");
                return true;
            } catch (Exception ex) {
                seamFailed = true;
                android.util.Log.e("HomeCenterQueue", "operator ingress seam unavailable; ordinary chat left untouched", ex);
                return false;
            }
        }

        private Field declaredField(Class<?> type, String name) throws Exception {
            Field field = type.getDeclaredField(name);
            field.setAccessible(true);
            return field;
        }

        private void installPanel(Activity activity) {
            if (panel != null) return;
            View content = activity.findViewById(android.R.id.content);
            if (!(content instanceof FrameLayout)) return;
            host = (FrameLayout) content;

            panel = new LinearLayout(activity);
            panel.setOrientation(LinearLayout.VERTICAL);
            panel.setPadding(dp(activity, 12), dp(activity, 9), dp(activity, 12), dp(activity, 9));
            panel.setBackgroundColor(Color.argb(248, 18, 18, 18));
            panel.setElevation(dp(activity, 18));
            panel.setVisibility(View.GONE);
            panel.setContentDescription("Home Center queued message composer");

            status = new TextView(activity);
            status.setTextColor(Color.WHITE);
            status.setTextSize(12f);
            status.setText("Current work continues. Queue another message.");
            panel.addView(status, new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT));

            LinearLayout row = new LinearLayout(activity);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(0, dp(activity, 5), 0, 0);

            input = new EditText(activity);
            input.setSingleLine(true);
            input.setHint("Queue without interrupting...");
            input.setTextColor(Color.WHITE);
            input.setHintTextColor(Color.LTGRAY);
            input.setImeOptions(EditorInfo.IME_ACTION_SEND);
            input.setContentDescription("Queue another Home Center message without interrupting current work");
            row.addView(input, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

            queueButton = new Button(activity);
            queueButton.setText("Queue");
            queueButton.setAllCaps(false);
            queueButton.setContentDescription("Queue message");
            LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT);
            buttonParams.setMargins(dp(activity, 8), 0, 0, 0);
            row.addView(queueButton, buttonParams);
            panel.addView(row, new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT));

            queueButton.setOnClickListener(v -> enqueueFromPanel());
            input.setOnEditorActionListener((v, actionId, event) -> {
                boolean send = actionId == EditorInfo.IME_ACTION_SEND
                        || (event != null && event.getAction() == KeyEvent.ACTION_DOWN
                        && event.getKeyCode() == KeyEvent.KEYCODE_ENTER);
                if (!send) return false;
                enqueueFromPanel();
                return true;
            });

            FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.WRAP_CONTENT,
                    Gravity.BOTTOM);
            params.setMargins(dp(activity, 8), dp(activity, 8), dp(activity, 8), dp(activity, 8));
            host.addView(panel, params);
        }

        private void removePanel() {
            if (host != null && panel != null) host.removeView(panel);
            host = null;
            panel = null;
            status = null;
            input = null;
            queueButton = null;
        }

        private void enqueueFromPanel() {
            if (active == null || input == null) return;
            String exact = input.getText() == null ? "" : input.getText().toString();
            if (exact.trim().isEmpty()) {
                Toast.makeText(active, "Type a queued message first.", Toast.LENGTH_SHORT).show();
                return;
            }
            OperatorIngressQueue.Item item = ingressQueue.enqueue(
                    exact,
                    currentConversationId(),
                    "busy_turn_interrupt");
            if (item == null) {
                Toast.makeText(active, "Queue is full. Nothing was dropped.", Toast.LENGTH_LONG).show();
                return;
            }
            input.setText("");
            Toast.makeText(active, "Queued. Current work continues.", Toast.LENGTH_SHORT).show();
            refreshStatus(true, hasBarrier(), ingressQueue.size());
        }

        private void tick() throws Exception {
            if (active == null || panel == null || !seamResolved) return;
            boolean busy = busyField.getBoolean(active);
            boolean barrier = hasBarrier();
            int queued = ingressQueue.size();
            boolean shouldShow = busy || barrier || queued > 0;
            panel.setVisibility(shouldShow ? View.VISIBLE : View.GONE);
            if (!shouldShow) return;

            refreshStatus(busy, barrier, queued);
            if (busy || barrier || queued <= 0) return;

            OperatorIngressQueue.Item head = ingressQueue.snapshot().get(0);
            String currentConversation = currentConversationId();
            if (!head.conversationId.isEmpty()
                    && !currentConversation.isEmpty()
                    && !head.conversationId.equals(currentConversation)) {
                status.setText("Queued " + queued + " for another conversation. Return there to continue.");
                status.setContentDescription(status.getText());
                return;
            }

            OperatorIngressQueue.Item dispatch = ingressQueue.beginDispatch();
            if (dispatch == null) return;
            try {
                submitMessageMethod.invoke(active, dispatch.text, false);
                ingressQueue.completeDispatch(dispatch.id);
                android.util.Log.i("HomeCenterQueue", "dispatched queued item " + dispatch.id);
            } catch (Exception ex) {
                ingressQueue.retryInflight(dispatch.id);
                android.util.Log.e("HomeCenterQueue", "queued dispatch failed; item restored", ex);
                Toast.makeText(active, "Queued message preserved after dispatch failure.", Toast.LENGTH_LONG).show();
            }
        }

        private boolean hasBarrier() {
            if (active == null || !seamResolved) return false;
            try {
                Object pendingConfirmation = pendingConfirmationField.get(active);
                String pendingReconnect = String.valueOf(pendingReconnectField.get(active));
                return pendingConfirmation != null
                        || (pendingReconnect != null
                        && !"null".equals(pendingReconnect)
                        && !pendingReconnect.trim().isEmpty());
            } catch (Exception ex) {
                return true;
            }
        }

        private String currentConversationId() {
            if (active == null || !seamResolved) return "";
            try {
                Object value = activeConversationField.get(active);
                return value == null ? "" : String.valueOf(value).trim();
            } catch (Exception ex) {
                return "";
            }
        }

        private void refreshStatus(boolean busy, boolean barrier, int queued) {
            if (status == null) return;
            String text;
            if (busy) {
                text = queued > 0
                        ? "Current work continues • queued " + queued
                        : "Current work continues • queue is open";
            } else if (barrier) {
                text = queued > 0
                        ? "Waiting at the current confirmation gate • queued " + queued
                        : "Waiting at the current confirmation gate • queue is open";
            } else if (queued > 0) {
                text = "Queued " + queued + " • dispatching the next turn in order";
            } else {
                text = "Queue is open";
            }
            status.setText(text);
            status.setContentDescription(text);
        }

        private int dp(Activity activity, int value) {
            float density = activity.getResources().getDisplayMetrics().density;
            return Math.max(1, Math.round(value * density));
        }
    }
}