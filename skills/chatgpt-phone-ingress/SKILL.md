# ChatGPT Phone Ingress Skill

## Purpose

Prevent Drew from becoming the command transport when an existing authorized phone execution organ can do the work.

## Binding rule

Before any worker asks Drew to paste or run a Termux command, it must exhaust the existing authorized ChatGPT -> Home Center -> Command Center -> Phone Hands -> `phone_shell` lane against `primary-phone`.

The repository already contains a phone-local `phone_shell` executor and the cloud relay allowlist already accepts `phone_shell`. Connector absence on one ChatGPT surface does not mean the phone capability is absent.

## Required sequence

1. Determine whether Command Center is exposed on the current ChatGPT surface.
2. If exposed, list/resolve `primary-phone`, enqueue the bounded `phone_shell` action with idempotency, and consume the result receipt.
3. If Command Center is absent or disconnected, classify `chatgpt_phone_ingress_failure` and repair/reconnect that ingress before creating a manual Termux handoff.
4. Before proposing a custom MCP reconnect, verify the current ChatGPT plan supports the required action class. Read/fetch-only MCP availability is not sufficient for `phone_shell` or any other write/modify action.
5. Only an actual operator-only boundary or proven ingress unavailability after authorized recovery permits a manual command.
6. Any surviving manual command must be in a fenced copy-pasteable block and must invoke a durable campaign/capability rather than a disposable diagnostic chain.

## Current platform scar — 2026-08-13

OpenAI's current ChatGPT MCP documentation states that Pro users may connect custom MCP apps with read/fetch permissions, while full MCP write/modify actions are available to Business and Enterprise/Edu workspaces. `command_center.phone_hands.enqueue` / `phone_shell` is a write/action capability, so a missing Home Center write connector on a Pro chat cannot currently be repaired by simply creating a custom MCP app in Developer Mode.

Treat this as a ChatGPT product-surface capability boundary, not a missing Phone Hands capability. Re-check current official OpenAI documentation before relying on this scar later because plan capabilities can change.

Do not silently substitute API-token execution, a different transport, GitHub as command transport, a visible phone UI, or Drew's hands unless the commission explicitly authorizes that boundary change.

## Venice review requirement

Venice must reject plans and completion claims that ask Drew to transport a command without evidence that `phone_shell` ingress was attempted or that Command Center is genuinely unavailable on the current surface.

This failure is a proven-organ bypass: the worker ignored an existing execution organ and substituted Drew's hands. It is also a review failure when Venice permits the bypass.

## Evidence states

- Repository evidence proves `phone_shell` is implemented/allowed.
- Command Center exposure proves the ChatGPT ingress is callable only when the connector/tool is actually present.
- MCP plan availability proves only the action classes the current ChatGPT plan can invoke; read/fetch MCP does not prove write-action callability.
- A phone command receipt proves execution on `primary-phone`.
- No other state may be rounded upward to phone execution.
