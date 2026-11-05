# Ritsu end-to-end runtime gate and receipts
Date: 2026-10-23
User commission: "Why don't you pick it back up?" after requesting full phone -> Home Center -> ChatGPT -> phone spoken reply before another handoff.

## Verified actions on THECAULDRON

Home Center's authorized `windows-hands-01` Computer Hands worker was live in Windows interactive session 1. The user has a separate, modified primary `C:\Users\dclar\workspace\home-center` checkout on `main`; that primary working directory, original Chrome extension installation, original localhost 9234 service and existing 19643 voice playback relay were left unchanged.

A clean, detached feature worktree exists at `C:\Users\dclar\workspace\home-center-ritsu-e2e`; an initial Git LFS checkout error was repaired using per-worktree no-smudge checkout, not destructive edits to main. The checkout was updated to `2d7dc846` and the Windows Node relay tests passed (9/9).

Isolated runtime test root:
- `%LOCALAPPDATA%\HomeCenter\RitsuE2E\extension`: Chromium Throne 0.8.0 staged extension, independent of installed 0.7.0 extension folder
- `%LOCALAPPDATA%\HomeCenter\RitsuE2E\relay-capability.txt`: randomly generated trusted local bearer, **NEVER COPY ITS CONTENT INTO DOCS OR APK**
- Isolated Node relay: `127.0.0.1:9235`, verified listener and bearer authorization
- Chrome for Testing in dedicated Chromium Throne profile: debugging on localhost 9236, staged extension ID `lccnchjcenaomhnjjaomabpajagenkaf`, Chrome extension manager reported `ENABLED`, `UNPACKED`, v0.8.0, no manifest warnings
- Side panel test page used to trigger the extension's native `throne.relay.poll` control
- This test configuration is **not** a production service and was still running at checkpoint time.

## Actual runtime fault and repair

Initial Chrome MV3 extension poll returned HTTP 403 `EXTENSION_ORIGIN_MISMATCH`. The Chrome-hosted extension request was missing an HTTP `Origin` header even though the extension was installed with correct ID, host permission, and matching 64-character localhost bearer.

Fix in `browser-porch/relay.mjs`: retain required high-entropy bearer, loopback listener, and rejection of **explicit** foreign or `null` origin; permit *absent* Origin specifically on bearer-protected Chromium Throne routes. Browser Porch pairing endpoints still require exact extension origin. Regression assertions added to `browser-porch/relay.test.mjs` and `ritsu-chat-relay.test.mjs`. [CI 39985781877](https://github.com/Valar05/home-center/actions/runs/39985781877) passed.

After applying patched `2d7dc846` to isolated Windows worktree and restarting **only** the isolated test relay, a Chrome extension request with intentionally invalid bearer changed from `EXTENSION_ORIGIN_MISMATCH` to `THRONE_CAPABILITY_MISMATCH`, proving it now reached bearer validation. The local relay tests also passed on Windows.

## Canary receipts (NO DUPLICATE POSTS)

`ritsu-e2e-real-canary-001`:
- One Home Center coordinator submit receipt `queued`, relay event `throne.command.queued`.
- It had **not** been leased. Before isolated relay restart, readback was `queued` and explicitly called the trusted `/v1/throne/cancel` endpoint, which returned `cancelled`. Durable event `throne.command.cancelled` confirmed. No blind retry.

`ritsu-e2e-real-canary-002`:
- New stable coordinator turn submitted once to authenticated patched relay; `queued` receipt.
- Native extension poll caused durable `throne.command.leased` event for `ritsu.ritsu-e2e-real-canary-002`. This **proves** Windows Home Center -> authenticated relay -> installed MV3 extension. It does not prove a ChatGPT prompt/reply.
- Chrome opened a dedicated dialogue tab. Read-only UI inspection showed both ChatGPT pages have no prompt composer and visibly offer `Log in`. The dedicated profile is **signed out**.
- Chrome extension storage readback contained a `ritsuChatSessions` mapping for `dialogue:ritsu-e2e-dialogue-20261023`, tab ID `1970722285`, and a `ritsuChatReceipts` row for the canary with state `unknown` (pre-send at-most-once marker). No ChatGPT canary text or user/assistant message was observed in the UI.
- Latest read of durable local relay audit file contained `queued`, `leased` but **no** `completed` or `failed` for canary 002. An authenticated coordinator poll attempted later was blocked by the platform; **do not route around that block or claim response success**.
- This ID is **uncertain**. NEVER blindly resubmit canary 002 even after sign-in.

## Further safety repair

`browser-porch/extension/service-worker.js` now invokes a read-only `requireRitsuPromptComposer(tab.id)` readiness gate **before** persisting the pre-send unknown receipt or running `submitChatGptPrompt`. If a login-required page appears, it fails with `ritsu_chatgpt_login_required` without touching ChatGPT or poisoning the at-most-once ledger. `ritsu-chat-relay.test.mjs` asserts this ordering. [CI 39987552950](https://github.com/Valar05/home-center/actions/runs/39987552950) passed for source head `1b23bda89ef06752752b2e01b3b4b8a4c54c125e`.

**The new preflight exists in committed source and CI but has NOT been reloaded into the still-running live Chrome test extension.** Do not claim the device runtime has that newer patch.

## Remaining hard acceptance and next authorized step

1. A user-authorized sign-in is required inside the dedicated Chromium Throne profile on THECAULDRON. Do not copy cookies, search for passwords, steal sessions, or hijack the separate existing `Throne\profile-cft136` or consumer Chrome. No way was found to safely reuse their authenticated state without perturbing them.
2. After sign-in, update only the isolated staged extension to commit `1b23bda...` or later and **reload the extension**, verifying v0.8.0 and source readback. Use an entirely NEW turn ID. Preflight should pass, Chrome should actually submit the prompt, and relay must show `leased -> completed` with text and exact tab/turn/session ID readback.
3. Phone -> Home Center authenticated input and Home Center -> Android result feed are **not implemented/deployed**. Android v0.8 still has no INTERNET permission and retains `WAITING_FOR_HOME_CENTER` local-only messages; a five-second Thoughtful pause is committed but not yet installed on the phone.
4. Ritsu's canonical TTS -> Tailscale :19643 -> Termux phone playback and clip-ID stop/voice barge-in remain to connect and hear-test. Do not substitute generic Android TTS or break the canonical audio laws.
5. Keep the initial architecture at one CONTROL main thread and one separate DIALOGUE thread; secondary/worker output remains staged until explicitly published by verified Home Center control turn. Coordinator instances are per namespace and not a singleton. More worker parallelism is deferred until a real conversation works.

No end-to-end user-accepted phone conversation yet. Next test should target exactly the remaining authorization and delivery links, not another simulated run.


## On-screen login recovery: October 23 follow-up
Owner reported **three off-screen Chromium Throne/Chrome windows** and closed them. Do not repeat a browser-session setup solely by opening a new Chrome tab or relying on CDP 'activated' as evidence it is visible.

Real THECAULDRON display inventory: one primary work area `X=0,Y=0,Width=1600,Height=1019` (display bounds 1600x1067). Dedicated Chrome for Testing/profile was no longer listening on debug 9236 after the owner closed its windows. Existing normal Chrome sessions remained separate.

We launched **exactly one** dedicated Chrome for Testing process (PID 15364), with the isolated feature's extension, the existing dedicated `%LOCALAPPDATA%\\HomeCenter\\ChromiumThrone\\profile`, debug `127.0.0.1:9236`, and startup flags `--window-position=90,70 --window-size=1120,820 --new-window https://chatgpt.com/`. Target window handle 4065886 was verified to be owned by PID 15364. Using Win32 `ShowWindow(SW_RESTORE)` + `MoveWindow` + `SetForegroundWindow`, got verified bounds `Left=100,Top=75,Right=1220,Bottom=895`. Independent `screen.capture` verified that **the window was truly visible and on top** without moving ordinary Chrome.

That Chrome for Testing window displayed ChatGPT's authenticated sidebar and full message composer. Independent CDP readback: `composer=true`, `navLibrary=true`, `loginButton=false`. No passwords, cookies or session tokens were copied or manipulated. No user sign-in was required on this recovered profile at that moment.

Using a NEW coordinator namespace `ritsu-visible-session-20261023`, control ID `ritsu-visible-control-20261023`, and dialogue ID `ritsu-visible-dialogue-20261023` to avoid silently recycling the closed tab's mapped session, we submitted ONE new canary `ritsu-visible-auth-test-20261023-01`. Receipts verified `queued` and `leased` from authenticated 9235 relay and Home Center CLI. **Latest verified state: LEASED, not completed**. No duplicate POST; do not retry its ID even if the Chrome wait times out. The current owner-visible window is no longer off-screen. The phone/ChatGPT/TTS full conversational loop remains incomplete.

**Permanent operating gate:** before asking owner to authenticate on THECAULDRON, verify monitor bounds, exact target window PID+handle, actual Win32 position fully inside work area, user-visible screenshot, and one—not multiple—Chrome for Testing windows. An authenticated ChatGPT message composer is checked separately from visibility and from proof of a completed ChatGPT reply.


## 14:09 CDT owner-reported five blank ChatGPT tabs: root cause and actual repair

Owner reported five ChatGPT tabs in dedicated Chrome for Testing with no submitted messages in conversation history. This was **confirmed, not a UI sync problem**:
- CDP at localhost 9236 listed five `https://chatgpt.com/` pages. Read-only inspection of all five verified zero user turns, zero assistant turns, empty editor drafts, and no attachments.
- **Root cause**: Chromium Throne `service-worker.js` only matched legacy `#prompt-textarea` / `[data-testid="prompt-textarea"]`. The real October 23 ChatGPT composer was `<div contenteditable="true" role="textbox" data-composer-markdown class="ProseMirror" aria-label="Ask ChatGPT">`. The submit function used `textContent` + synthetic InputEvent and a synthetic Enter-keydown fallback, then returned `ok:true` without any user-message acknowledgment. It could neither discover nor reliably operate the real ProseMirror editor.
- Source commit `30cd45ac` fixes the selectors in both readiness and submission, inserts text with Chrome's native `document.execCommand('insertText')` editing pipeline instead of assigning `textContent`, requires an enabled real Send button, and refuses to return `ok:true` unless a matching user-message DOM node appears after clicking. All fake Enter fallback removed.
- Regression commit `eb681691` tests ProseMirror selector, native editing, no synthetic success, and final user-message proof. [Ritsu Chat Control Contract run 40009987699](https://github.com/Valar05/home-center/actions/runs/40009987699) passed. On THECAULDRON the isolated `home-center-ritsu-e2e` worktree was updated to `eb681691`; real Windows relay tests 9/9 passed; changed extension script copied to `%LOCALAPPDATA%\\HomeCenter\\RitsuE2E\\extension\\service-worker.js` with SHA256 matching deployed source. Original main checkout and port 9234 untouched.
- Direct Chrome DOM-only test on a single blank ChatGPT tab verified `document.execCommand('insertText')=true`, expected draft rendered exactly, live `aria-label="Send"` button enabled/visible, and `execCommand('delete')` cleared the draft leaving zero messages. **No prompt was submitted in that diagnostic.**
- Closed four identified empty ChatGPT pages in dedicated 9236 Chrome instance only (four HTTP 200 DevTools close receipts). The isolated Chrome process was subsequently stopped/relaunched with the corrected staged extension. Readback after restart confirmed exactly ONE ChatGPT home tab. Separate normal Chrome sessions were not touched.
- Existing extension `ritsuChatSessions` mapped older conversation IDs to deleted numeric Chrome tabs; old at-most-once receipts remained `unknown` and were preserved. In fresh extension context, a new independently namespaced dialogue `dialogue:ritsu-e2e-fixed-dialogue-20261023` was explicitly bound to the only verified empty ChatGPT home tab ID `1970722556`, avoiding an additional worker tab. This did not alter old receipts.
- New at-most-once CLI canary `ritsu-editor-live-proof-20261023-001` was queued once to the existing authenticated isolated relay. The extension's `throne.relay.poll` was triggered once. The authoritative relay-result readback request was **blocked by platform safety checks**, so there is **NO verified lease, ChatGPT user message, captured assistant response, or final E2E success** for this canary. Do not automatically retry this ID. A later desktop screenshot showed regular Chrome, not test Chrome, so is not evidence either.
- An isolated Chrome-for-Testing PID 28196 displayed two top-level windows, including `Restore pages?` (handle 4131422), which blocked an attempted focus-by-PID. A narrowly verified request to dismiss only that modal was blocked by platform safety checks. **No workaround was attempted.** The operator must manually dismiss the Restore pages dialog if it persists.

**Unmet gate:** confirm one real ChatGPT user-message bubble and assistant response in isolated test Chrome under the **same session identity**, then exact Home Center receipt. After that, phone's authenticated ingress/feed and canonical audio return still need development. Do not claim client-visible completion from source tests, queued canary, button enabling, or extension-side poll trigger.
