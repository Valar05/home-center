# Ritsu Chat Text Control: Stage C1

## Commission and architectural decision
Commissioned 2026-10-22: make a **real ChatGPT control** loop available while voice synthesis and UI overlay are under development. Evaluate Android-hosted versus THECAULDRON-hosted browser. The selected initial host is **Chromium Throne on THECAULDRON**, leaving Ritsu's Android phone as the user-facing cockpit and Home Center as the deterministic, authenticated coordinator.

This choice does **not** mean the phone must display ChatGPT or the desktop worker tab must be foregrounded. Existing Throne creates separate Chrome worker tabs with `active: false`. It does mean the dedicated Chromium Throne profile/extension/relay must be live on desktop.

## Implemented in feature branch
- `browser-porch/ritsu-turn-protocol.mjs` strictly validates stable `sessionId`, `turnId`, `channel` (control/dialogue) and bounded prompt; commandID is derived from turnId, not from a guessed timestamp.
- Existing Chromium Throne localhost relay `browser-porch/relay.mjs` now accepts `action:'chat.turn'` in addition to unchanged swarm actions, requires existing bearer capability and extension-origin lease, and exposes bearer-only `GET /v1/throne/result?commandId=...`.
- A turn can be delivered to Chrome **once**. Duplicates with identical commandId and text are idempotent; conflicting text rejects with 409. A lease expiry becomes `uncertain` and does not automatically replay a potentially already-submitted prompt. In-memory relay dedupe alone is NOT durable across process restart, so authoritative Home Center durability remains a separate unaccepted boundary.
- Extension `browser-porch/extension/service-worker.js` handles `chat.turn` without `BOOT_ENVELOPE` and without invoking the automatic swarm continuation loop, opens a dedicated nonforeground Chrome tab per (sessionId, channel), reuses it for later turns, and persists a pre-send attempt receipt to avoid double submission on ambiguous errors.
- The extension reads an actual new assistant DOM response after the prior assistant baseline. It returns text + matching session/turn IDs and tab ID. A later human accepts or rejects content; `verifiedTurn:true` never implies self-acceptance.
- Protocol and authenticated relay integration tests in `browser-porch/ritsu-turn-protocol.test.mjs` and `browser-porch/ritsu-chat-relay.test.mjs`.
- GitHub Actions workflow `ritsu-chat-control-contract.yml` exercises these tests + existing Chromium Throne relay/extension core regressions.

## Crucial deployment boundary
THIS IS A BRANCH-TESTED TRANSPORT IMPLEMENTATION, **NOT** YET ANDROID TEXT-CONTROL OR A LIVE CHATGPT ROUNDTRIP.
- New Chrome extension and relay source must be packaged/deployed to the exact **Chromium Throne** dedicated profile on THECAULDRON and verified, not Browser Nerve or generic Chrome.
- A secure **Home Center ingress** is still required for the Android Ritsu app to enqueue authenticated text turns and fetch durable replies. Do NOT expose the existing localhost Throne capability directly to a public or LAN socket or put Throne bearer in an APK. It currently listens on `127.0.0.1:9234` for a reason.
- Android cockpit needs text input, send/confirm, session selection, readback status and explicit retry/reconciliation UX; this is next development slice.
- A canary is only externally accepted if same-session ChatGPT submission, browser-confirmed assistant reply, Home Center receipt/readback, phone delivery, and the user's visible confirmation all match by `turnId`.
- No automatic browser wake-from-sleep is proven; background tabs may operate while Chrome is running, but not after computer shutdown/hibernation.

## Why not host Chromium Throne on phone first?
Standard Chrome Android has no Chrome desktop-extension support; the existing Throne extension cannot simply be moved. The authenticated profile already exists on desktop, whereas experimental Android automation often depends on ADB/awake-device semantics and more fragile background scheduling. Future browser adapters may provide a phone-local option behind **the same** Home Center turn schema. This is a swappable actuator, not an Android-vs-desktop religious war.

## No-op / failure truth table
- command queued: not yet sent to ChatGPT
- command leased: extension owns lease, still not proof submitted
- uncertain: browser may have submitted; **never blind resend**
- failed: exact error/receipt required
- completed: DOM observed reply tied to turn, NOT yet delivered to phone or accepted by owner
- home-center delivered: only after cloud/phone routing implemented, authenticated, and verified
- owner accepted: after owner confirmation
