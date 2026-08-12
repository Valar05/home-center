# Chromium Throne / Browser Porch

Status: **source implementation on branch; not yet installed or acceptance-proven on Drew's desktop.**

Chromium Throne is the desktop ChatGPT workflow organ for Home Center. The current design deliberately uses **one ordinary visible ChatGPT tab plus one Chromium extension side panel**. It does not require hidden browser processes, a second dashboard tab, copied browser profiles, cookies, credentials, or a parallel agent framework.

## Current boundary

This is a later compute organ, not the local-first bootstrap. Phone/Continue/Adam local coding must work independently first. Chromium Throne exists so that workflow can later borrow ordinary authenticated ChatGPT web capacity when useful.

The extension currently provides:

- one-tab ChatGPT targeting: the active tab must be exactly `https://chatgpt.com`;
- a side-panel commission box, persistent local queue, `Run now`, `Run next`, stop/resume, and checkpoint capture;
- fresh-worker mode, which reuses the **same browser tab** by navigating it to a fresh ChatGPT conversation before dispatch;
- a deterministic worker boot envelope headed by **`PORTCULLIS LOCKED`**;
- bounded local receipts for sent commissions and captured assistant checkpoints;
- no rate-limit bypass, account rotation, hidden-tab swarm, credential scraping, or cookie access.

## Worker boot contract: `PORTCULLIS LOCKED`

`PORTCULLIS LOCKED` is the execution-mode phrase. It intentionally reduces worker latitude rather than adding personality. Every fresh worker receives rules that:

1. preserve the requested outcome, owner, tool, execution lane, exclusions, evidence standard, and delivery surface;
2. prohibit silent substitution of adjacent tools, architectures, workflows, or weaker evidence;
3. allow creativity only inside the commission boundary;
4. separate requested, implemented, deployed, and proposed capability;
5. carry all earlier constraints through revisions;
6. continue until artifact plus acceptance evidence exists or a real external/user action is strictly required;
7. report the exact blocking boundary rather than manufacture substitute success;
8. re-read the commission after each completed unit and advance the next unmet acceptance criterion.

The phrase is a boot marker, not magic. Enforcement comes from the fixed envelope plus deterministic extension behavior and receipts.

## Extension files

- `extension/manifest.json` — MV3 declaration with `activeTab`, `scripting`, `sidePanel`, `storage`, and only `https://chatgpt.com/*` host authority.
- `extension/service-worker.js` — boot envelope, exact-origin gate, single-tab dispatch, fresh-worker navigation, DOM prompt submission, checkpoint capture, and bounded receipt storage.
- `extension/sidepanel.html` / `sidepanel.js` — one-panel queue/operator UI. No second web dashboard is required.
- `contract.mjs` / `relay.mjs` — earlier Browser Porch lease/receipt work retained for Home Center integration. The standalone side-panel path does not claim that relay integration is deployed.

## Desktop installation canary

1. Open Chromium/Chrome extensions and enable Developer mode.
2. Load unpacked: `browser-porch/extension/`.
3. Open exactly one normal authenticated `https://chatgpt.com/` tab.
4. Click **Chromium Throne** to open its side panel.
5. Enter a small observable commission and choose **Run now** with fresh worker enabled.
6. Verify the same ChatGPT tab becomes a fresh conversation and receives a prompt beginning `PORTCULLIS LOCKED.` followed by the exact commission.
7. After the response completes, press **Checkpoint** and verify the side panel shows the assistant text in a receipt.
8. Queue two commissions and use **Run next** twice; verify the queue advances without opening another browser tab.

Until that canary is run on the real desktop, the correct status is **implemented source, not deployed/accepted**.
