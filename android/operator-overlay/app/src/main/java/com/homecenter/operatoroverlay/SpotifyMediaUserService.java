package com.homecenter.operatoroverlay;

import android.content.Context;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.net.Uri;
import android.os.Bundle;
import android.os.SystemClock;
import android.system.Os;

import org.json.JSONObject;

import java.util.List;
import java.util.Locale;

/**
 * Shell/root-side Shizuku UserService for the exact Spotify media session.
 *
 * This class intentionally exposes no shell, Activity launch, generic media key,
 * package mutation, screen automation, or credential capability.
 */
public final class SpotifyMediaUserService extends ISpotifyMediaControl.Stub {
    static final String TARGET_PACKAGE = "com.spotify.music";
    static final String BACKEND = "shizuku-user-service";
    private static final int VERIFY_SETTLE_MS = 450;

    private final Context context;

    /** Required by Shizuku; v13 normally prefers the Context constructor. */
    public SpotifyMediaUserService() {
        this.context = null;
    }

    /** Context constructor supported by Shizuku API v13. */
    public SpotifyMediaUserService(Context context) {
        this.context = context;
    }

    @Override
    public String probe() {
        return guarded("probe", "", false);
    }

    @Override
    public String status() {
        return guarded("status", "", false);
    }

    @Override
    public String execute(String action, String argument) {
        return guarded(action, argument, true);
    }

    private String guarded(String action, String argument, boolean mutate) {
        try {
            return executeInternal(action, argument, mutate).toString();
        } catch (SecurityException error) {
            return failure(
                    "SPOTIFY_SESSION_AUTHORITY_UNAVAILABLE",
                    error.getClass().getSimpleName() + ": " + safeMessage(error)).toString();
        } catch (Throwable error) {
            return failure(
                    "SPOTIFY_MEDIA_CONTROL_FAILED",
                    error.getClass().getSimpleName() + ": " + safeMessage(error)).toString();
        }
    }

    private JSONObject executeInternal(String action, String argument, boolean mutate)
            throws Exception {
        String normalized = String.valueOf(action == null ? "" : action)
                .trim().toLowerCase(Locale.ROOT);
        if (!isSupported(normalized, mutate)) {
            return failure("SPOTIFY_ACTION_UNSUPPORTED", normalized);
        }

        SessionLookup lookup = lookupSpotifySession();
        JSONObject receipt = baseReceipt(normalized);
        receipt.put("mediaSessionAuthority", lookup.authority);
        receipt.put("activeSessionCount", lookup.activeSessionCount);
        receipt.put("spotifySessionPresent", lookup.controller != null);
        receipt.put("authorityError", lookup.authorityError);
        JSONObject before = sessionState(lookup.controller);
        receipt.put("before", before);

        if (!lookup.authority) {
            receipt.put("ok", false);
            receipt.put("verified", false);
            receipt.put("error", "SPOTIFY_SESSION_AUTHORITY_UNAVAILABLE");
            return receipt;
        }
        if (lookup.controller == null) {
            receipt.put("ok", false);
            receipt.put("verified", false);
            receipt.put("error", "SPOTIFY_SESSION_ABSENT");
            return receipt;
        }
        if (!mutate || normalized.equals("probe") || normalized.equals("status")) {
            receipt.put("ok", true);
            receipt.put("verified", true);
            receipt.put("after", before);
            return receipt;
        }

        MediaController.TransportControls controls = lookup.controller.getTransportControls();
        switch (normalized) {
            case "play":
                controls.play();
                break;
            case "pause":
                controls.pause();
                break;
            case "play_pause":
                if (isPlaying(before.optInt("playbackState", PlaybackState.STATE_NONE))) {
                    controls.pause();
                } else {
                    controls.play();
                }
                break;
            case "next":
                controls.skipToNext();
                break;
            case "previous":
                controls.skipToPrevious();
                break;
            case "stop":
                controls.stop();
                break;
            case "play_context":
                String uri = String.valueOf(argument == null ? "" : argument).trim();
                if (!validPlaylistUri(uri)) {
                    receipt.put("ok", false);
                    receipt.put("verified", false);
                    receipt.put("error", "SPOTIFY_CONTEXT_URI_REJECTED");
                    receipt.put("argumentAccepted", false);
                    return receipt;
                }
                controls.playFromUri(Uri.parse(uri), Bundle.EMPTY);
                receipt.put("argumentAccepted", true);
                receipt.put("contextUri", uri);
                break;
            default:
                return failure("SPOTIFY_ACTION_UNSUPPORTED", normalized);
        }

        SystemClock.sleep(VERIFY_SETTLE_MS);
        JSONObject after = sessionState(lookup.controller);
        boolean verified = verifies(normalized, before, after);
        receipt.put("commandAccepted", true);
        receipt.put("verified", verified);
        receipt.put("ok", verified);
        receipt.put("after", after);
        if (!verified) receipt.put("error", "SPOTIFY_COMMAND_UNVERIFIED");
        return receipt;
    }

    private SessionLookup lookupSpotifySession() {
        if (context == null) {
            return new SessionLookup(false, 0, null, "user_service_context_unavailable");
        }
        MediaSessionManager manager =
                (MediaSessionManager) context.getSystemService(Context.MEDIA_SESSION_SERVICE);
        if (manager == null) {
            return new SessionLookup(false, 0, null, "media_session_manager_unavailable");
        }
        try {
            List<MediaController> controllers = manager.getActiveSessions(null);
            MediaController spotify = null;
            for (MediaController controller : controllers) {
                if (TARGET_PACKAGE.equals(controller.getPackageName())) {
                    spotify = controller;
                    break;
                }
            }
            return new SessionLookup(true, controllers.size(), spotify, "");
        } catch (SecurityException error) {
            return new SessionLookup(
                    false,
                    0,
                    null,
                    error.getClass().getSimpleName() + ": " + safeMessage(error));
        }
    }

    private static JSONObject sessionState(MediaController controller) throws Exception {
        JSONObject state = new JSONObject();
        state.put("targetPackage", TARGET_PACKAGE);
        if (controller == null) {
            state.put("present", false);
            state.put("playbackState", PlaybackState.STATE_NONE);
            state.put("playing", false);
            state.put("title", "");
            state.put("artist", "");
            state.put("album", "");
            state.put("mediaId", "");
            state.put("mediaUri", "");
            state.put("positionMs", 0L);
            state.put("actions", 0L);
            return state;
        }

        state.put("present", true);
        PlaybackState playback = controller.getPlaybackState();
        int playbackState = playback == null
                ? PlaybackState.STATE_NONE : playback.getState();
        state.put("playbackState", playbackState);
        state.put("playing", isPlaying(playbackState));
        state.put("positionMs", playback == null ? 0L : playback.getPosition());
        state.put("actions", playback == null ? 0L : playback.getActions());

        MediaMetadata metadata = controller.getMetadata();
        state.put("title", metadataText(metadata, MediaMetadata.METADATA_KEY_TITLE));
        state.put("artist", metadataText(metadata, MediaMetadata.METADATA_KEY_ARTIST));
        state.put("album", metadataText(metadata, MediaMetadata.METADATA_KEY_ALBUM));
        state.put("mediaId", metadataText(metadata, MediaMetadata.METADATA_KEY_MEDIA_ID));
        state.put("mediaUri", metadataText(metadata, MediaMetadata.METADATA_KEY_MEDIA_URI));
        return state;
    }

    private static String metadataText(MediaMetadata metadata, String key) {
        if (metadata == null) return "";
        CharSequence value = metadata.getText(key);
        return value == null ? "" : value.toString();
    }

    private static boolean verifies(String action, JSONObject before, JSONObject after) {
        int afterState = after.optInt("playbackState", PlaybackState.STATE_NONE);
        switch (action) {
            case "play":
            case "play_context":
                return isPlaying(afterState);
            case "pause":
                return afterState == PlaybackState.STATE_PAUSED
                        || afterState == PlaybackState.STATE_STOPPED;
            case "play_pause":
                return before.optInt("playbackState", PlaybackState.STATE_NONE) != afterState;
            case "stop":
                return afterState == PlaybackState.STATE_STOPPED
                        || afterState == PlaybackState.STATE_PAUSED;
            case "next":
            case "previous":
                return !identity(before).equals(identity(after));
            default:
                return false;
        }
    }

    private static String identity(JSONObject state) {
        String id = state.optString("mediaId", "");
        if (!id.isEmpty()) return id;
        String uri = state.optString("mediaUri", "");
        if (!uri.isEmpty()) return uri;
        return state.optString("artist", "") + "\n" + state.optString("title", "");
    }

    private static boolean isPlaying(int state) {
        return state == PlaybackState.STATE_PLAYING
                || state == PlaybackState.STATE_BUFFERING
                || state == PlaybackState.STATE_CONNECTING;
    }

    private static boolean validPlaylistUri(String uri) {
        if (!uri.startsWith("spotify:playlist:")) return false;
        String id = uri.substring("spotify:playlist:".length());
        return id.matches("[A-Za-z0-9]{10,80}");
    }

    private static boolean isSupported(String action, boolean mutate) {
        if (!mutate) return action.equals("probe") || action.equals("status");
        return action.equals("play")
                || action.equals("pause")
                || action.equals("play_pause")
                || action.equals("next")
                || action.equals("previous")
                || action.equals("stop")
                || action.equals("play_context");
    }

    private static JSONObject baseReceipt(String action) throws Exception {
        JSONObject receipt = new JSONObject();
        receipt.put("schema", "home-center.spotify-media-receipt.v1");
        receipt.put("backend", BACKEND);
        receipt.put("action", action);
        receipt.put("targetPackage", TARGET_PACKAGE);
        receipt.put("uid", Os.getuid());
        receipt.put("activityLaunchUsed", false);
        receipt.put("genericMediaKeyUsed", false);
        receipt.put("screenAutomationUsed", false);
        receipt.put("foregroundTouched", false);
        receipt.put("observedAtMs", System.currentTimeMillis());
        return receipt;
    }

    private static JSONObject failure(String code, String detail) {
        try {
            JSONObject receipt = baseReceipt("");
            receipt.put("ok", false);
            receipt.put("verified", false);
            receipt.put("error", code);
            receipt.put("detail", detail == null ? "" : detail);
            return receipt;
        } catch (Exception ignored) {
            return new JSONObject();
        }
    }

    private static String safeMessage(Throwable error) {
        String message = error.getMessage();
        if (message == null) return "";
        return message.substring(0, Math.min(1000, message.length()));
    }

    /** Reserved Shizuku UserService destroy transaction. */
    @Override
    public void destroy() {
        System.exit(0);
    }

    private static final class SessionLookup {
        final boolean authority;
        final int activeSessionCount;
        final MediaController controller;
        final String authorityError;

        SessionLookup(boolean authority, int activeSessionCount,
                      MediaController controller, String authorityError) {
            this.authority = authority;
            this.activeSessionCount = activeSessionCount;
            this.controller = controller;
            this.authorityError = authorityError;
        }
    }
}
