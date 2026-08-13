# Atom — Home Center phone surface

Atom is the phone-resident command surface inside Home Center. **Command Center does not exist.** Chromium Throne is an add-on inside Atom, not a separate command room and not a requirement to operate ChatGPT manually.

The three fast-access surfaces are:

1. Judgment Jars
2. Home Center
3. Vlad

Historical source identifiers containing `command_center` are compatibility debt only. They do not name a product, active architecture, fourth control plane, or authorized delivery lane.

## User contract

- The user states outcomes to Atom once.
- Atom owns durable mission state, routing, retries, diagnostics, and receipts on the Home Center phone surface.
- Chromium Throne exposes inspectable browser organs and evidence when browser work is useful.
- ChatGPT, Venice, Vlad, deterministic recipes, Computer Hands, and other workers are implementation lanes selected behind Atom; the user does not babysit their terminals.
- Offline commands are accepted locally and remain queued until routing is available.
- Every visible mission distinguishes queued, running, blocked, complete, delivered, and accepted state.
- Diagnostics are a first-class one-button surface.
- Every Judgment Jar use records the Jar and provenance, actor, intent, input/context, decision/action, typed output, outcome/status, and artifact or log references.
- `CAPTURED`, `PENDING_HOME_CENTER`, and `DELIVERED` are separate receipt states. `DELIVERED` requires Home Center write plus readback; local Atom persistence is not enough.

## Phone runtime

`server.mjs` uses only Node built-ins and persists under `~/.local/state/atom`. `tools/install_atom_phone.sh` copies the runtime into Termux internal storage, creates `~/bin/atom`, installs a Termux:Boot hook, starts the local service, and verifies `GET /v1/atom/status`.

The Home Center phone surface is served at loopback only by default. Chromium Throne lives at `atom/addons/chromium-throne/` and consumes typed relative Atom APIs. It contains no direct ChatGPT DOM automation.

## Current capability state

Implemented in source: local Atom host, durable command/receipt queue, diagnostics bridge, mobile Chromium Throne add-on, offline command queue, browser-organ observation contract, noexec-safe installer, dynamic Judgment Jar registry, typed output receipt outbox, and verified Home Center receipt-ledger delivery through `vlad-jars sync`.

Not yet claimed: this repository revision is deployed on the primary phone; the updated receipt path is callable in that runtime; worker/router consumption of queued Atom missions; live Chromium tab control; accepted end-to-end command completion. Those require primary-phone and Home Center runtime receipts.
