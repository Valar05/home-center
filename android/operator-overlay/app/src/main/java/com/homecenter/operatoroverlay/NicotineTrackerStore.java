package com.homecenter.operatoroverlay;

import android.content.Context;
import android.os.SystemClock;

import java.io.IOException;
import java.util.TimeZone;

/**
 * The only production write aperture for tracker events.
 *
 * Callers must be app-local UI code. No provider, receiver, daemon, model, or
 * exported component is given this method or its app-private path.
 */
final class NicotineTrackerStore {
    private NicotineTrackerStore() {}

    static String newLocalIdempotencyKey() {
        return NicotineTrackerLedger.newIdempotencyKey();
    }

    static NicotineTrackerLedger.SaveResult saveFromLocalReview(
            Context context,
            NicotineTrackerContract.Draft draft,
            String note,
            String idempotencyKey) throws IOException {
        if (context == null) throw new IllegalArgumentException("app-local context required");
        return NicotineTrackerLedger.save(
                context.getFilesDir(),
                draft,
                note,
                idempotencyKey,
                new NicotineTrackerLedger.Clock() {
                    @Override
                    public long wallTimeMillis() {
                        return System.currentTimeMillis();
                    }

                    @Override
                    public long monotonicNanos() {
                        return SystemClock.elapsedRealtimeNanos();
                    }

                    @Override
                    public String zoneId() {
                        return TimeZone.getDefault().getID();
                    }
                });
    }
}
