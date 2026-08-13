# Overlay Radio Skill

## Purpose
Recover and operate a promptable, persistent media-radio lane through the existing Home Center Adam overlay. The first provider adapter is Spotify Android, but the doctrine applies to any later streaming provider or local media source without collapsing intent, provider control, physical playback, and user acceptance into one claim.

## Commission boundary
The user-facing surface is the existing Home Center/Adam Android overlay. Do not create a second overlay, dashboard, fake player, browser replica, or unrelated notification surface merely because it is easier.

The normal physical lane is:

`Adam overlay prompt/control -> operator state provider -> Adam body router -> deterministic radio controller -> provider app/media session -> Android audio output -> receipt`

Home Center -> Command Center -> Phone Hands remains the remote setup, repair, and evidence lane. A desktop may help build or review source, but it cannot replace physical-phone playback proof.

## Separation law
Never collapse these states:

1. **Prompt received** — the overlay recorded the user’s request.
2. **Intent compiled** — a deterministic controller selected a bounded media action.
3. **Provider action dispatched** — Spotify or another provider accepted an Android intent or transport command.
4. **Provider session observed** — the intended package owns the Android media session.
5. **Playback verified** — the provider session reports a playing/buffering/connecting state and useful metadata when exposed.
6. **Audibility accepted** — the user confirms the expected sound when human hearing is the commissioned acceptance standard.
7. **Continuity verified** — later status proves the intended station is still running or recovered within policy.

An intent exit code, foreground activity, generated playlist file, generic media-key success, scheduler state, or source implementation is not playback proof.

## Spotify adapter contract
The canonical provider identity is `com.spotify.music`.

- Use the installed Spotify Android app and its Android `MediaSession`.
- Do not collect, log, copy, or persist Spotify passwords, cookies, OAuth tokens, client secrets, or account data.
- Do not introduce the Spotify Web API merely to avoid using the commissioned phone body.
- Resolve the real launcher activity rather than trusting a generic `monkey` success.
- Search playback uses the Android `MEDIA_PLAY_FROM_SEARCH` intent.
- Playlist/track/album/artist links may use explicit Spotify URI or `open.spotify.com` identity.
- Before sending transport keys, prove Spotify owns a media session. After the action, read the same Spotify session back.
- Never let a generic global media key silently control a different player.

## Prompt contract
The existing Adam overlay accepts explicit `RADIO` mode and unambiguous Spotify/radio prompts from the other Adam modes. Deterministic examples include:

- `play Battles by Alpine Universe on Spotify`
- `keep it rolling`
- `pause radio`
- `resume radio`
- `next`
- `previous`
- `radio status`
- `stop radio`

Unrecognized requests do not guess. They return bounded usage guidance or remain in the previously selected Adam lane.

Overlay transport buttons submit the same radio prompts through the Adam state provider. They do not bypass the prompt/receipt lane with anonymous media-key calls.

## Playlist contract
A playlist is considered created only after the provider app shows the requested name and contents on the real account. A requested name in config, a JSON object, a search result, or a local queue is not a Spotify playlist.

For each playlist preserve:

- human-readable name;
- provider URI or verified provider URL when available;
- at least one seed track read back from Spotify;
- creation/readback receipt;
- current continuity policy.

Default station identity:

- name: `Fortress Radio — Rolling Forge`
- seed query: `Battles Alpine Universe`

## Keep-rolling policy
“Keep it rolling” means persistent best-effort continuity, not an immortal process that fights the user.

The monitor may recover only when all are true:

- radio `enabled` is true;
- radio `suspended` is false;
- prior playing state was physically verified;
- Spotify is now stopped, missing, or errored beyond the recovery grace period.

The monitor must **not** auto-resume a `PAUSED` session. Explicit pause, stop, off, mute, Android audio focus, phone calls, alarms, and local user action outrank continuity. `stop radio` disables recovery until a later explicit start or resume.

One monitor process is enough. Duplicate monitor processes are a defect, not redundancy.

## Accessibility
- Radio controls require meaningful content descriptions and minimum touch targets.
- Prompt results must return concise text through the existing overlay.
- Status should expose provider, state, track/artist when available, radio enabled/suspended state, and whether playback was verified.
- Never require color alone to distinguish play, pause, stopped, or failed state.
- Pocket Space TTS may speak a status result when explicitly requested, but synthesized/status speech is separate from music playback evidence.

## Deployment discipline
Do not mutate or reset a dirty user checkout. Use an isolated branch/worktree, validate source, preserve unrelated overlay controls, then build/install on the primary phone.

Before replacing the overlay APK, preserve and regression-check:

- local enable/disable authority;
- mute state;
- draggable/collapsible behavior;
- existing TERM/CHAT/CONT/VLAD modes;
- Adam request provider fields;
- Pocket Space playback in its owning Home Center package;
- signing/update identity.

Repository implementation proves implementation only. Runtime acceptance requires the installed APK version, installed stable controller, live monitor identity, overlay prompt receipt, provider session readback, physical playback, and final phone health.

## Evidence receipt
A successful radio action receipt should include, where applicable:

- primary-phone identity;
- overlay request ID and mode;
- controller action;
- provider package;
- Spotify intent or URI identity without secrets;
- session state before/after;
- title/artist/album when exposed;
- playlist name and URI when verified;
- enabled/suspended continuity state;
- playback verification boolean;
- exact command/ticket ID;
- terminal status;
- final phone/overlay status;
- human audibility acceptance when required.

## Failure handling
If Spotify is installed but no session appears, diagnose activity resolution, login/account state, app focus, audio focus, and provider UI before claiming absence.

If the visible local Home Center control switch is off, surface the existing overlay and request exactly one local `ENABLE` tap. Never add or use a remote enable bypass.

If playlist creation reaches a real Spotify login, MFA, subscription, or provider-confirmation boundary, finish every independent implementation and report the exact blocked transition. Do not substitute a local playlist and call it Spotify.

## Completion gate
DONE requires all of:

1. Spotify control physically works on `primary-phone`.
2. The commissioned Spotify playlist exists and is read back from Spotify.
3. Playback begins from that playlist or its verified seed and Spotify owns the playing media session.
4. Adam-overlay prompts and radio controls operate the same deterministic controller.
5. Explicit pause remains paused through a monitor cycle.
6. Explicit resume/start restores playback.
7. Stable runtime and monitor survive outside the dirty development checkout.
8. Durable source, tests, deployment receipt, execution receipt, final phone health, and fresh Venice `STOP_ALLOWED` review exist.

Until those conditions are met, the directive is `CONTINUE_REQUIRED`.
