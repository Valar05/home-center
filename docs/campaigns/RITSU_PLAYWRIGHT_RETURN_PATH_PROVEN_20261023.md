# Ritsu Playwright return path: live text retrieval PROVEN (2026-10-23)

## Narrow acceptance verdict
**PASS for one simple, authorized, same-tab ChatGPT answer retrieved by Home Center through Playwright.** Do not generalize to multiline code/artifacts, unattended service deployment, voice playback, or autonomous execution until those are separately exercised.

- Proof source Git SHA: `0a61e0078aa00bf40cf7a2362806c9d08e76193b` on `feature/ritsu-command-bridge-scavenge-20261022`, PR #387.
- Implemented existing-browser reader: `tools/campaigns/ritsu-playwright/runner.mjs`. Pure deterministic policy: `tools/campaigns/ritsu-playwright/capture-policy.mjs`; pinned package `playwright-core@1.64.1`; unit tests `capture-policy.test.mjs`.
- Attached to owner-authorized existing Chrome-for-Testing at `127.0.0.1:9236`. Verified **exact target tab ID and conversation URL**; Playwright did not create a browser/tab and did not read a different chat.
- Windows Home Center `windows-hands-01` invoked the pinned runner through `computer_hands.request.create` `process.start`, then independently retrieved `%LOCALAPPDATA%\HomeCenter\RitsuPlaywrightProbe\latest.json` via `shell.exec`.
- Live job ID: `ritsu-pw-real-canary-20261023-003`. Receipt `state=retrieved`, source `playwright_existing_bound_tab_dom`, exactCanaryMatched `true`, stableSamples `3`, generationStopped `true`, baseline `6`, assistantCount `6`. Completion did not rely on DOM message counts increasing.
- Exact UTF-8 browser-rendered text, from independent Home Center Base64 bytes readback:

  `🦀 This Playwright response retrieval canary contains the exact marker RITSU_PW_378E97E248487A5DB95F.`

- SHA-256 of the above exact UTF-8 answer: `6f8be486dea325e5c29274a2f308583c4c139fdac9cc2cde7185bfffecb470a8`. Independently recomputed and matched.
- The default Windows `shell.exec` stdout rendered the emoji incorrectly (`dY??`) due to a terminal/PowerShell encoding boundary. Reading raw private receipt bytes as Base64 through Home Center and decoding as UTF-8 recovered the exact emoji and original saved text. **Use byte-preserving UTF-8 transport**, not default shell stdout, for future answer return.
- Six deterministic policy tests passed on THECAULDRON, and GitHub Actions **Ritsu Playwright Reply Contract** passed for the pinned SHA: https://github.com/Valar05/home-center/actions/runs/40043745738.

## Why earlier readers falsely failed

1. The direct Chrome network capture observed SSE but did not reconstruct modern compressed `p/o/v/c` deltas. Preserve that code as experimental only, not the primary answer pathway.
2. ChatGPT's current DIL frontend **does not expose** legacy `[data-message-author-role]` or `[data-testid="conversation-turn"]` selectors in the bound test conversation. Playwright's read-only structural inspection found `main [class*="bg-user-message"]` (user) and `main [class*="MarkdownRoot-"]` (assistant).
3. ChatGPT recycled its rendered turn containers (7 previously, 6 later), so `assistantCount === baseline + 1` failed despite visible prompt and answer. Identify the new user prompt and assistant reply by their unique random marker, not by container count.
4. The previous campaign's own output `blocked` was accurate until the final verified proof. Do not count prior attempted canary prompts as successful text retrieval.

## Stable initial interface
`node tools/campaigns/ritsu-playwright/runner.mjs --mode Plan|Inspect|Apply|Status|Receipts|Stop`

`Apply` requires exact pinned `--revision`, a unique `--jobId`, the authorized `--tabId`, and `--boundUrl`. Launch Apply using Home Center's Windows `process.start` rather than a foreground developer terminal. It creates append-only durable receipts and refuses duplicate IDs. `Inspect` returns bounded structural metadata; `Stop` latches cancellation. Browser controls remain restricted to the explicitly bound existing tab. Do not save or print arbitrary conversations, session headers, tokens, or cookies.

## What is *not* yet accepted
- A multiline Markdown/code/URL output test, including exact formatting and URL recognition, still needs its own receipt.
- Persistent response observer/automatic new-turn pickup is **not** deployed. The current proven path is one initiated canary through the operator campaign, not a background listener.
- Home Center still needs to turn the parser and receipts into a stable internal `assistant_reply` contract for other consumers.
- No direct Phone Hands/voice playback, arbitrary code execution, GitHub apply, or task runner was changed or authorized by this proof.
- CSS-renderer class changes and Playwright/Chrome CDP compatibility remain failure modes; keep a structural compatibility canary and fail closed.

## Next bounded slice
Test a multiline answer containing a code block and GitHub URL; verify the correct assistant message, full text and SHA with UTF-8 byte-preserving Home Center return. Then expose a Home Center response contract consumed by the existing Git-first script campaign interface. Reuse existing Git campaign executables rather than inventing a new privileged runner.

**Bottom line: the original prerequisite is now proven for simple text. Next gate is structured answer payload and unattended pickup, not another attempt to reverse-engineer SSE.**
