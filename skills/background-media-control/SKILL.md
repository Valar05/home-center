# Background Media Control Skill

## Purpose

Build and operate promptable background-media controls through an existing user-owned surface without laundering foreground launch, generic media keys, or source existence into provider-specific playback.

The canonical chain is:

`USER INTENT -> EXISTING WIDGET/PROMPT -> TYPED PLAN -> PROVIDER ACCOUNT ADAPTER -> EXACT ANDROID PROVIDER SESSION -> PHYSICAL PLAYBACK -> RECEIPT -> HUMAN ACCEPTANCE`

Every stage remains distinct. A button tap, accepted Intent, API response, playlist manifest, generated APK, or media command is not physical playback.

## 1. Preserve the commissioned surface and body

When the user names an existing overlay, notification, cockpit, app, or accessibility surface, extend it. Do not create a parallel app, second overlay, browser dashboard, or substitute player because it is easier.

When Shizuku is commissioned as the Android body, use a narrow Shizuku UserService or equally explicit Shizuku contract. Shizuku being alive does not prove the shell/root identity has the required provider authority. Probe the exact capability and fail closed.

A local remote-control kill switch may govern remote screen/body actions without owning local background playback lifetime. Collapsing, hiding, or disabling remote control must not silently stop an already-authorized local media session unless the user explicitly requests that coupling.

## 2. Provider specificity is mandatory

Bind each adapter to an exact provider identity. Spotify uses `com.spotify.music`.

Before mutation:

1. obtain the authoritative Android media-session list through the commissioned body;
2. locate a controller whose package exactly matches the provider;
3. reject absent or ambiguous sessions;
4. invoke one bounded transport operation on that exact controller;
5. observe the same controller afterward and verify the requested state or track identity changed.

Generic media keys, media-button broadcasts, `cmd media_session dispatch`, key injection, or untargeted AudioManager dispatch are forbidden for provider-specific work. They can affect the wrong player and cannot prove provider ownership.

## 3. Background means no foreground recovery trick

Normal status, play, pause, toggle, next, previous, stop, context playback, and rolling maintenance must not:

- launch an Activity;
- use `Intent.ACTION_VIEW` or a deep link;
- call `phone.open_uri`, `am start`, `monkey`, taps, coordinates, UIAutomator, or input keyevents;
- take a screen lease;
- switch the foreground package;
- fall back to browser playback, a generic player, desktop playback, system TTS, or another provider.

If the exact session is unavailable, return a named failure such as `PROVIDER_SESSION_ABSENT` or `PROVIDER_SESSION_AUTHORITY_UNAVAILABLE`. Absence is not permission to foreground the provider.

## 4. Separate the account plane from the playback body

Playlist creation, search, item mutation, and account authorization belong to the provider account plane. Playback transport belongs to the commissioned Android body. Keep their credentials, receipts, failure states, and acceptance evidence separate.

Use current provider endpoints and explicit OAuth contracts. Store tokens only in owner-private state. Never place access tokens, refresh tokens, PKCE verifiers, authorization codes, client secrets, cookies, or raw authorization URLs in overlay preferences, repository files, ordinary logs, Drive documents, or durable receipts.

An account playlist is accepted only after provider readback proves its exact ID/name/snapshot and item count. Local JSON and a proposed track list are not playlist creation proof.

## 5. Promptability compiles to a finite plan

Natural-language media prompts may compile once into a typed plan, for example `spotify.plan.v1`. The executor accepts only a finite vocabulary such as:

- status;
- play, pause, play/pause;
- next, previous, stop;
- play an exact validated context;
- create or revise the rolling playlist;
- enable or disable rolling;
- stop after the current track.

Unknown prose returns legal examples. It never becomes shell text, an Activity Intent, or an autonomous screen loop. Ordinary rolling maintenance must not call a model.

A revision changes only the unplayed tail unless the user explicitly requests a skip or replacement of the current track.

## 6. Rolling is a bounded deterministic state machine

Persist only non-secret state: playlist ID, snapshot ID, policy hash, recent track/artist windows, refill threshold, refill count, rolling flag, and stop-after-current anchor.

The daemon must be idle without provider authentication or network calls when rolling is off and stop-after-current is false. When active, it:

1. verifies the commissioned playlist is the current context;
2. finds the current track in the provider-read playlist;
3. calculates the remaining unplayed tail;
4. appends one bounded idempotent batch at or below the threshold;
5. backs off on provider rate limits;
6. leaves current playback untouched when refill fails.

Explicit pause and stop outrank rolling. Calls, competing media, lost provider authority, and ambiguous state yield rather than fight the user or hammer recovery.

## 7. Accessibility is part of the command contract

Use minimum 48dp touch targets, precise content descriptions, stable ordering, and textual status that does not depend on album art, color, or animation. Compact controls remain reachable when the rest of the surface collapses. Prompt input must work with voice keyboards and screen readers.

Announcements are bounded. Do not repeatedly announce polling/status probes. Announce explicit local command results and actionable failures without interrupting TalkBack continuously.

## 8. Stable runtime and boot continuity

Do not leave the live adapter dependent on a dirty or unrelated checkout. Install reviewed bytes under a stable owner-private runtime path, expose a fixed wrapper, verify source and installed SHA-256 equality, and use an idempotent restart-safe boot hook.

The boot hook starts a deterministic daemon only. It does not authorize an account, request Shizuku permission, launch the provider, start playback, or create a playlist by itself.

## 9. Evidence and capability-state law

Keep these states explicit:

- requested;
- intended;
- implemented in repository;
- source-tested;
- APK built;
- installed;
- Shizuku-authorized;
- provider-account-authorized;
- session-callable;
- playlist-created/read back;
- physical playback verified;
- delivered;
- human accepted.

Repository code proves implementation only. Tests prove tested behavior only. An APK hash proves built bytes only. Installation proves installation only. A Binder receipt proves the command path only. Provider readback proves account state only. Physical playback and human audibility require their own evidence.

A completed action receipt records at minimum:

- device and request identity;
- visible surface and typed plan/action;
- provider package;
- pre/post session state and metadata;
- authority and session-presence results;
- whether Activity launch, generic media keys, screen automation, or foreground mutation were used;
- playlist ID/snapshot when applicable;
- rolling decision when applicable;
- final device health;
- human acceptance state when commissioned.

## 10. Recovery sequence

When background control fails:

1. check the body/relay heartbeat without changing the user-owned kill switch;
2. distinguish background shell/service authority from screen-control authority;
3. verify Shizuku binder, version, permission, and exact media-session authority independently;
4. verify the provider package and exact active session;
5. verify stable runtime hashes and daemon state;
6. verify account authorization separately from playback authority;
7. restart only the failed organ;
8. run one status/probe before any playback mutation;
9. execute the exact requested operation and verify the provider afterward.

Do not convert a diagnosable blocker into a handback. Diagnose and repair every non-operator layer first. Stop only at an actual user-owned authorization/consent boundary, explicit user stop, safety boundary, or a fresh Venice `STOP_ALLOWED` review for the commissioned checkpoint.

## Completion law

Background media is complete only when the requested provider is physically playing through the requested device, the existing widget and prompt path both control the exact provider session, the account playlist exists by provider readback, rolling behavior is demonstrated without violating yield rules, foreground state remains untouched, final device health is observed, and the commissioned perceptual verifier accepts the result.