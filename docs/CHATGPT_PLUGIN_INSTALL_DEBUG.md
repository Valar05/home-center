# ChatGPT Plugin Install Debug

Type: Termux / ChatGPT MCP install diagnostics / Playwright Chrome evidence
Status: v1 runbook
Date: 2026-07-11

## Rule

Debug ChatGPT plugin or MCP app installation from Termux with Playwright Chromium as the primary ChatGPT surface.

Do not use the Android ChatGPT app as the acceptance surface. The app path is limited and may hide developer-mode, connector, OAuth, and MCP details. Shizuku/uiautomator evidence is fallback only.

## Command

```sh
cd /storage/emulated/0/Documents/GodotProjects/home-center
node tools/debug_chatgpt_plugin_install.mjs
```

The command checks:

- local Termux bootstrap state;
- Home Center pairing config at `~/.config/home-center/codex-hub.json`;
- Home Center MCP and Command Center MCP protocol health;
- shallow Command Center discovery and stale-schema fallback;
- Playwright Chromium desktop ChatGPT page state through Debian/proot;
- recent `mcp_connector_*` Cloud Run logs.

It writes the main report under:

```text
tools/chatgpt_connector_evidence/plugin_install_debug_<runId>.json
```

The Playwright artifact is written under:

```text
generated/chatgpt-plugin-debug/<runId>.json
generated/chatgpt-plugin-debug/<runId>.png
```

## Status Classes

- `ok`: backend checks are green and Playwright sees Home Center connected or installed.
- `blocked_user_action`: local pairing is missing, expired, or lacks a token.
- `blocked_local_setup`: Termux, Debian/proot, Node, npm, Playwright, or Chromium is not runnable.
- `blocked_backend`: Home Center or Command Center MCP protocol/tool exposure is stale or broken.
- `blocked_chatgpt_auth`: Playwright reached ChatGPT but the browser profile is not signed in or is behind verification.
- `blocked_chatgpt_ui`: ChatGPT loaded but reports connector/install failure or did not proceed to MCP after OAuth.
- `unknown`: evidence exists, but no layer produced a specific diagnosis.

## Bootstrap Boundary

This debugger may do local setup such as using Debian/proot, installing ignored `browser-worker/node_modules` with `--no-bin-links`, and reading the paired Home Center token config.

It must not automatically deploy Firebase Functions, rebuild or install the Android APK, delete OAuth state, or perform irreversible provider changes. When those are needed, the debugger reports the exact next command or evidence path.

## Useful Variants

```sh
node tools/debug_chatgpt_plugin_install.mjs --chatgpt-url https://chatgpt.com/
node tools/debug_chatgpt_plugin_install.mjs --skip-playwright
node tools/debug_chatgpt_plugin_install.mjs --skip-backend
node tools/debug_chatgpt_plugin_install.mjs --since-minutes 90
```

Use `--skip-playwright` only when diagnosing backend MCP state. It does not prove ChatGPT install state.

For interactive ChatGPT verification, headed Playwright requires a real X display. On this phone, direct script execution from shared storage may fail with `Permission denied`; always call the helper through `sh`:

```sh
sh tools/run_chatgpt_plugin_playwright_check.sh --headed --run-id chatgpt-login
```

If that reports `DISPLAY is not set`, Termux:X11 is not running. Xvfb is not enough for human verification because it is not an interactive visible display.

For the original active-phone-use constraint, whole-phone foreground takeover was forbidden and the accepted Android UI fallback was a bounded Chrome frame/window that the user could intentionally avoid:

```sh
sh tools/launch_chatgpt_chrome_frame.sh https://chatgpt.com/
```

The launcher requests Android freeform/windowed Chrome and writes evidence under `tools/chatgpt_connector_evidence/chrome_frame_<runId>.txt`. It refuses success if `dumpsys` does not show Chrome in a bounded/freeform task.

It also writes `tools/chatgpt_connector_evidence/chrome_frame_<runId>.learning.json`, a Home Center operation envelope for `app_control.record_run` and `browser_sessions.record_episode`. Submit that envelope with `node tools/submit_chrome_frame_learning.mjs --envelope tools/chatgpt_connector_evidence/chrome_frame_<runId>.learning.json` so the discovery lands in the Home Center cloud bucket instead of remaining a Termux-only note.

Retrospective: the bounded frame was useful for containment but fragile as a product workflow. Android can keep Chrome alive while hidden, `am start` and task move commands can fail or target the wrong task, keyboard/launcher/Termux focus can hide the frame, and OAuth spans multiple origins and sometimes leaks to the installed ChatGPT app. See `docs/CHATGPT_COMMAND_CENTER_CONNECTOR_RETROSPECTIVE.md`.

The newer product direction is a durable `human_authorized_foreground_task`: the user authorizes a named workflow, Command Center stores the task state, and a paired on-device worker advances the multi-page flow until completion or a human gate. This is different from a one-page foreground click script and different from the old frame-only fallback.

## Fast Learning Integration

If a ChatGPT connector/debug run becomes slow or painful, stop iterating the UI and promote the observation into Home Center app-control learning:

```sh
sh tools/learn_chatgpt_connector_frame_lane.sh --submit
```

This generator emits a Home Center operation envelope with:

- `app_control.put_profile` for the updated Chrome `chatgptCommandCenterConnector` workflow
- `app_control.record_run` for the redacted frame-lane observation
- `browser_sessions.record_episode` for browser-hands discovery

Use `--dry-run` to validate the envelope locally without cloud mutation. The next live run should start by reading the cloud profile and proving connector `Connected` state, not by replaying OAuth.



## Clean-Slate ChatGPT Web Verification

Use the Playwright-first clean-slate verifier when ChatGPT web must prove it can consume Home Center and Command Center after connector churn:

```sh
sh tools/run_chatgpt_clean_slate_verify.sh --run-id clean-slate-$(date +%Y%m%d%H%M%S)
```

For the final no-op proof, add `--verify-prompt`. The verifier uses a persistent Debian/proot Chromium profile, records screenshots and DOM summaries under `generated/chatgpt-plugin-debug/<runId>/`, and writes `clean_slate_result.json`. Clean slate means connector state only: do not delete Home Center cloud buckets, app-control profiles, browser episodes, or browser playbooks. If ChatGPT auth needs visible human action, use the bounded Chrome frame lane and stop if the frame is lost.
