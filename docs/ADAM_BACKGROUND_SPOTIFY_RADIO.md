# Adam Background Spotify Radio

Status: source implementation in progress; no phone deployment or playback claim.
Owner: Drew
Surface: existing Home Center / Adam Android overlay
Background control body: Shizuku UserService targeting `com.spotify.music`
Account plane: Spotify Web API for private playlist creation and playlist item maintenance only

## Mission

Make the existing Adam overlay a background Spotify radio widget and prompt surface. The widget controls the exact Spotify media session without launching Spotify, changing the foreground app, using screen automation, or dispatching untargeted media keys. Adam prompts create or revise one stable private playlist named `Adam Radio — Rolling`; a deterministic rolling state machine keeps a bounded unplayed tail.

## Non-negotiable exclusions

The Spotify lane must not use:

- `Intent.ACTION_VIEW` or another Spotify Activity/deep-link launch;
- `phone.open_uri`, `am start`, `monkey`, UIAutomator, taps, coordinates, or key injection;
- `AudioManager.dispatchMediaKeyEvent` or a generic media-button broadcast;
- a different player or TTS/media engine;
- a model running continuously in the background;
- repository or test evidence as a substitute for phone playback evidence.

If Shizuku cannot enumerate or control the exact Spotify session, return `SPOTIFY_SESSION_AUTHORITY_UNAVAILABLE` or `SPOTIFY_SESSION_ABSENT`. Do not fall back.

## Architecture

```text
Adam overlay widget
  -> typed local Spotify command
  -> Shizuku UserService (UID 2000 or 0)
  -> MediaSessionManager
  -> exact MediaController package com.spotify.music

Adam overlay prompt
  -> spotify.plan.v1
  -> deterministic Spotify account adapter
  -> POST /me/playlists or current playlist item endpoints
  -> bounded radio state
  -> exact Shizuku Spotify MediaController play_context
```

The Shizuku service performs a first-class capability probe. A running Shizuku binder is not sufficient evidence that Android grants shell/root access to active media sessions on this build.

## Typed operations

- `spotify.status`
- `spotify.play`
- `spotify.pause`
- `spotify.play_pause`
- `spotify.next`
- `spotify.previous`
- `spotify.stop`
- `spotify.play_context`
- `spotify.rolling.create`
- `spotify.rolling.revise`
- `spotify.rolling.enable`
- `spotify.rolling.disable`
- `spotify.rolling.stop_after_current`

## Account and secret boundary

Spotify OAuth uses Authorization Code with PKCE. Client ID, verifier, access token, refresh token, and expiry remain in owner-private local configuration. None may appear in overlay preferences, provider rows, Adam receipts, Home Center logs, GitHub, or Drive documents.

Current Spotify playlist routes used by this implementation are:

- `POST /me/playlists`
- `GET /playlists/{id}/items`
- `POST /playlists/{id}/items`
- `PUT /playlists/{id}/items`

The retired `/playlists/{id}/tracks` routes are forbidden.

## Rolling state machine

Rolling is deterministic and bounded. Explicit prompts may compile a policy once. Ordinary refill never calls a model.

Persistent non-secret state contains playlist ID, snapshot ID, policy, recent track/artist windows, rolling flag, stop-after-current state, and minimum/refill tail sizes. At or below the refill threshold, the account adapter appends a bounded batch idempotently. Rate limits back off. A refill failure never pauses current playback.

## Evidence contract

Source implementation is not deployment. Physical acceptance later requires a fresh primary-phone receipt proving:

1. the exact target package is `com.spotify.music`;
2. the foreground package is unchanged before and after every control;
3. no Activity, generic media key, or screen automation was used;
4. private playlist identity and snapshot are read back;
5. at least two track transitions occur and trigger a bounded tail refill;
6. an Adam prompt revises only upcoming items unless it explicitly asks to skip;
7. overlay collapse/hide and remote-control-off do not stop playback or rolling;
8. stopping Shizuku fails closed without foreground fallback;
9. final phone and Spotify session state are healthy.

The current source checkpoint performs no phone, Shizuku, overlay, Spotify, or screen action.
