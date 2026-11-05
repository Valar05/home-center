> **SUPERSEDED for the user goal of assistant reply recovery:** The network-only attempt below remains a truthful *historical blocked checkpoint*, but Home Center and Playwright subsequently **retrieved and UTF-8-verified a real assistant reply**. See [RITSU_PLAYWRIGHT_RETURN_PATH_PROVEN_20261023.md](RITSU_PLAYWRIGHT_RETURN_PATH_PROVEN_20261023.md). The Playwright path is primary; do not resume network SSE reverse-engineering before the next structured-output acceptance test.

# Ritsu network text-return: live checkpoint (2026-10-23)
Mission: Prove a COMPLETE, EXACT ChatGPT assistant-visible answer can be retrieved by a deterministic Home Center-controlled reader from one authorized existing Chromium Throne network stream before enabling speech or autonomous code execution.

## Current capability and source
- Active feature branch: `feature/ritsu-command-bridge-scavenge-20261022`, PR #387. Pinned latest tested code SHA `59f30309d115192f1391bd992c2db09775520cfa`.
- Code: `browser-porch/ritsu-network-sse.mjs`, test `browser-porch/ritsu-network-sse.test.mjs`, pinned campaign `tools/campaigns/ritsu-network-probe-campaign.mjs`, CI `.github/workflows/ritsu-network-response-proof.yml`.
- Exact pinned THECAULDRON checkout in isolated local app data; nine Node SSE regression cases PASS through connected Home Center Computer Hands. GitHub independent contract tests also passed for preceding SHA.
- Existing Chromium-for-Testing CDP `:9236`, explicitly bound test conversation/tab, no new tab, no assistant DOM/screenshot reply extraction, no voice changed.
- Windows Computer Hands worker itself online and able to dispatch command, stage Git, run unit tests, start process, and retrieve durable receipts.
- Git/LFS snag: initial checkout failed fetching old missing LFS binary; exact-Git-SHA worktree with smudge disabled succeeded, without modifying the main checkout.
- Windows Computer Hands `shell.exec` sometimes reports `stdout did not close after process exit` when initiating detached background campaign; `process.start` executed the pinned Apply and returned PID, avoiding the misleading transport error. Always reconcile against actual durable campaign receipt rather than shell ticket alone.

## Live network findings
- Real browser POST stream observed and collected through `Network.streamResourceContent` and `Network.dataReceived.data`.
- One ChatGPT action yielded *multiple* conversation HTTP requests. Bounded per-request tracking now distinguishes them.
- Live payload protocol is compact SSE delta with `p/o/v/c`, inherited compressed frames `v/c`, and `message_marker`, not only full `message` snapshots. Never concatenate arbitrary messages or thinking/tool events.
- Exact 2026-10-23 live campaign `ritsu-net-proof-bound-20261023-008` at SHA `59f30309d115192f1391bd992c2db09775520cfa` wrote `schema_diagnostic` and `blocked: no_terminal_network_reply_with_canary_marker`. Main response request had 8,446 captured bytes, 17 parsed SSE events, `terminalDone=true`, `seeded=true`, `visible=true`, `textCandidate=true`, `finished=false`; Chrome marked HTTP request `loadingFailed` after a terminal SSE. This is **not** a successful actual response retrieval.
- Code already accepts `[DONE]` plus user-visible marker without the old status field and reconciles Chrome `loadingFailed` if SSE itself reached `[DONE]`; 9/9 local tests PASS. However the **candidate text still lacked the unique canary marker**, most likely because some compressed deltas are not applied. Must diagnose field inheritance/patch semantics rather than relaxing canary matching, guessing a result, or reading DOM.
- Never persist raw auth headers, cookies, bearer tokens, reasoning data, or full arbitrary SSE payloads. Historical diagnostics record only bounded keys/type/channel/content metadata and counters.

## Next bounded slice
1. Add a *redacted structural delta trace* showing only safe `p/o` names, `v` primitive/object type and length, `c` channel and bounded event ordering. No response text, tokens, secrets, or user IDs. Test the redaction.
2. Derive/implement per-channel delta inheritance and message snapshot/append rules from the actual stream. Filter for user-visible assistant message only. Add synthetic regressions for text append, inherited path/op, multi-message isolation, partial delivery, and no marker/no terminal.
3. With approved preflight, execute ONE pinned no-new-tab canary through Home Center's existing `windows-hands-01` and verify a `retrieved` receipt containing exact assistant text, nonce, SHA256, original conversation binding, real terminal SSE. CONTROL can retrieve that text via Home Center, not from browser DOM. No phone speech or arbitrary code execution until this gate is earned.
4. Write verified target-side receipts. Current state is **IMPLEMENTED, TESTED LOCALLY, PARTIALLY OBSERVED ON LIVE BROWSER, NOT RETRIEVED**.

Voice and Git coding handoff remain downstream phases. This checkpoint is a continuation record, not a claim that the campaign completed.
