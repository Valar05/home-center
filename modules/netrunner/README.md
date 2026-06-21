# Netrunner

Netrunner is an accessible-first browser capability inside Home Center.

Goal: let a user accomplish web tasks through conversation while the browser records, narrates, magnifies, and eventually assists with repeated workflows.

The browser is the execution layer.
The cloud brain is the product.

## MVP principle

Do not start with full automation. Start with training wheels:

1. User drives the browser.
2. Netrunner observes DOM flow, focus, clicks, page transitions, and user corrections.
3. Netrunner narrates and magnifies the current task.
4. Successful episodes become candidate discoveries.
5. Repeated discoveries become trusted playbooks.

## Visible v0 acceptance

The first APK should launch directly into Netrunner, load `https://example.com`, accept a typed URL, and expose Back, Forward, Reload, Highlight, Read page title, and Home Center controls.

## Child systems

- `browser-shell` - embedded browser/webview host.
- `accessibility-overlay` - focus spotlight, magnifier, large targets, read-aloud affordances.
- `dom-observer` - visible DOM, accessibility tree, focused element, landmarks.
- `episode-recorder` - safe event log for human-driven sessions.
- `playbook-engine` - applies learned site/task guidance.
- `voice-engine` - Cartesia-backed read aloud, local key storage, interruption controls.

## Non-negotiables

- Never store secrets in GitHub, prompts, logs, or plain Drive.
- Redact passwords, payment fields, tokens, private messages, and medical/legal identifiers by default.
- Require explicit confirmation before purchases, submissions, account changes, or recurring billing.
- Shared learning must be promoted through observed -> candidate -> tested -> trusted, never self-mutated globally.
