# Atom — phone command center

Atom is the phone-resident command surface. Chromium Throne is an add-on inside Atom, not a separate command room and not a requirement to operate ChatGPT manually.

## User contract

- The user states outcomes to Atom once.
- Atom owns durable mission state, routing, retries, diagnostics, and receipts.
- Chromium Throne exposes inspectable browser organs and evidence when browser work is useful.
- ChatGPT, Venice, Vlad, deterministic recipes, Computer Hands, and other workers are implementation lanes selected behind Atom; the user does not babysit their terminals.
- Offline commands are accepted locally and remain queued until routing is available.
- Every visible mission distinguishes queued, running, blocked, complete, delivered, and accepted state.
- Diagnostics are a first-class one-button surface.

## Phone runtime

`server.mjs` uses only Node built-ins and persists under `~/.local/state/atom`. `tools/install_atom_phone.sh` copies the runtime into Termux internal storage, creates `~/bin/atom`, installs a Termux:Boot hook, starts the local service, and verifies `GET /v1/atom/status`.

The mobile command center is served at loopback only by default. Chromium Throne lives at `atom/addons/chromium-throne/` and consumes typed relative Atom APIs. It contains no direct ChatGPT DOM automation.

## Current capability state

Implemented in source: local Atom host, durable command/receipt queue, diagnostics bridge, mobile Chromium Throne add-on, offline command queue, browser-organ observation contract, noexec-safe installer.

Not yet claimed: deployed on the primary phone; worker/router consumption of queued Atom missions; live Chromium tab control; accepted end-to-end command completion. Those require a primary-phone runtime receipt.
