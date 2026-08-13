package com.homecenter.operatoroverlay;

import android.content.Context;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.net.Uri;
import android.os.Bundle;
import android.os.Looper;
import android.os.SystemClock;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Exact-package Spotify media-session bridge executed through Shizuku/rish.
 *
 * This class is intentionally not an Android Activity or Service. The Termux
 * controller loads the reviewed installed overlay APK through app_process while
 * rish supplies Android's shell identity. It never launches Spotify or any
 * other foreground UI. Missing Spotify session or authority fails closed.
 */
public final class SpotifyMediaBridge {
    private static final String SPOTIFY_PACKAGE = "com.spotify.music";
    private static final Set<String> ACTIONS = new HashSet<>(Arrays.asList(
            "status", "play", "pause", "toggle", "next", "previous", "stop", "play-uri"));

    private SpotifyMediaBridge() {}

    public static void main(String[] args) {
        int exit = 1;
        try {
            String action = args.length > 0 ? args[0].trim().toLowerCase() : "status";
            String uri = args.length > 1 ? args[1].trim() : "";
            if (!ACTIONS.contains(action)) {
                throw new BridgeException("UNSUPPORTED_ACTION", "Unsupported action: " + action);
            }
            if ("play-uri".equals(action) && !validPlaylistUri(uri)) {
                throw new BridgeException("INVALID_PLAYLIST_URI", "A validated Spotify playlist URI is required.");
            }

            Context context = createSystemContext();
            MediaSessionManager manager = context.getSystemService(MediaSessionManager.class);
            if (manager == null) {
                throw new BridgeException("MEDIA_SESSION_MANAGER_UNAVAILABLE", "MediaSessionManager is unavailable.");
            }

            List<MediaController> beforeControllers = manager.getActiveSessions(null);
            List<String> competitors = competingPlayers(beforeControllers);
            if (!competitors.isEmpty()) {
                throw new BridgeException(
                        "COMPETING_MEDIA_SESSION",
                        "Another package is actively playing: " + String.join(",", competitors));
            }
            MediaController before = selectSpotify(beforeControllers);
            if (before == null) {
                throw new BridgeException(
                        "SPOTIFY_SESSION_ABSENT",
                        "Spotify has no active Android media session; foreground launch is forbidden.");
            }

            String beforeJson = controllerJson(before);
            int beforeState = state(before);
            String beforeTitle = title(before);
            String beforeArtist = artist(before);
            long beforePosition = position(before);
            if (!"status".equals(action)) {
                MediaController.TransportControls controls = before.getTransportControls();
                switch (action) {
                    case "play":
                        controls.play();
                        break;
                    case "pause":
                        controls.pause();
                        break;
                    case "toggle":
                        if (state(before) == PlaybackState.STATE_PLAYING) controls.pause();
                        else controls.play();
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
                    case "play-uri":
                        controls.playFromUri(Uri.parse(uri), Bundle.EMPTY);
                        break;
                    default:
                        throw new BridgeException("UNSUPPORTED_ACTION", action);
                }
                SystemClock.sleep(action.equals("next") || action.equals("previous") ? 1200L : 850L);
            }

            List<MediaController> afterControllers = manager.getActiveSessions(null);
            MediaController after = selectSpotify(afterControllers);
            if (after == null) {
                throw new BridgeException("SPOTIFY_COMMAND_UNVERIFIED", "Spotify session disappeared after command.");
            }
            List<String> afterCompetitors = competingPlayers(afterControllers);
            if (!afterCompetitors.isEmpty()) {
                throw new BridgeException(
                        "SPOTIFY_COMMAND_UNVERIFIED",
                        "A competing package became active after command: " + String.join(",", afterCompetitors));
            }

            int afterState = state(after);
            boolean trackChanged = trackChanged(beforeTitle, beforeArtist, after);
            boolean positionReset = position(after) + 1000L < beforePosition;
            boolean postcondition = postcondition(
                    action, beforeState, trackChanged, positionReset, afterState);
            String result = "{"
                    + "\"ok\":" + postcondition + ","
                    + "\"schema\":\"home-center.spotify-media-bridge.v1\","
                    + "\"action\":" + quote(action) + ","
                    + "\"targetPackage\":\"" + SPOTIFY_PACKAGE + "\","
                    + "\"requestedUri\":" + quote(uri) + ","
                    + "\"trackChanged\":" + trackChanged + ","
                    + "\"positionReset\":" + positionReset + ","
                    + "\"foregroundLaunchUsed\":false,"
                    + "\"competingPackages\":[],"
                    + "\"before\":" + beforeJson + ","
                    + "\"after\":" + controllerJson(after)
                    + "}";
            System.out.println(result);
            exit = postcondition ? 0 : 5;
        } catch (BridgeException error) {
            System.out.println(errorJson(error.code, error.getMessage()));
            exit = 4;
        } catch (SecurityException error) {
            System.out.println(errorJson("SPOTIFY_SESSION_AUTHORITY_UNAVAILABLE", error.toString()));
            exit = 6;
        } catch (Throwable error) {
            System.out.println(errorJson("SPOTIFY_MEDIA_BRIDGE_FAILED", error.toString()));
            exit = 7;
        } finally {
            System.out.flush();
            System.err.flush();
            System.exit(exit);
        }
    }

    private static Context createSystemContext() throws Exception {
        if (Looper.myLooper() == null) {
            Looper.prepareMainLooper();
        }
        Class<?> activityThread = Class.forName("android.app.ActivityThread");
        Method systemMain = activityThread.getDeclaredMethod("systemMain");
        systemMain.setAccessible(true);
        Object thread = systemMain.invoke(null);
        try {
            Method currentSystemContext = activityThread.getDeclaredMethod("currentSystemContext");
            currentSystemContext.setAccessible(true);
            Object context = currentSystemContext.invoke(null);
            if (context instanceof Context) return (Context) context;
        } catch (NoSuchMethodException ignored) {
            // Android versions before currentSystemContext().
        }
        Method getSystemContext = activityThread.getDeclaredMethod("getSystemContext");
        getSystemContext.setAccessible(true);
        return (Context) getSystemContext.invoke(thread);
    }

    private static MediaController selectSpotify(List<MediaController> controllers) {
        MediaController fallback = null;
        for (MediaController controller : controllers) {
            if (!SPOTIFY_PACKAGE.equals(controller.getPackageName())) continue;
            if (fallback == null) fallback = controller;
            int state = state(controller);
            if (state == PlaybackState.STATE_PLAYING
                    || state == PlaybackState.STATE_BUFFERING
                    || state == PlaybackState.STATE_CONNECTING) {
                return controller;
            }
        }
        return fallback;
    }

    private static List<String> competingPlayers(List<MediaController> controllers) {
        List<String> packages = new ArrayList<>();
        for (MediaController controller : controllers) {
            String packageName = controller.getPackageName();
            if (SPOTIFY_PACKAGE.equals(packageName)) continue;
            int state = state(controller);
            if (state == PlaybackState.STATE_PLAYING
                    || state == PlaybackState.STATE_BUFFERING
                    || state == PlaybackState.STATE_CONNECTING) {
                if (!packages.contains(packageName)) packages.add(packageName);
            }
        }
        return packages;
    }

    private static int state(MediaController controller) {
        PlaybackState value = controller.getPlaybackState();
        return value == null ? PlaybackState.STATE_NONE : value.getState();
    }

    private static boolean postcondition(
            String action,
            int beforeState,
            boolean trackChanged,
            boolean positionReset,
            int afterState) {
        switch (action) {
            case "status":
                return true;
            case "play":
            case "play-uri":
                return afterState == PlaybackState.STATE_PLAYING
                        || afterState == PlaybackState.STATE_BUFFERING
                        || afterState == PlaybackState.STATE_CONNECTING);
            case "pause":
                return afterState == PlaybackState.STATE_PAUSED;
            case "stop":
                return afterState == PlaybackState.STATE_STOPPED
                        || afterState == PlaybackState.STATE_PAUSED;
            case "toggle":
                return afterState != beforeState
                        && afterState != PlaybackState.STATE_ERROR
                       && afterState != PlaybackState.STATE_NONE;
            case "next":
                return trackChanged;
            case "previous":
                return trackChanged || positionReset;
            default:
                return false;
        }
    }

    private static String title(MediaController controller) {
        MediaMetadata metadata = controller.getMetadata();
        String value = metadata == null ? "" : metadata.getString(MediaMetadata.METADATA_KEY_TITLE);
        return value == null ? "" : value;
    }

    private static String artist(MediaController controller) {
        MediaMetadata metadata = controller.getMetadata();
        String value = metadata == null ? "" : metadata.getString(MediaMetadata.METADATA_KEY_ARTIST);
        return value == null ? "" : value;
    }

    private static long position(MediaController controller) {
        PlaybackState playback = controller.getPlaybackState();
        return playback == null ? 0L : playback.getPosition();
    }

    private static boolean trackChanged(
            String beforeTitle,
            String beforeArtist,
            MediaController after) {
        String afterTitle = title(after);
        String afterArtist = artist(after);
        if (afterTitle.isEmpty() && afterArtist.isEmpty()) return false;
        return !beforeTitle.equals(afterTitle) || !beforeArtist.equals(afterArtist);
    }

    private static String controllerJson(MediaController controller) {
        PlaybackState playback = controller.getPlaybackState();
        MediaMetadata metadata = controller.getMetadata();
        String title = metadata == null ? "" : metadata.getString(MediaMetadata.METADATA_KEY_TITLE);
        String artist = metadata == null ? "" : metadata.getString(MediaMetadata.METADATA_KEY_ARTIST);
        String album = metadata == null ? "" : metadata.getString(MediaMetadata.METADATA_KEY_ALBUM);
        long duration = metadata == null ? 0L : metadata.getLong(MediaMetadata.METADATA_KEY_DURATION);
        long position = playback == null ? 0L : playback.getPosition();
        long actions = playback == null ? 0L : playback.getActions();
        CharSequence queueTitle = controller.getQueueTitle();
        return "{"
                + "\"package\":" + quote(controller.getPackageName()) + ","
                + "\"state\":" + state(controller) + ","
                + "\"stateName\":" + quote(stateName(state(controller))) + ","
                + "\"title\":" + quote(title) + ","
                + "\"artist\":" + quote(artist) + ","
                + "\"album\":" + quote(album) + ","
                + "\"durationMs\":" + duration + ","
                + "\"positionMs\":" + position + ","
                + "\"actions\":" + actions + ","
                + "\"queueTitle\":" + quote(queueTitle == null ? "" : queueTitle.toString())
                + "}";
    }

    private static String stateName(int state) {
        switch (state) {
            case PlaybackState.STATE_STOPPED: return "stopped";
            case PlaybackState.STATE_PAUSED: return "paused";
            case PlaybackState.STATE_PLAYING: return "playing";
            case PlaybackState.STATE_FAST_FORWARDING: return "fast_forwarding";
            case PlaybackState.STATE_REWINDING: return "rewinding";
            case PlaybackState.STATE_BUFFERING: return "buffering";
            case PlaybackState.STATE_ERROR: return "error";
            case PlaybackState.STATE_CONNECTING: return "connecting";
            case PlaybackState.STATE_SKIPPING_TO_PREVIOUS: return "skipping_previous";
            case PlaybackState.STATE_SKIPPING_TO_NEXT: return "skipping_next";
            case PlaybackState.STATE_SKIPPING_TO_QUEUE_ITEM: return "skipping_queue_item";
            default: return "none";
        }
    }

    private static boolean validPlaylistUri(String value) {
        if (value == null || value.length() > 4096) return false;
        if (value.matches("spotify:playlist:[A-Za-z0-9]{10,64}")) return true;
        try {
            Uri uri = Uri.parse(value);
            if (!"https".equals(uri.getScheme())) return false;
            if (!("open.spotify.com".equals(uri.getHost()) || "www.spotify.com".equals(uri.getHost()))) {
                return false;
            }
            List<String> segments = uri.getPathSegments();
            return segments.size() >= 2
                    && "playlist".equals(segments.get(0))
                    && segments.get(1).matches("[A-Za-z0-9]{10,64}");
        } catch (Throwable ignored) {
            return false;
        }
    }

    private static String errorJson(String code, String detail) {
        return "{"
                + "\"ok\":false,"
                + "\"schema\":\"home-center.spotify-media-bridge.v1\","
                + "\"error\":" + quote(code) + ","
                + "\"detail\":" + quote(detail) + ","
                + "\"targetPackage\":\"" + SPOTIFY_PACKAGE + "\","
                + "\"foregroundLaunchUsed\":false"
                + "}";
    }

    private static String quote(String value) {
        if (value == null) return "\"\"";
        StringBuilder result = new StringBuilder(value.length() + 16);
        result.append('"');
        for (int index = 0; index < value.length(); index++) {
            char c = value.charAt(index);
            switch (c) {
                case '"': result.append("\\\""); break;
                case '\\': result.append("\\\\"); break;
                case '\b': result.append("\\b"); break;
                case '\f': result.append("\\f"); break;
                case '\n': result.append("\\n"); break;
                case '\r': result.append("\\r"); break;
                case '\t': result.append("\\t"); break;
                default:
                    if (c < 0x20) result.append(String.format("\\u%04x", (int) c));
                    else result.append(c);
            }
        }
        result.append('"');
        return result.toString();
    }

    private static final class BridgeException extends Exception {
        final String code;

        BridgeException(String code, String message) {
            super(message);
            this.code = code;
        }
    }
}
