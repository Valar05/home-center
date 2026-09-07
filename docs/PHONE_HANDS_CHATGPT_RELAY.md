# ChatGPT → Android Phone Hands Relay

## Mission

Remove the human copy/paste bridge and the desktop runtime dependency.

Authoritative path:

`ChatGPT -> Home Center MCP -> Home Center cloud relay -> Android phone relay agent -> Phone Hands -> Shizuku/rish -> Android`

Tailscale remains the direct peer-to-phone lane for devices already on the tailnet. The Home Center relay is the cloud rendezvous that allows ChatGPT to reach the phone without requiring the desktop to stay online.

## Home Center compatibility operations

The deployed API still contains historical `command_center.*` identifiers. Those names are compatibility debt inside Home Center; they do not establish a separate Command Center product, owner, queue, control plane, or operator surface.

- `command_center.phone_hands.devices` — Home Center compatibility operation that lists owner-scoped registered phones and last-seen state.
- `command_center.phone_hands.enqueue` — Home Center compatibility operation that enqueues one bounded Phone Hands action with idempotency and TTL.
- `command_center.phone_hands.get` — Home Center compatibility operation that reads command status/result/failure.

The relay action allowlist includes `phone_shell` for bounded Termux commands as well as observe, tap, swipe, text, keyevent, home, back, recents, launch, force_stop, local_ask, dungeon_run, and the other explicitly registered Phone Hands actions. `phone_shell` executes through the phone-local Termux shell adapter; it is not equivalent to granting arbitrary Android/root authority.

### ChatGPT ingress is mandatory

If a ChatGPT worker needs a Termux command executed, it must attempt the existing Home Center Phone Hands ingress first. Where the deployed operation registry exposes only the historical compatibility name, invoke `command_center.phone_hands.enqueue` with the bounded `phone_shell` action through Home Center. A manual Termux handoff is legal only after durable evidence shows the authorized Home Center phone execution lane is unavailable or requires operator-only authority.

If the current ChatGPT surface does not expose or connect the required Home Center ingress operation, classify that as a **ChatGPT phone-ingress failure**. Repair or reconnect the Home Center ingress. Do not reinterpret connector or compatibility-operation absence as proof that Phone Hands or `phone_shell` does not exist, and do not route around the missing ingress by turning Drew into the command transport.

Any manual fallback that genuinely survives that exhaustion must be a fenced, immediately copy-pasteable command block.

## Phone authentication

The phone reuses its existing Home Center Termux pairing (`~/.config/home-center/codex-hub.json`). Expired short-lived access tokens are refreshed with the existing `termuxTokenRefresh` endpoint. A separate random device secret is generated locally during registration; only its SHA-256 digest is stored in Firestore.

The device secret is never returned by Home Center Phone Hands operations and must not be copied into chat, Drive, GitHub, or logs.

## Owner isolation

ChatGPT commands are owner-scoped using the existing Home Center OAuth caller identity. Phone registration maps the same Home Center bearer identity to the same owner key. Reads across owners return not-found semantics.

## Phone agent

`tools/android_phone_home_center_relay.py` polls Home Center for commands, leases one command, executes through the existing local Phone Hands implementation, and posts the result. It can also invoke the local executive or a named Coding Dungeon manifest.

Install/start script:

`tools/setup_android_phone_home_center_relay.sh`

## Completion evidence

This capability is **implemented** when the relay module, MCP wiring, phone agent, and deployment scripts exist and pass syntax/contract checks.

It is **deployed** only when all of the following are observed through the authorized lane:

1. `phoneHandsRelay` Cloud Function is ACTIVE.
2. Home Center advertises the three historical compatibility operations `command_center.phone_hands.devices`, `command_center.phone_hands.enqueue`, and `command_center.phone_hands.get` (or their explicitly superseding Home Center names).
3. Android registers `primary-phone` and reports a recent `lastSeenAtMs`.
4. ChatGPT enqueues a bounded `phone_shell` canary through Home Center; the phone executes it; ChatGPT reads the actual stdout/exit receipt back.
5. ChatGPT enqueues `observe` through Home Center; the phone executes it; ChatGPT reads the actual foreground state back.
6. ChatGPT enqueues `home` through Home Center; the phone changes to Home; a second `observe` confirms the mutation.
7. Desktop is not part of the path during the test.

Repository files or local-only tests are not deployment proof.

## Stewardship provenance

2026-09-07 archaeology reconciliation: this document previously described the compatibility namespace as an active “Command Center” surface and told workers to reconnect “Command Center.” Current Fortress doctrine preserves the exact `command_center.*` strings only where required to invoke deployed compatibility operations. Home Center is the authoritative integration and delivery surface. This reconciliation changes naming/routing doctrine only; it does not claim any runtime deployment state changed.
