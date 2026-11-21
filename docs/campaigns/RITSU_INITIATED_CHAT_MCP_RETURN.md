# Ritsu initiated-chat return: MCP first, no screen scraping
2026-10-23

## Owner's primary acceptance
"I would say your end goal should be to be able to retrieve the result of a chat that you initiate."
"It should be noted that the retrieval should probably happen through mCP so we don't resort to screen scraping."

**Therefore: a Home Center agent must initiate a real ChatGPT turn and retrieve its answer as structured Home Center MCP data.**

### What the existing UI relay cannot prove
- Chrome opening a page or injecting text is not an answer.
- A user-message DOM node is not an assistant reply.
- The old `waitForCompletedAssistant` extracts ChatGPT text via DOM inspection. Rewrapping that output in an MCP call **does not satisfy no screen scraping**. It remains a legacy diagnostic, not the accepted retrieval path.
- There is no currently verified native Home Center MCP operation capable of returning arbitrary ChatGPT conversation results. The new callback operations are **authored but not yet deployed**.
- MCP itself does not grant access to another private ChatGPT conversation. The **responding agent must be able to invoke the connected Home Center MCP publisher**; this must be verified in the actual target chat and cannot be inferred from the initiator's connection.
- Do not silently substitute paid OpenAI API calls or pretend that API response IDs are ChatGPT app conversation IDs.

### Protocol: responding-agent callback
Server code: `functions/ritsu_chat_callback_api.js`. Stable `drive_operation` registry additions:

1. Initiator invokes `ritsu.chat.prepare` with one stable `requestId` (turn), `sessionId`, and `channel=control`. Home Center stores an **owner-scoped, immutable prepared ticket**. A random single-use callback secret is returned **only on first prepare**, stored hashed server-side.
2. Initiator commissions a ChatGPT thread through the existing authorized ChatGPT ingress, providing its task, the ticket identity, and an explicit requirement: once it has composed its final answer, invoke connected Home Center MCP `drive_operation` with `operation=ritsu.chat.publish`, `args={requestId,sessionId,channel,callbackKey,text}`. The tool's output is the durable completion receipt.
3. The initiating agent calls Home Center MCP `drive_operation` with `operation=ritsu.chat.result`, `args={turnId}`. The result is `prepared` with `text=null` until the responding agent actually calls publish; after the call, result returns the exact immutable text. Polling is read-only; never resend a chat when status is pending or uncertain.
4. The acceptance proof is a **real target-agent MCP publish**, same owner/turn/session/channel, followed by **initiator MCP retrieval of exact text**. A callback is a claim from a model agent, not cryptographic proof of model identity; do not label it a native OpenAI API retrieval.
5. No automatic new Chrome tabs; explicit existing-tab binding and at-most-once send rules remain mandatory. There is **no DOM/screenshot extraction of assistant reply** in this proof.

### Current execution gate
- [x] Git callback API authored and Home Center's stable dynamic operation registry wired in source.
- [x] Tests cover owner scoping, callback secret, immutable publication, no browser page-extraction APIs, pending/null result, and readback.
- [ ] CI is green for the exact pinned callback revision.
- [ ] New Home Center MCP functions deployed and the remote `capabilities.operationSurfaces.drive.operations` lists all three operations.
- [ ] The *target* ChatGPT conversation can invoke Home Center MCP `ritsu.chat.publish` (not assumed).
- [ ] One real initiated chat publishes actual answer, then initiator retrieves that answer over MCP and displays it.

### Secondary priorities, only after first verified MCP result
Android send/receive, Pocket TTS, and parallel assistant/worker lanes. Keep per-session instances; only the main CONTROL thread decides publication. Never widen scope to hardware or speech until the small typed MCP response loop works.

Campaign etiquette: Git commit + pinned SHA + tests, then **one final bounded deployment campaign**, not a stream of ad hoc Windows commands. Cloud Home Center MCP deployment is a separate explicit campaign gate, not accomplished by Git authoring alone.
