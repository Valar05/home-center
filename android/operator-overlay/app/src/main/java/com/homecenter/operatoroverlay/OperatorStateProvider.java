package com.homecenter.operatoroverlay;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;

public class OperatorStateProvider extends ContentProvider {
    private static final String[] COLUMNS = new String[]{
            "control_enabled",
            "muted",
            "last_heartbeat_ms",
            "last_update_ms",
            "latest_source",
            "screen_active_until_ms",
            "screen_yield_until_ms",
            "panel_collapsed",
            "overlay_hidden"
    };

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        MatrixCursor cursor = new MatrixCursor(COLUMNS);
        cursor.addRow(new Object[]{
                OperatorState.controlEnabled(getContext()) ? 1 : 0,
                OperatorState.muted(getContext()) ? 1 : 0,
                OperatorState.lastHeartbeatMs(getContext()),
                OperatorState.lastUpdateMs(getContext()),
                OperatorState.latestSource(getContext()),
                OperatorState.screenActiveUntilMs(getContext()),
                OperatorState.screenYieldUntilMs(getContext()),
                OperatorState.panelCollapsed(getContext()) ? 1 : 0,
                OperatorState.overlayHidden(getContext()) ? 1 : 0
        });
        return cursor;
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
