# Body Lane Authority Skill

## Purpose

Keep physical screen authority separate from background execution authority. A user-owned screen-control switch protects visible Android input. It is not a master kill switch for every service, shell, file operation, diagnostic, audio engine, media session, or recovery organ on the device.

This skill applies to Phone Hands, Computer Hands, overlays, notifications, accessibility services, media widgets, background daemons, and future body adapters.

## Core distinction

Classify every action before dispatch:

1. **Screen and input actions** manipulate or inspect the visible interactive surface: taps, swipes, text injection, key events, navigation, launching or force-stopping apps, window composition/focus/swap, screenshots, and screen-dependent agents.
2. **Background actions** operate without taking the visible screen: bounded Termux commands, deterministic file/factory work, diagnostics, compilation, artifact processing, background audio or media-session control, provider status, daemon recovery, and other explicitly registered non-UI work.
3. **Overlay maintenance** reads, restores, heartbeats, or updates the local operator surface without granting control.
4. **Unknown actions** are unclassified and fail closed.

The user-owned screen switch gates category 1 and category 4. It does not gate category 2 or category 3.

## Explicit allowlists

Background bypass must be an explicit finite allowlist. Do not infer safety from an arbitrary action name, payload, or model judgment.

Each background adapter retains its own authority checks. Examples:

- Phone Shell enforces command length, working-directory, timeout, output, and secret-redaction bounds.
- File/factory actions enforce registered roots and operation schemas.
- Shizuku-backed media actions enforce exact provider/session ownership.
- Status audio obeys the local mute state even when screen control is off.
- Diagnostics remain read-only and bounded.

Bypassing the screen switch never means bypassing the action’s own contract.

## Recovery law

The execution organ required to repair the screen-control path must remain callable while screen control is off. Otherwise the safety control becomes a circular outage generator.

At minimum, these recovery classes remain independent of the screen switch:

- background shell execution;
- relay status and restart;
- read-only diagnostics;
- overlay status/start/update;
- stable-runtime hash and process checks.

Do not ask the user to enable the screen interface merely to repair or operate backend machinery.

## Local controls

A local widget button may submit a typed background request while the remote screen switch is off. Hiding the widget may hide its controls, but existing background playback or computation continues unless the user issued a stop command.

Remote code may never turn the local screen switch on. The correct response to a disabled screen switch is:

- continue legal background work;
- deny only screen/input work;
- surface the exact denied category when a visible action is genuinely required.

## Muting and physical effects

Screen authority and physical-effect preferences are separate. Background speech and audio may bypass the screen switch but still obey the appropriate local mute, volume, focus, call-state, and competing-media policies.

Do not treat “screen control off” as “all sound forbidden,” and do not treat “mute off” as permission to manipulate the screen.

## Dispatch order

A relay should dispatch in this order:

1. validate request identity and schema;
2. handle read-only diagnostics;
3. handle overlay maintenance;
4. handle explicitly allowlisted background actions and their local policy checks;
5. apply the user-owned screen gate;
6. dispatch registered interactive actions;
7. reject unknown actions.

A universal gate placed before classification is a defect.

## Evidence

Completion requires separate receipts for:

- action classification;
- action-specific authorization;
- whether the screen gate was consulted;
- background or interactive lane used;
- terminal execution state;
- physical/provider postcondition where applicable;
- final device health.

A repository change proves implementation only. The corrected relay must be installed/restarted, a background canary must complete while screen control is off, and a screen action must still be denied before the authority split is runtime-proven.

## Regression requirements

Tests must prove all of the following:

- background dispatch appears before the screen gate;
- Phone Shell works with screen control disabled;
- diagnostics and overlay maintenance remain callable;
- status audio reads mute without requiring control enabled;
- an interactive action remains denied while control is disabled;
- an unknown action remains denied;
- background action names cannot be supplied dynamically by untrusted input;
- adding a new action requires explicit classification.

## Compact law

The switch protects Drew’s screen. It does not hold the backend hostage. Classify first, gate only interactive work, and keep repair lanes callable from the state they repair.
