# Local Orchestration Broker — governed contracts

This package contains the broker's fail-closed contracts and a minimal dependency-free local swarm. The swarm executes explicit argv arrays locally, stores queue/lease/receipt truth in SQLite, and keeps in-flight workers alive while one dispatcher generation drains and its successor takes new work. It opens no listener, uses no shell expansion, and does not move cognition into the dispatcher.

`NS` is preserved as an opaque literal route token. This package assigns it no invented expansion. Regnet QA remains the quality/evidence gate and Venice remains the separate final stop gate.

## Minimal local swarm

```sh
./swarm --db ~/.local/state/home-center-swarm/swarm.sqlite3 init
./swarm --db ~/.local/state/home-center-swarm/swarm.sqlite3 dispatcher-register --id local-v1 --identity-file ~/.local/state/home-center-swarm/local-v1.identity
./swarm --db ~/.local/state/home-center-swarm/swarm.sqlite3 dispatcher-activate --generation 1 --identity-file ~/.local/state/home-center-swarm/local-v1.identity
./swarm --db ~/.local/state/home-center-swarm/swarm.sqlite3 enqueue --key feature-1 --lane NS --argv-json '["python3","-c","print(\"worker alive\")"]' --retry-safe
./swarm --db ~/.local/state/home-center-swarm/swarm.sqlite3 run-one --generation 1 --identity-file ~/.local/state/home-center-swarm/local-v1.identity --worker local-1
./swarm --db ~/.local/state/home-center-swarm/swarm.sqlite3 status
```

For live replacement, register generation 2 and activate it with a bounded drain window. Generation 1 immediately loses new-claim authority, its exact unexpired worker leases may finish, and generation 2 starts other queued work. Expired safe work is retried with a higher lease token; ambiguous non-retry-safe work parks in `WAITING_EVIDENCE`.

## Authority boundary

- Venice mobile is the primary command/dispatch/receipt surface. ChatGPT supplies Venice cognition and orchestration; desktop ChatGPT Voice is only a diagnostic relay carrier. Home Center and the future broker own durable queue, identity, lease, process, repository, sacred-session, and receipt state.
- Zero-credit means deterministic local tools, local models, or access already included by the product. It never means quota bypass, unlimited compute, credential reuse, or API-key Agents SDK work.
- Commission hashes bind the commission ID, queue document/folder/revision/state owner, lane ID/owner, worker identity, exact operations, and mutating flag. Validators recompute that digest.
- Material transitions require exact capability states plus trusted, immutable, hashed, timestamped evidence. Queue compaction and approvals require complete persistent identities, replay registries, and compare-and-swap consumption.
- Findings require recipients, acknowledgements, and evidence. Approvals are scope- and digest-bound, expiring, and single-use. Sacred sessions retain exact identity and resume commands.

## Voice-to-local descriptor boundary

The package describes, but does not execute, `YIELD_LOCAL → LOCAL_OWNS_ACTUATOR → RETURN_TO_VOICE`. All three phases bind one transition, commission, lane, session, action, fencing token, lease digest, and terminal receipt. Local assembly and local playback are separate typed records. Playback requires its own audio lease.

Mobile envelopes bind device/app/build/account/session/conversation/turn, exact transcript hashes, event chains, expiry, durable offline idempotency, executor attribution, and an affirmative no-UI-typing rule. Deterministic `REFLEX` actions such as cache-first `DEVICE_TTS_STATUS` are non-cognitive; every other `COGNITION` action stays with ChatGPT as Venice. Continue, Qwen, and Ollama remain the durable offline coding spine and cannot author Venice cognition.

When real local Venice output is relayed, ChatGPT Voice is only the audible carrier. Venice remains the attributed speaker, Adam remains the interface narrator/orchestrator, and a trusted source receipt plus exact-word flag prevents invention or impersonation when Venice is unavailable. Piper is reserved for separately commissioned personal-touch durable audio and can neither auto-synthesize nor auto-play. Gemini and Orus are reserved for separately commissioned polished artifacts behind spending, delivery, publication, and human-acceptance gates. Every audio route has a text mirror.

Dynamic ASMR is an optional, muteable, nonsemantic projection under an audio lease. Hash-pinned pre-rendered cues have separate hit, miss, refill, ready, play-start, play-finish, play-fail, and muted receipts under bounded LRU/byte/time/decoded-memory policy. A miss skips the cue and keeps Voice/text moving. A failure parks only its affected lane: Piper degrades to text; ASMR to silence plus text; playback leaves assembly intact; Voice failure leaves Home Center/local commissioned work alive; transport timeout preserves the exact sacred session; ChatGPT quota exhaustion parks new ChatGPT work while local commissioned lanes continue. With no independent lane available, the system retains a text-visible recoverable gate. Safety gates still fail closed and degraded operation never invents success.

Append-only per-stream session/job/finding/receipt/approval/lease/offline-command/probe-consumption/cue events and rolling checkpoints prevent a context event horizon. A checkpoint is required before handoff, transport timeout, context compaction, lane switch, Voice shutdown, or quota park and binds the exact queue revision, per-stream watermarks, active leases, unresolved gates, sacred sessions/resume commands, pending receipts, and evidence pointers. A new Voice context advances nothing until it rebuilds from durable queue, registries, pending receipts, and offline commands at every exact watermark.

Here, local `multitask` means one supervisory Voice over many independently fenced local lanes—not one chat doing every job and not a promise of unmetered provider work. Adam remains the sole state owner; every lane has a unique owner/path/branch, a one-transition budget, and explicit operations. One failed lane parks while independent lanes keep rolling.

Groq and Hugging Face are optional experimental hidden multipliers only. Their envelopes bind provider/model/purpose/classification/privacy/cost/quota/expiry/idempotency/result/executor identity; absence never stops the core, Groq defaults disabled, and results remain quarantined until harvested into verified local artifacts, tests, jars, or skills. The exact phrase `additional quotes` remains unresolved, with `additional quotas` only a suggested correction. A paired desktop Codex app-server/CLI is described solely as a human-setup-gated included-quota candidate using managed OAuth/device-code and JSON-RPC threads/turns/events; it does not imply API-key access, UI typing, a Home Center executor, or a General ChatGPT response API.

## Verification

```sh
npm test
npm run check
npm run test:swarm
```

The package uses Node and Python standard-library components only and intentionally has no network client or production deployment configuration. Source-tested does not mean installed, callable, delivered, or accepted on the primary phone.
