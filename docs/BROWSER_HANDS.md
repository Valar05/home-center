# Browser Hands

Type: Home Center web automation / accessibility / learning substrate
Status: v1 contract
Date: 2026-07-11

## Product Rule

Playwright is an essential Home Center app function for browser hands. It is not an optional smoke tool and not a one-off novelty.

Home Center uses Playwright desktop Chromium as the primary web execution surface because the target is the full desktop web feature set. Mobile UX is not the priority. Chrome remains the first target; Amazon is not prioritized for v1.

Shizuku still matters, but for a different layer: Android Chrome launch, freeform/subframe control, device focus, screenshots, and fallback manual lanes. Shizuku does not replace Playwright for browser DOM, accessibility tree, desktop-mode replay, or reusable web task learning.

## Host Requirement

Playwright is a required app capability, but it is not run inside Android/Termux Node. The preferred phone-local v1 execution host is Debian/proot on the Android device, using Debian-native `/usr/bin/node` plus Debian `/usr/bin/chromium`.

Desktop/cloud workers are fallback capacity for heavier jobs or other household machines. They are not the acceptance target for proving this capability on Drew's phone.

If a browser task must touch Android Chrome itself, use Shizuku/Chrome app-control as the bounded fallback lane and still record learning into browser/app-control records.

## Runtime Shape

```text
Home Center / ChatGPT / Android app
  -> command_center_operation browser_sessions.*
    -> Command Center browser session + learning records
      -> registered browser worker
        -> browser-worker package
          -> Debian/proot Playwright desktop Chromium on device
```

The runtime package is `browser-worker/`. It owns Chromium launch, DOM/accessibility snapshots, constrained actions, redaction, and local episode artifact generation.



## First Painful, Second Automatic

Home Center's browser-hands learning contract is household leverage: when Drew painfully uses a website once and the run is verified, Home Center can promote that successful Playwright DOM/accessibility path into a trusted playbook that June can run automatically later. The reusable unit is `origin + taskKey`, not exact pixels or a phone layout.

Playbooks must store selector ladders built from stable web semantics: `data-testid`, HTML `id`, `name`, label text, ARIA label, role/name, href/form metadata, and only then visible text. Android bounds and screenshots may document containment or failure evidence, but they are not the automation strategy and cannot be the only promoted selector.

Second-use replay is automatic with gates. Home Center may fill, navigate, search, filter, and click non-sensitive controls from a trusted playbook. It must stop for CAPTCHA, login verification, payment, purchase, deletion, account-security changes, or any irreversible final action unless a narrower future whitelisted policy explicitly covers that action.

## Human-Authorized Foreground Task

Some web workflows cannot be usefully handled through background Playwright or a frame-in-frame lane because the user is already in the real authenticated browser session. Home Center supports a separate **human-authorized foreground task** lane for that case.

Contract:

- The human authorizes a named task, not just a current page.
- The task declares allowed packages, allowed origins, expected transitions, and human gates.
- The agent may rapidly take over the full foreground browser flow for that task. No frame-in-frame is required.
- The agent batches observation, selector extraction, typing, clicks, and evidence capture; it must not do slow terminal round-trips for each tiny action.
- The human clicks only human-required gates: CAPTCHA, login verification, payment, purchase, account security, destructive action, or consent not already authorized for the workflow.
- The agent stops at task completion, unexpected origin/package, focus loss, sensitive gate, or stale selector evidence.
- Every burst records `app_control.record_run` and `browser_sessions.record_episode` so the first painful use can become a faster Home Center playbook.

This is not background automation and not a default fallback. It is foreground control with explicit task-scoped consent. The acceptance metric is speed plus clean handoff: a burst should be measured in seconds, not a long visible click script.

Foreground task learning still cannot promote coordinate-only browser behavior to trusted playbooks. Trusted replay must extract DOM/accessibility selectors with Playwright or an equivalent semantic browser channel before it can serve June-style automatic assistance.

The ChatGPT connector retrospective is the current concrete case study: `docs/CHATGPT_COMMAND_CENTER_CONNECTOR_RETROSPECTIVE.md`.

## Command Center Visual QA

Command Center visual QA is a browser-worker responsibility, not a generic
Codex executor proof. A verified final-render lane must produce a terminal
Command Center job with a completed browser episode and artifact records for
`visual_qa_manifest.json`, `screenshot.png`, and `browser_episode.json`. A
`browser_sessions.act` record with status `requested` is only a request; it is
not screenshot evidence and must not be used as visual acceptance.

The browser-worker capture CLI is:

```sh
npm run visual-qa -- --url HOSTED_URL --target crimson-sword --job-id JOB_ID --session-id SESSION_ID --out-dir generated/visual-qa/RUN_ID
```

For final-render debugging, keep the screenshot, screenshot SHA, console/network
log, DOM/accessibility summary, browser episode, and page debug payload together
so ChatGPT can inspect the same cloud evidence Pose Lab consumes.

## Learning Contract

Every browser invocation must record a redacted episode through:

```text
operation: browser_sessions.record_episode
```

Episodes become candidate discoveries. Candidate discoveries become trusted shared behavior only through explicit promotion:

```text
operation: browser_discoveries.promote
```

This preserves the Home Center rule: record first, extract patterns second, automate third.

## Accessibility Contract

Browser hands must support June-style web assistance:

- narratable page title and visible text summary;
- focused element and available actions;
- accessibility tree or landmark summary;
- manual blocker narration;
- safe resume/stop points;
- no hidden final actions.

Sensitive actions are always human-controlled: CAPTCHA, login verification, payment, purchase, account security, destructive account changes, and anything equivalent.

## V1 Chrome Target

Default surface:

```json
{
  "runtime": "playwright",
  "browser": "chromium",
  "mode": "desktop",
  "userAgentMode": "desktop"
}
```

Android Chrome may be linked through app-control profiles and Shizuku when the Chrome app itself is the execution surface, but the first browser-hands implementation is Playwright desktop Chromium running locally through Debian/proot when the worker is on a phone.

## Chrome Frame Learning

Real Android Chrome frame discoveries belong to the same Home Center browser-hands learning path as Playwright runs. The frame launcher is a Termux runner, not a separate product workflow.

A bounded Chrome frame run must write a Home Center learning envelope containing both:

```text
command_center_operation app_control.record_run
command_center_operation browser_sessions.record_episode
```

Use `tools/chrome_frame_learning_envelope.mjs` to build that envelope and `tools/submit_chrome_frame_learning.mjs` to submit it. Do not treat a `.txt` launcher log, a screenshot, or terminal stdout as the durable learning store.


## Clean-Slate ChatGPT Web Verification

Use the Playwright-first clean-slate verifier when ChatGPT web must prove it can consume Home Center and Command Center after connector churn:

```sh
sh tools/run_chatgpt_clean_slate_verify.sh --run-id clean-slate-$(date +%Y%m%d%H%M%S)
```

For the final no-op proof, add `--verify-prompt`. The verifier uses a persistent Debian/proot Chromium profile, records screenshots and DOM summaries under `generated/chatgpt-plugin-debug/<runId>/`, and writes `clean_slate_result.json`. Clean slate means connector state only: do not delete Home Center cloud buckets, app-control profiles, browser episodes, or browser playbooks. If ChatGPT auth needs visible human action, use the bounded Chrome frame lane and stop if the frame is lost.
