package com.homecenter.operatoroverlay;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Base64;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;

public class OperatorStateProvider extends ContentProvider {
    private static final int STATE_SCHEMA_VERSION = 2;
    private static final String METHOD_SPOTIFY_CONTROL = "spotify_control";
    private static final String METHOD_RESTORE_MIGRATION_STATE = "restore_migration_state";

    private static final Set<String> MIGRATION_RESTORABLE_KEYS = new HashSet<>(Arrays.asList(
            OperatorState.KEY_MUTED,
            OperatorState.KEY_LAST_HEARTBEAT_MS,
            OperatorState.KEY_LAST_UPDATE_MS,
            OperatorState.KEY_LATEST_SOURCE,
            OperatorState.KEY_PANEL_COLLAPSED,
            OperatorState.KEY_OVERLAY_HIDDEN,
            OperatorState.KEY_OVERLAY_X,
            OperatorState.KEY_OVERLAY_Y));

    private static final Set<String> MIGRATION_GUARD_KEYS = new HashSet<>(Arrays.asList(
            OperatorState.KEY_CONTROL_ENABLED,
            OperatorState.KEY_SCREEN_ACTIVE_UNTIL_MS,
            OperatorState.KEY_SCREEN_YIELD_UNTIL_MS));

    private static final String[] COLUMNS = new String[]{
            "state_schema_version",
            "feature_quit_kit_dial_v1",
            "control_enabled",
            "muted",
            "last_heartbeat_ms",
            "last_update_ms",
            "latest_source",
            "screen_active_until_ms",
            "screen_yield_until_ms",
            "panel_collapsed",
            "overlay_hidden",
            "overlay_x",
            "overlay_y",
            "adam_request_id",
            "adam_request_mode",
            "adam_request_payload_b64",
            "spotify_request_id",
            "spotify_receipt_b64",
            "spotify_summary",
            "spotify_updated_ms"
    };

    private static final Set<String> SPOTIFY_COMMANDS = new HashSet<>(Arrays.asList(
            "probe", "status", "play", "pause", "play_pause", "next", "previous", "stop",
            "play_context"));

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        MatrixCursor cursor = new MatrixCursor(COLUMNS);
        cursor.addRow(new Object[]{
                STATE_SCHEMA_VERSION,
                1,
                OperatorState.controlEnabled(getContext()) ? 1 : 0,
                OperatorState.muted(getContext()) ? 1 : 0,
                OperatorState.lastHeartbeatMs(getContext()),
                OperatorState.lastUpdateMs(getContext()),
                OperatorState.latestSource(getContext()),
                OperatorState.screenActiveUntilMs(getContext()),
                OperatorState.screenYieldUntilMs(getContext()),
                OperatorState.panelCollapsed(getContext()) ? 1 : 0,
                OperatorState.overlayHidden(getContext()) ? 1 : 0,
                OperatorState.overlayX(getContext()),
                OperatorState.overlayY(getContext()),
                OperatorState.adamRequestId(getContext()),
                OperatorState.adamRequestMode(getContext()),
                OperatorState.adamRequestPayloadB64(getContext()),
                OperatorState.spotifyRequestId(getContext()),
                OperatorState.spotifyReceiptB64(getContext()),
                OperatorState.spotifySummary(getContext()),
                OperatorState.spotifyUpdatedMs(getContext())
        });
        return cursor;
    }

    @Override
    public Bundle call(String method, String arg, Bundle extras) {
        if (METHOD_RESTORE_MIGRATION_STATE.equals(method)) {
            return restoreMigrationState(Objects.requireNonNull(getContext()), extras);
        }
        if (!METHOD_SPOTIFY_CONTROL.equals(method)) {
            return super.call(method, arg, extras);
        }

        Context context = Objects.requireNonNull(getContext());
        context.enforceCallingOrSelfPermission(
                android.Manifest.permission.DUMP,
                "spotify_control requires android.permission.DUMP");

        String command = arg == null ? "" : arg.toLowerCase(Locale.ROOT);
        long requestId = extras == null ? 0L : extras.getLong("request_id", 0L);
        String argumentB64 = extras == null ? "" : extras.getString("argument_b64", "");
        String argument = decodeSpotifyArgument(argumentB64);
        boolean accepted = SPOTIFY_COMMANDS.contains(command) && argument != null;

        if (accepted) {
            Intent intent = new Intent(context, OperatorOverlayService.class)
                    .setAction(OperatorOverlayService.ACTION_SPOTIFY_COMMAND)
                    .putExtra(OperatorOverlayService.EXTRA_SPOTIFY_COMMAND, command)
                    .putExtra(OperatorOverlayService.EXTRA_SPOTIFY_ARGUMENT, argument)
                    .putExtra(OperatorOverlayService.EXTRA_SPOTIFY_REQUEST_ID, requestId);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
        }

        Bundle result = new Bundle();
        result.putBoolean("accepted", accepted);
        result.putString("command", command);
        result.putLong("request_id", requestId);
        result.putString("target_package", "com.spotify.music");
        result.putBoolean("activity_launch_used", false);
        result.putBoolean("generic_media_key_used", false);
        result.putBoolean("screen_automation_used", false);
        return result;
    }

    private static Bundle restoreMigrationState(Context context, Bundle extras) {
        context.enforceCallingPermission(
                android.Manifest.permission.DUMP,
                "restore_migration_state requires android.permission.DUMP");
        validateMigrationExtras(extras);
        if (!OperatorState.restoreMigrationState(context, extras)) {
            throw new IllegalStateException("migration state commit failed");
        }

        Bundle result = new Bundle();
        result.putBoolean("restored", true);
        result.putBoolean("control_enabled", false);
        return result;
    }

    private static void validateMigrationExtras(Bundle extras) {
        if (extras == null) return;
        for (String key : extras.keySet()) {
            if (!MIGRATION_RESTORABLE_KEYS.contains(key) && !MIGRATION_GUARD_KEYS.contains(key)) {
                throw new IllegalArgumentException("unsupported migration field: " + key);
            }
        }

        if (extras.containsKey(OperatorState.KEY_CONTROL_ENABLED)
                && !Boolean.FALSE.equals(extras.get(OperatorState.KEY_CONTROL_ENABLED))) {
            throw new IllegalArgumentException("migration cannot enable control");
        }
        rejectNonzeroLease(extras, OperatorState.KEY_SCREEN_ACTIVE_UNTIL_MS);
        rejectNonzeroLease(extras, OperatorState.KEY_SCREEN_YIELD_UNTIL_MS);
    }

    private static void rejectNonzeroLease(Bundle extras, String key) {
        if (!extras.containsKey(key)) return;
        Object value = extras.get(key);
        if (!(value instanceof Long) || ((Long) value) != 0L) {
            throw new IllegalArgumentException("migration cannot restore screen leases");
        }
    }

    private static String decodeSpotifyArgument(String encoded) {
        if (encoded == null || encoded.indexOf('=') >= 0
                || !encoded.matches("[A-Za-z0-9_-]*") || encoded.length() % 4 == 1) {
            return null;
        }
        try {
            byte[] decoded = Base64.decode(encoded, Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
            String value = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(decoded))
                    .toString();
            return value.length() <= 512 ? value : null;
        } catch (IllegalArgumentException | CharacterCodingException e) {
            return null;
        }
    }

    @Override
    public String getType(Uri uri) {
        return "vnd.android.cursor.item/vnd.homecenter.operator-state";
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException("read only");
    }
}
