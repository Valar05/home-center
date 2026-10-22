package com.homecenter.ritsucontrol;

import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/**
 * User-added system Quick Settings entry point. Android 14+ can dismiss even
 * ongoing FGS notifications; a tile keeps a deliberate, discoverable way
 * to reopen the control screen. This tile NEVER starts mic capture or TTS.
 */
public final class RitsuQuickTileService extends TileService {
    @Override public void onStartListening() {
        super.onStartListening();
        Tile tile = getQsTile();
        if (tile == null) return;
        tile.setLabel("Ritsu controls");
        tile.setState(Tile.STATE_ACTIVE); // available to open, NOT a live mic indicator
        tile.updateTile();
    }

    @Override public void onClick() {
        super.onClick();
        Intent open = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        if (Build.VERSION.SDK_INT >= 34) {
            PendingIntent intent = PendingIntent.getActivity(this, 101, open,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            startActivityAndCollapse(intent);
        } else {
            startActivityAndCollapse(open);
        }
    }
}
