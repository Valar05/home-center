package com.homecenter.operatoroverlay;

import android.content.ComponentName;
import android.content.ServiceConnection;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import org.json.JSONObject;

import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import rikka.shizuku.Shizuku;

/** Bounded client for the Spotify-only Shizuku UserService. */
public final class SpotifyShizukuClient implements AutoCloseable {
    public static final String CLIENT_SCHEMA = "home-center.spotify-shizuku-client.v1";

    private static final Set<String> ACTIONS = Set.of(
            "probe", "status", "play", "pause", "play_pause", "next", "previous",
            "stop", "play_context");

    public interface ReceiptCallback {
        void onReceipt(long requestId, String receiptJson);
    }

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final AtomicBoolean binding = new AtomicBoolean(false);
    private final AtomicBoolean closed = new AtomicBoolean(false);
    private final Shizuku.UserServiceArgs userServiceArgs = new Shizuku.UserServiceArgs(
            new ComponentName(BuildConfig.APPLICATION_ID, SpotifyMediaUserService.class.getName()))
            .daemon(true)
            .processNameSuffix("spotify")
            .version(BuildConfig.VERSION_CODE);

    private volatile ISpotifyMediaControl service;

    private final ServiceConnection serviceConnection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder binder) {
            service = ISpotifyMediaControl.Stub.asInterface(binder);
            binding.set(false);
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            service = null;
            binding.set(false);
        }

        @Override
        public void onBindingDied(ComponentName name) {
            service = null;
            binding.set(false);
        }

        @Override
        public void onNullBinding(ComponentName name) {
            service = null;
            binding.set(false);
        }
    };

    private final Shizuku.OnBinderReceivedListener binderReceivedListener = this::startBinding;
    private final Shizuku.OnBinderDeadListener binderDeadListener = () -> {
        service = null;
        binding.set(false);
    };
    private final Shizuku.OnRequestPermissionResultListener permissionResultListener =
            (requestCode, grantResult) -> {
                if (grantResult == PackageManager.PERMISSION_GRANTED) startBinding();
            };

    public SpotifyShizukuClient() {
        Shizuku.addBinderReceivedListenerSticky(binderReceivedListener);
        Shizuku.addBinderDeadListener(binderDeadListener);
        Shizuku.addRequestPermissionResultListener(permissionResultListener);
    }

    public void execute(long requestId, String action, String argument, ReceiptCallback callback) {
        if (callback == null) throw new IllegalArgumentException("callback is required");
        if (closed.get()) {
            deliver(requestId, failure("SHIZUKU_CLIENT_CLOSED", ""), callback);
            return;
        }
        executor.execute(() -> executeOnBackground(requestId, action, argument, callback));
    }

    private void executeOnBackground(
            long requestId, String action, String argument, ReceiptCallback callback) {
        String normalized = action == null ? "" : action.trim().toLowerCase(Locale.ROOT);
        if (!ACTIONS.contains(normalized)) {
            deliver(requestId, failure("SPOTIFY_ACTION_UNSUPPORTED", normalized), callback);
            return;
        }
        if (!Shizuku.pingBinder()) {
            startBinding();
            deliver(requestId, failure("SHIZUKU_BINDER_UNAVAILABLE", ""), callback);
            return;
        }
        if (Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED) {
            deliver(requestId, failure("SHIZUKU_PERMISSION_REQUIRED", ""), callback);
            return;
        }

        ISpotifyMediaControl current = service;
        if (current == null || !current.asBinder().isBinderAlive()) {
            service = null;
            startBinding();
            deliver(requestId, failure("SHIZUKU_USER_SERVICE_UNAVAILABLE", ""), callback);
            return;
        }

        try {
            String receipt;
            if ("probe".equals(normalized)) {
                receipt = current.probe();
            } else if ("status".equals(normalized)) {
                receipt = current.status();
            } else {
                receipt = current.execute(normalized, argument == null ? "" : argument);
            }
            deliver(requestId, withClientIdentity(receipt, requestId), callback);
        } catch (Throwable error) {
            service = null;
            deliver(requestId, failure(
                    "SHIZUKU_BINDER_CALL_FAILED", error.getClass().getSimpleName()), callback);
        }
    }

    private void startBinding() {
        if (closed.get() || !Shizuku.pingBinder()) return;
        if (Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED) return;
        if (!binding.compareAndSet(false, true)) return;
        try {
            Shizuku.bindUserService(userServiceArgs, serviceConnection);
        } catch (Throwable error) {
            binding.set(false);
        }
    }

    private void deliver(long requestId, JSONObject receipt, ReceiptCallback callback) {
        try {
            receipt.put("requestId", requestId);
            receipt.put("clientSchema", CLIENT_SCHEMA);
        } catch (Exception ignored) {
            // JSONObject accepts these values; retained only to keep delivery fail-safe.
        }
        String json = receipt.toString();
        mainHandler.post(() -> callback.onReceipt(requestId, json));
    }

    private void deliver(long requestId, String receipt, ReceiptCallback callback) {
        mainHandler.post(() -> callback.onReceipt(requestId, receipt));
    }

    private static String withClientIdentity(String rawReceipt, long requestId) {
        try {
            JSONObject receipt = new JSONObject(rawReceipt == null ? "{}" : rawReceipt);
            receipt.put("requestId", requestId);
            receipt.put("clientSchema", CLIENT_SCHEMA);
            return receipt.toString();
        } catch (Exception error) {
            return failure("SPOTIFY_RECEIPT_INVALID", error.getClass().getSimpleName(), requestId)
                    .toString();
        }
    }

    private static JSONObject failure(String code, String detail) {
        return failure(code, detail, null);
    }

    private static JSONObject failure(String code, String detail, Long requestId) {
        JSONObject receipt = new JSONObject();
        try {
            receipt.put("ok", false);
            receipt.put("verified", false);
            receipt.put("error", code);
            receipt.put("detail", detail == null ? "" : detail);
            receipt.put("clientSchema", CLIENT_SCHEMA);
            if (requestId != null) receipt.put("requestId", requestId);
        } catch (Exception ignored) {
            // Constants and primitive values cannot fail normal JSONObject insertion.
        }
        return receipt;
    }

    @Override
    public void close() {
        if (!closed.compareAndSet(false, true)) return;
        Shizuku.removeBinderReceivedListener(binderReceivedListener);
        Shizuku.removeBinderDeadListener(binderDeadListener);
        Shizuku.removeRequestPermissionResultListener(permissionResultListener);
        if (binding.get() || service != null) {
            try {
                Shizuku.unbindUserService(userServiceArgs, serviceConnection, true);
            } catch (Throwable ignored) {
                // Cleanup remains idempotent if Shizuku has already disconnected.
            }
        }
        service = null;
        binding.set(false);
        executor.shutdownNow();
    }
}
