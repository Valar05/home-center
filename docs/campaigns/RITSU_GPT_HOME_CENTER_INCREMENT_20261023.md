# Ritsu ChatGPT bridge: first non-singleton Home Center increment
Date: 2026-10-23
Scope chosen by owner: **Thoughtful 5-second pause; work on GPT integration; full worker parallelism later; do NOT build a singleton.**

## Architecture frozen for the first executable slice

Android Ritsu Control (voice + visible chat)
    [future authenticated phone/Home Center ingress; NOT YET DEPLOYED]
Home Center coordinator instance per campaign / independent configured session
    - CONTROL: stable main-thread Chrome ChatGPT session
    - DIALOGUE: separate ChatGPT conversation, reply staged for review
    - WORKERS: result envelope schema only, no fanout/worker spawning
Home Center trusted local executor on THECAULDRON
    - authenticated localhost 127.0.0.1:9234/v1/throne
    - existing Chromium Throne extension / actual ChatGPT login session
Home Center result inbox -> validated control/main publication -> future phone UI
    [voice playback still uses canonical Windows/Tailscale :19643 -> Termux]

**There is no singleton.** Each call creates a coordinator with its own namespace, control session, dialogue session, injected store and injected transport. The state is separate per campaign and later per user/device. The file-store adapter locks each campaign namespace across *independent* CLI processes. Cross-campaign coordinator instances can run independently. This is small now but structurally ready for future parallel worker output.

## Source implemented

- `browser-porch/ritsu-home-center-coordinator.mjs`: explicit `createRitsuHomeCenterCoordinator({namespace,controlSessionId,dialogueSessionId,store,transport})`. Deterministic stored receipts, stable turn IDs, fail-closed duplicate/collision handling, durable pre-dispatch receipt, readback with exact matching session/turn/channel/tabId.
- `browser-porch/ritsu-coordinator-file-store.mjs`: private JSON state files written through write + fsync + atomic rename. O_EXCL per-campaign lock across separate host CLI instances, with bounded acquisition deadline. Stale crash lock requires explicit operator recovery instead of guessing/releasing it. Higher-volume production may substitute a transactional Home Center DB behind the same interface.
- `browser-porch/ritsu-home-center-throne-transport.mjs`: bearer authenticated local adapter. Rejects any endpoint except HTTP 127.0.0.1 with the required /v1/throne path; does not expose capabilities to Android.
- `browser-porch/ritsu-home-center-cli.mjs`: Home Center host-local CLI that reads **one JSON operation from stdin** for submit, poll, state, feed, or main publication. Its authority is the trusted local Home Center executor, **not an exported phone endpoint**.
- `browser-porch/ritsu-home-center-coordinator.test.mjs` and `ritsu-home-center-cli.test.mjs`: session/campaign isolation, replay/collision, readback after ambiguous dispatch, staged dialogue and worker results, control-only publish, chronological deterministic merge, concurrent independent CLI processes and full CLI -> actual localhost relay -> *simulated* extension complete -> readback.
- Updated GitHub Actions workflow for syntax + tests.
- **Android** default preference changed to 5 seconds and one-time upgrade migration for existing settings, while preserving later explicit changes. No APK/device retest needed just for the timing update.

## Exact logical contract

1. The owner completes an utterance; Android creates one stable `turnId` and keeps it until Home Center acceptance. (Android authenticated ingress is still missing.)
2. A trusted Home Center actor calls `submitUserTurn` with channel dialogue or control. The coordinator persists a pre-send `dispatch_unknown` receipt before network POST. If the network outcome is lost or process crashes, never blindly replay a potentially submitted ChatGPT prompt.
3. Authenticated Chromium Throne relay accepts `ritsu.<turnId>` and the dedicated Chrome extension dispatches `chat.turn` to its role's logged-in ChatGPT tab.
4. Home Center calls `readOneTurn`. A reply only counts as *completed* with exact IDs, tab ID, nonempty text, and matching validated wire receipt. A relay 404, missing extension, stale tab, or uncertain dispatch is NOT proof of delivery and never authorizes a duplicate POST.
5. Control results can be projected as main-thread receipts. Dialogue/worker results remain **staged** and invisible in the outward merged projection until a separate `mainThreadPublish({controlTurnId,turnIds,resultIds})` call has verified that `controlTurnId` is a genuinely completed CONTROL turn. Worker result text is inert content, never interpreted as a command and never initiates recursive dispatch.
6. Publication ordering uses coordinator event sequence, **not** browser tab finish time, worker text, local clock, or assumed parallel job order. IDs are unique and bounded.
7. Future parallel workers can supply additional result envelopes through `stageWorkerResult`. This does NOT spawn workers or automatically publish their content in the current slice.

## Host-local usage boundary

Environment on trusted Windows Home Center runner (not in the APK or copied to phone):
- `HOME_CENTER_RITSU_NAMESPACE` stable ID
- `HOME_CENTER_RITSU_CONTROL_SESSION` stable CONTROL conversation ID
- `HOME_CENTER_RITSU_DIALOGUE_SESSION` separate DIALOGUE conversation ID
- `HOME_CENTER_RITSU_STATE_DIR` absolute private writable directory
- `HOME_CENTER_CHROMIUM_THRONE_CAPABILITY` existing secret stored only on trusted desktop
- optional `HOME_CENTER_RITSU_RELAY_URL` loopback URL (default 127.0.0.1:9234)

Feed exactly one JSON request to the CLI on STDIN:
- `{"operation":"submit","turnId":"ritsu-demo-turn-01","channel":"dialogue","prompt":"Hello."}`
- `{"operation":"poll","turnId":"ritsu-demo-turn-01"}`
- `{"operation":"state"}`
- `{"operation":"feed"}`
- `{"operation":"publish","controlTurnId":"ritsu-control-turn-01","turnIds":["ritsu-demo-turn-01"]}`

No public listener, no debug default credential, no direct Android bearer, no automatic worker subprocesses, no hidden job polling. Operational deployment requires Home Center worker privilege and a **verified live Chromium Throne profile**.

## Acceptance / explicit gaps

**Code/tests** validate a real authenticated relay transport and the deterministic main-controlled merge, with browser completions **simulated** inside integration tests. They do NOT prove Chromium Throne is deployed on THECAULDRON or that a real ChatGPT response was captured.

Still required:
- Authenticated phone -> Home Center turn ingress and protected result feed under existing Home Center identity, with durable acceptance ack and no credentials in the APK.
- Deploy this coordinator and changed Chromium Throne extension to the live host profile; one literal user prompt -> captured ChatGPT assistant DOM reply -> coordinator result proof -> main conversation presentation.
- Real Android result rendering from Home Center receipt/worker feeds.
- Approved Ritsu voice synthesis and canonical phone playback with user-heard test; audio interruption and phone playback rejection.
- Multi-worker scheduling, fanout cap, deterministic control approvals and context rotation only **after one dialogue + control path works live**.

**Do not** claim a Home Center cloud operation already exists for Ritsu turns. The connected deployed registry currently exposes Ritsu voice operations but does not list a `ritsu.turn.submit`/result feed. Adding source files to a feature branch does not deploy the cloud connector.

PR: https://github.com/Valar05/home-center/pull/387
