# App Control Cloud Bucket

Type: Home Center cloud app automation / profile bucket / Shizuku migration
Status: candidate cloud contract with Chrome seed
Date: 2026-07-11

## Correction

The app-control bucket is Home Center cloud state, not a Termux-local folder. Repo files may seed and test it, but the runtime owner is Firebase/Command Center so the same profile can serve Drew's phone, June's phone, or another paired device with minimal local setup.

Use the already-connected Home Center MCP surface:

```text
tool: command_center_operation
operation: app_control.seed_profiles
args: {"idempotencyKey":"stable-seed-id"}
```

After seeding, read profiles through:

```text
operation: app_control.list_profiles
args: {"packageName":"com.android.chrome","workflow":"googleSearch"}

operation: app_control.get_profile
args: {"profileId":"com.android.chrome@150.0.7871.114+787111433"}
```

## Cloud Ownership

Firestore collections:

- `appControlProfiles/{profileId}`: app-specific profile versioned by Android package, `versionName`, and `versionCode`.
- `appControlRuns/{runId}`: redacted execution observations, elapsed time, UI action count, frame-lane status, and learned fixes.
- `commandCenterBucketObjects`: mirrored durable bucket objects under `app-control/profiles`, `app-control/runs`, and `app-control/frame-lanes` lanes for Command Center discovery and promotion.

Built-in seed data ships with Firebase Functions under `functions/app_control_seed/`. This is deployment input, not the steady-state user path.

## Current Chrome Seed

Profile id:

```text
com.android.chrome@150.0.7871.114+787111433
```

Source observation:

```text
/storage/emulated/0/Documents/GodotProjects/generated/android-shizuku-app-operator/chrome-scrambled-eggs-submit-20260711-094144
```

Important profile facts:

- Package: `com.android.chrome`
- Version: `150.0.7871.114` / `787111433`
- Workflow: `googleSearch`
- Preferred bounded surface: Android freeform frame
- Last observed frame bounds: `[449, 867, 997, 1947]`
- Search box bounds: `[575, 1019, 833, 1051]`
- Clear button bounds: `[832, 1019, 862, 1051]`
- Search button bounds: `[915, 1019, 943, 1051]`

## Frame Lane Rule

True background control is preferred: intents, exported activities, services, broadcasts, content providers, notification actions, app-owned files, or app-owned test hooks.

When an app cannot be fully backgrounded, Home Center may use a frame lane only if the executor keeps all UI actions inside a declared bounded surface and stops when the frame is lost. Whole-phone foreground takeover is not an acceptable fallback for slow repeated workflows.

The Chrome seed marks `wholePhoneFallbackAllowed=false` and `requiresUserRespectedSubframe=true`.

## Human-Authorized Foreground Task Rule

Home Center also supports a different explicit lane for real authenticated browser workflows:

```text
lane: human_authorized_foreground_task
```

This lane is allowed only when the human deliberately authorizes a named task and grants the agent a short takeover window. It is not a frame lane and does not require freeform bounds. It is also not silent background automation; the visible browser flow is temporarily the agent's work surface.

Required profile fields:

- `taskKey`
- `allowedPackages`
- `allowedOrigins`
- `wrongSurfacePackages`
- `requiresFreshHumanAuthorization=true`
- `humanKeepsSensitiveGates=true`
- `wholePhoneFallbackAllowed=true` only for the named foreground task, not as a general fallback
- `maxBurstMs` and `maxUiActions`
- `stopSignals` for focus loss, unexpected package/origin, sensitive gates, CAPTCHA/login verification, payment/purchase, destructive actions, and stale selectors
- `learningOps=["app_control.record_run","browser_sessions.record_episode"]`

Required run evidence:

- foreground package, URL/title/page signature, and task state before action;
- selector or accessibility evidence used for each action when available;
- fallback coordinates only as containment evidence, never as the promoted browser playbook;
- elapsed time, UI action count, final status, blocker if stopped, and evidence refs;
- redaction report proving no secrets, payment data, cookies, tokens, or raw sensitive fields were stored.

Promotion rule: foreground tasks may become candidate discoveries, but trusted household replay still requires semantic selectors from Playwright DOM/accessibility or an equivalent web channel. Coordinates alone stay diagnostic.

## Minimal Second-Phone Setup

1. Install Home Center and sign in.
2. Pair the device/household bucket.
3. Install Shizuku/rish only when the local executor requires it.
4. Let Home Center fetch `appControlProfiles` from cloud.
5. The executor reports unsupported local capabilities instead of falling back to whole-phone takeover.

## Promotion Rule

A workflow stays `candidate` until another run proves it is measurably faster and less disruptive than terminal automation. Promote only with `appControlRuns` evidence: elapsed time, UI action count, frame-lane status, app version, and failure fixes.


## Browser Hands Relationship

Chrome browser tasks should prefer the Playwright `browser-worker/` desktop Chromium runtime when the goal is web understanding, narration, DOM/action learning, or reusable browser playbooks. On Android, that means Debian/proot on the device with Debian-native Node and Chromium. Android Shizuku/Chrome app-control profiles remain the Chrome-app/window fallback lane for device-specific control, freeform bounds, and visible manual assistance.

## Shared Runtime Rule

Termux, Home Center, paired-device, and browser-worker callers use the same retained app-control and browser operation contracts. Durable learning belongs in owner-scoped app-control runs, browser episodes, discoveries, and bucket objects. Terminal transcripts, screenshots, and coordinates are diagnostics only and cannot become trusted replay behavior.
