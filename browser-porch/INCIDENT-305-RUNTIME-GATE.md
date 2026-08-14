# Incident 305 — Chromium Throne runtime gate

Status: **source recovery gate only; runtime acceptance still requires THECAULDRON receipts.**

This is the lean execution card for the first operator-facing critical path after the 2026-08-13 serialization/token-exhaustion incident. It deliberately does not expand into a general bootstrap or new control plane.

## Gate 0 — repository truth

- Start from current `main` after PR #304.
- Use `tools/install_chromium_throne.ps1`; do not redesign Chromium Throne.
- The installer pins the reviewed 0.7.0 extension commit carrying invocation-independent Fortress doctrine.
- A source/install receipt is not runtime acceptance.

## Gate 1 — one real Chromium Throne MVP

Execute through the already-authorized THECAULDRON machine lane:

`powershell -ExecutionPolicy Bypass -File tools/install_chromium_throne.ps1 -Launch`

Acceptance is all-or-nothing:

1. installer source checks pass and `install-receipt.json` exists;
2. Chromium Throne 0.7.0 launches visibly;
3. reuse an already-authenticated authorized ChatGPT session before declaring login a human boundary;
4. exactly one persistent visible ChatGPT Pro-reasoning conversation is the normal worker;
5. submit one tiny Fortress commission through the intended Throne/CLI control surface;
6. receive a durable checkpoint/receipt for that commission;
7. kill/restart the initiating shell/browser control path and prove the persistent campaign identity/state is recoverable;
8. run a second tiny evolution generation in the same persistent Pro conversation;
9. record requested / implemented / tested / installed / callable / delivered / accepted separately;
10. only then may Gate 1 be called accepted.

## Forbidden until Gate 1 passes

- no new universal bootstrap;
- no new browser farm or parallel worker architecture;
- no phone-control redesign;
- no speculative garden/daemon integration;
- no UI polish unrelated to a failure observed during the canary;
- no broad refactor because the runtime proof feels inconvenient;
- no declaration that `Fortress online`, `PORTCULLIS LOCKED`, or any other phrase is required to obtain competent operator/evidence/consultation behavior.

## Failure handling

On failure: preserve the exact receipt/error, classify the mechanism, inspect the smallest relevant source, make one bounded repair, and rerun the failed check. Do not widen the mission. If the authorized THECAULDRON lane is unavailable, record that exact runtime boundary; do not substitute local ChatGPT scratch or repository source as device proof.

## Next gate

Only after Gate 1 passes: serialize subsequent campaigns through the CLI/intake path one bounded task at a time, each ending in a durable checkpoint and receipt rather than a promise.
