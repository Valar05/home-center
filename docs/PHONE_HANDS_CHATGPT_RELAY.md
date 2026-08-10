# ChatGPT → Android Phone Hands Relay

## Mission

Remove the human copy/paste bridge and the desktop runtime dependency.

Authorized path:

`ChatGPT / Command Center MCP -> Home Center cloud relay -> Android phone relay agent -> Phone Hands -> Shizuku/rish -> Android`

Tailscale remains the direct peer-to-phone lane for devices already on the tailnet. The Home Center relay is the cloud rendezvous that allows ChatGPT to reach the phone without requiring the desktop to stay online.

## Command Center tools

- `command_center.phone_hands.devices` — list owner-scoped registered phones and last-seen state.
- `command_center.phone_hands.enqueue` — enqueue one bounded Phone Hands action with idempotency and TTL.
- `command_center.phone_hands.get` — read command status/result/failure.

Allowed relay actions are intentionally bounded: observe, tap, swipe, text, keyevent, home, back, recents, launch, force_stop, local_ask, and dungeon_run. Arbitrary shell is not part of the cloud relay contract.

## Phone authentication

The phone reuses its existing Home Center Termux pairing (`~/.config/home-center/codex-hub.json`). Expired short-lived access tokens are refreshed with the existing `termuxTokenRefresh` endpoint. A separate random device secret is generated locally during registration; only its SHA-256 digest is stored in Firestore.

The device secret is never returned by Command Center tools and must not be copied into chat, Drive, GitHub, or logs.

## Owner isolation

ChatGPT commands are owner-scoped using the existing Command Center OAuth caller identity. Phone registration maps the same Home Center bearer identity to the same owner key. Reads across owners return not-found semantics.

## Phone agent

`tools/android_phone_home_center_relay.py` polls Home Center for commands, leases one command, executes through the existing local Phone Hands implementation, and posts the result. It can also invoke the local executive or a named Coding Dungeon manifest.

Install/start script:

`tools/setup_android_phone_home_center_relay.sh`

## Completion evidence

This capability is **implemented** when the relay module, MCP wiring, phone agent, and deployment scripts exist and pass syntax/contract checks.

It is **deployed** only when all of the following are observed through the authorized lane:

1. `phoneHandsRelay` Cloud Function is ACTIVE.
2. Command Center MCP advertises the three `command_center.phone_hands.*` tools.
3. Android registers `primary-phone` and reports a recent `lastSeenAtMs`.
4. ChatGPT enqueues `observe`; the phone executes it; ChatGPT reads the actual foreground state back.
5. ChatGPT enqueues `home`; the phone changes to Home; a second `observe` confirms the mutation.
6. Desktop is not part of the path during the test.

Repository files or local-only tests are not deployment proof.
