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

## Shared Termux / Home Center Workflow

Termux and Home Center are different inputs to the same code path. A Termux script may launch, observe, or debug an app, but it must emit the same `command_center_operation` payloads that the Home Center app, a paired worker, or a cloud executor would submit.

For Chrome frame observations the shared envelope is:

```text
tools/chrome_frame_learning_envelope.mjs
```

It produces two operations:

```text
operation: app_control.record_run
operation: browser_sessions.record_episode
```

Submit the envelope through Home Center MCP with:

```sh
node tools/submit_chrome_frame_learning.mjs --envelope tools/chatgpt_connector_evidence/chrome_frame_<runId>.learning.json
```

This keeps the durable learning in `appControlRuns`, browser episodes, discoveries, and bucket objects. The terminal transcript is only local evidence.

## ChatGPT Command Center Connector Learning

The painful 2026-07-11 OAuth/frame run is now a Chrome app-control workflow named `chatgptCommandCenterConnector` in the cloud seed profile:

```text
functions/app_control_seed/com.android.chrome.150.0.7871.114+787111433.json
```

Do not repeat the manual OAuth maze as the first move. Promote the learning from the existing evidence into Home Center cloud with:

```sh
sh tools/learn_chatgpt_connector_frame_lane.sh --submit
```

For local contract-only validation:

```sh
node tools/chatgpt_connector_frame_learning_contract_test.mjs
```

Captured hard lessons:

- Approval prompts during live frame work kill the nested Chrome window. Pre-approve the Shizuku command lane before opening the frame, or stop before frame launch.
- ChatGPT web auth may callback into the installed ChatGPT app. That app is the wrong surface; force-stop `com.openai.chatgpt` and reopen the ChatGPT web connector URL in Chrome freeform.
- Google/OAuth WebViews can make XML unavailable. Capture screenshots first and use bounded, known controls only when the screenshot confirms the same page.
- Connected-state evidence is mandatory before any ChatGPT prompt or mutation test. Prompt text in the composer is not success.
- Coordinates in app-control profiles are containment/fallback evidence only. Reusable website intelligence belongs in browser playbooks with Playwright DOM/accessibility selectors so Drew's first-use discovery can automate June's later use.
