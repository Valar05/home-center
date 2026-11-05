# Home Center coding-chat handoff through existing Git campaigns
Date: 2026-10-23
Status: PROPOSED ARCHITECTURE ONLY. Not implemented, deployed, tested end-to-end, or authorized for arbitrary device execution.

## Owner correction
GitHub has not been the unreliable part. DO NOT replace its existing authoring, transport, revision-history, PR or CI functionality with a custom JSON source-code ingestion protocol. The bottleneck is relying on a ChatGPT *responding agent* to execute Home Center, Phone Hands, Computer Hands, or other action tools at the right time or at all.

Retain the existing Git script-campaign doctrine and let coding ChatGPT do most of the writing, editing, testing and GitHub publishing. Its **only mandatory returned handoff** is one of:
1. **Preferred: pinned GitHub URL** for an exact commit, PR head plus verified full SHA, or a committed named campaign script. Home Center resolves the URL with its authenticated GitHub integration and verifies exact immutable bytes/revision; a floating branch link is a locator, not a pin.
2. **Artifact reference** containing the proposed source, patch or campaign package with a verified hash and allowed provenance. Home Center must ingest and stage it to Git for reproducible execution, unless already versioned. Never assume a ChatGPT file link itself is a deployed artifact.
3. **Script/text directly in the completed ChatGPT answer**, only for a bounded small campaign candidate. Home Center stores it as inert untrusted text, validates it, and stages a pinned Git revision before execution. No user copy/paste and no immediate shell execution.

No special multi-file JSON envelope is required from the coding ChatGPT response. A small machine-readable footer/receipt MAY simplify deterministic detection (e.g. `CAMPAIGN_URL=<verified URL>`, `REVISION=<40-char SHA>`) but must never be treated as trusted authorization or proof. A well-scoped human-readable URL or artifact can be recognized by Home Center; ambiguity leads to REVIEW, not guessing.

## Clarification: preserve the existing executable campaign component
The user notes that previous Git campaigns **already usually include an executable component**. Do not invent a new runner/script format or make ChatGPT return custom execution JSON simply to automate this. Normally the coding chat can leave the existing campaign entrypoint (Plan/Apply/Status/Receipts/Stop or the project's already-authorized equivalent) in the pinned Git revision and return its URL. Home Center's deterministic controller chooses and invokes that **existing, allowlisted, reviewed entrypoint** through the established worker. The failure this aims to eliminate is the ChatGPT agent's unreliable attempt to invoke Phone Hands/Computer Hands and wait for it to complete, not necessarily a defect in the campaign script itself.

The executable component is **common, not an unconditional requirement** for every response: research, code review, documentation and artifact-only tasks may need no machine-side apply step. If there is no approved executable where a live apply is requested, mark the task NOT_READY rather than generate or run an ad hoc replacement. Conversely, if the existing script is actually defective, normal isolated tests and precise target receipts must expose that failure; don't assume ChatGPT invocation is always the only cause. Reuse campaign gates and the tested execution surface; no additional layer or new privileged executor unless evidence proves one is missing.

## Primary architecture
Authorized CONTROL commissions a bounded coding task in a known, explicitly bound authenticated ChatGPT conversation. ChatGPT uses GitHub itself as appropriate. The planned passive **browser NETWORK stream observer** identifies the complete response and extracts only a specific Git URL, artifact reference or source/script output, binding it to the correct job, session and conversation. No DOM screenshot/HTML scraping and no request that the coding ChatGPT invoke Home Center or machine-execution tools.

Home Center owns the durable job, capture, source resolution, provenance, policy, Git pin, validation, CI evidence, approval, execution, status, receipt and feedback. Reuse `CAMPAIGN_ETIQUETTE` Plan/Apply/Status/Receipts/Stop and the exact-Git-SHA disposable-checkout pattern. Home Center's existing Git integration is the source and transport authority; native Home Center/Computer Hands/Phone Hands workers are invoked **by Home Center's deterministic controller**, not by the ChatGPT coding agent.

## Suggested state machine
`COMMISSIONED -> CHAT_RESULT_CAPTURED -> SOURCE_RESOLVED -> PINNED -> VALIDATED -> TESTED -> READY_FOR_APPROVED_APPLY -> APPLIED -> TARGET_VERIFIED`
Unknown/incomplete browser stream is `CAPTURE_UNKNOWN`; unresolved/floating/unauthorized URL is `SOURCE_REVIEW_REQUIRED`; failing tests are `VALIDATION_FAILED`; ambiguous actuation is `APPLY_UNKNOWN`. None are silently retried or mislabeled DONE.

## Required validation and boundaries
- Match expected job/session/turn and trusted contract; reject URLs, scripts or artifact paths outside its allowlist; reject branch/hash mismatch, multi-candidate ambiguity, new unrequested services or source edits, secret/cookie leakage and unexpected code execution.
- Resolve candidate files and full SHA from GitHub by an authenticated Home Center call. Verify base revision, diff, mutable path allowlist, campaign script location, test commands, dependencies and runnable entrypoint against a contract originating **outside the coding model's answer**.
- The coding agent's test-pass claims are not evidence. Run actual syntax/unit/security/contract checks on the pinned source, then produce exact revision + CI/run readbacks and failure receipts.
- Scripts must be executed as untrusted code only in an appropriately isolated validation environment first. The generated script cannot broaden its own permissions by writing a manifest or asking for another tool.
- Allow automatic staging and bounded iteration; actual changes to THECAULDRON, phone, live services, browser sessions or production still require an already-approved target-specific campaign scope and successful preconditions. If authority is missing, leave the artifact READY_FOR_APPROVAL, not auto-apply.
- Preserve the current main Home Center checkout, working Chrome tabs, signed-in sessions, Tailscale, canonical Pocket voice/19643 relay, running audio processes, and Phone Hands/Computer Hands control terminals. Do not issue ad hoc shell chains.
- Persist job/attempt IDs and at-most-once apply receipts. On uncertain writes, reconcile actual worker/device state before retry. Capture output hashes, run command identity, target-side receipts and actual acceptance. Git commit/CI is not proof of running code.

## Minimal end-to-end demonstration
Commission ONE harmless test change. ChatGPT produces and commits a candidate on the designated feature branch, then returns only the pinned GitHub commit URL (or the permitted artifact/script fallback). The network observer captures the complete returned message. Home Center independently resolves the exact commit and checks the prescribed file/diff/tests, runs the authorized isolated Git campaign through the correct worker and retrieves its target-side receipt. CONTROL reads the verified result; any error goes back into a bounded coding follow-up.

**Not yet proven:** a deployed browser-network answer observer, external autonomous Home Center response-ingress controller, URL/artifact/script parser, verified Git campaign dispatch from that controller, or end-to-end device acceptance. The already callable Home Center Git and worker APIs establish reusable parts only.

Related work: `docs/campaigns/RITSU_CHAT_NETWORK_SPEECH_20261023.md` describes the independent network-observer-to-speech pipeline. This document defines its **coding-artifact consumer**, not a new ChatGPT tool dependency.
