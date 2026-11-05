# Ritsu real initiated ChatGPT reply retrieved through Home Center MCP

Date: 2026-10-23. Campaign: `ritsu-chat-voice-e2e`, primary acceptance subset "initiate an independent ChatGPT chat and retrieve its answer". This is an **actual model-agent MCP callback**, not a DOM scrape or simulated result.

## Production release
- [PR #390](https://github.com/Valar05/home-center/pull/390) merged a minimal four-file Home Center MCP callback slice to main, commit `5970c2d36668fa686e9ada01e08bc479b4717688`.
- [PR #391](https://github.com/Valar05/home-center/pull/391) repaired only ephemeral GitHub runner LFS normalization for two historically raw MP4 files, main commit `7c2e156069e4d73ff77cca76aac02c37367bf3fb`.
- [Production MCP deploy #40026817404](https://github.com/Valar05/home-center/actions/runs/40026817404) **SUCCESS**, using the preexisting, main-only `deploy-home-center-mcp-only.yml` campaign. No Chrome, Android, Pocket TTS, or user browser settings changed by cloud deployment.
- Live Home Center `capabilities` readback advertised `ritsu.chat.prepare`, `ritsu.chat.publish` and `ritsu.chat.result`.
- Owner-scoped cloud MCP smoke: prepared and retrieved pending result, then synthetically published a **clearly synthetic fixed marker**, and independently read it back. This proved cloud CRUD but was **not** treated as a real ChatGPT answer.

## One real browser-initiated chat test
- Exact tested Git source: `06f2cf6f86014cefe558ad48e05f2078eaebfe3f` (on `feature/ritsu-command-bridge-scavenge-20261022`).
- [Ritsu Chat Control Contract CI #40027693863](https://github.com/Valar05/home-center/actions/runs/40027693863) **SUCCESS**. Windows Computer Hands ran the *same* `tools/campaigns/ritsu-mcp-chat-initiate.test.mjs`: 4 passed.
- Single authorized Computer Hands campaign request: `ritsu-mcp-one-shot-real-chat-campaign-20261023`. The script `tools/campaigns/ritsu-mcp-chat-initiate.mjs` targeted exactly one **existing**, signed-in, blank test Chrome for Testing ChatGPT tab on loopback CDP 9236. It did **not** create another tab and did **not** extract any assistant reply from DOM/screenshot/CDP.
- One unique turn: `ritsu-mcp-real-target-20261023-001`. Session `ritsu-control-real-target-20261023`. Source browser tab ID `A67990116B5D70AEB70B14563740A470`.
- The browser campaign recorded pre-send `dispatch_unknown` and exited code 2 because it **could not confirm the user message appeared in the page**. This is an honest at-most-once ambiguity, not permission to retry; the original source journal was not overwritten.
- **Crucial independent success:** the target ChatGPT thread called the connected Home Center MCP tool to prepare/publish its own response. The *initiating* agent queried the production `ritsu.chat.result` operation **twice in separate MCP calls**, each returning `state=published`, `source=responding_chat_mcp_tool_call`, identical `turnId`, `sessionId`, `channel=control`, `publishedAtMs=1792791296463`, and exact durable text:

> 🦀 A persistent assistant should remember the campaign’s acceptance criteria: what counts as genuinely finished, which constraints must remain intact, and what evidence proves the result. That keeps a green test from masquerading as a completed mission.

- Production receipt explicitly declares `nativeApiProvenance=false`. This proves the **agent-invoked, owner-scoped MCP callback** and durable retrieval, not a native OpenAI ChatGPT Responses API signature. The model-published answer came back without scraping it.

## Acceptance verdict
**PASS for the user's narrowed primary goal:** an initiated ChatGPT thread publishes its reply by MCP and the initiator retrieves actual text by MCP. This is a real target-model interaction, distinct from the cloud CRUD smoke test.

**Open follow-on work (not part of this acceptance):** browser user-message acknowledgment robustness; ongoing independent thread scheduling and CONTROL merging; Android ingress/response UI; canonical Pocket TTS playback confirmation. Preserve the `dispatch_unknown` browser receipt and never repeat the old turn ID. No blanket claim of complete phone/voice embodiment.
