# Local Orchestration Broker — governed contracts

This isolated package defines pure data contracts and fail-closed policy for a future Home Center local orchestration broker. It starts no server, opens no browser, invokes no adapter, synthesizes or plays no audio, dispatches no work, and mutates neither Home Center nor a local machine.

## Authority boundary

- Browser Chat and ChatGPT Voice are supervisory apertures. Home Center and the future broker own durable queue, identity, lease, process, repository, sacred-session, and receipt state.
- Zero-credit means deterministic local tools, local models, or access already included by the product. It never means quota bypass, unlimited compute, credential reuse, or API-key Agents SDK work.
- Commission hashes bind the commission ID, queue document/folder/revision/state owner, lane ID/owner, worker identity, exact operations, and mutating flag. Validators recompute that digest.
- Material transitions require exact capability states plus hashed, timestamped evidence. Queue compaction requires a matching unexpired fenced lease and compare-and-swap revision.
- Findings require recipients, acknowledgements, and evidence. Approvals are scope- and digest-bound, expiring, and single-use. Sacred sessions retain exact identity and resume commands.

## Voice-to-local descriptor boundary

The package describes, but does not execute, `YIELD_LOCAL → LOCAL_OWNS_ACTUATOR → RETURN_TO_VOICE`. Local assembly and local playback are separate typed records. Playback requires its own audio lease.

When real local Venice output is relayed, ChatGPT Voice is only the audible carrier. Venice remains the attributed speaker, Adam remains the interface narrator/orchestrator, and a source receipt plus exact-word flag prevents invention or impersonation when Venice is unavailable. Piper is reserved for separately commissioned personal-touch durable audio and can neither auto-synthesize nor auto-play. Gemini and Orus are reserved for separately commissioned polished artifacts. Every audio route has a text mirror.

Dynamic ASMR is an optional, muteable, nonsemantic projection under an audio lease. A failure parks only its affected lane: Piper degrades to text; ASMR to silence plus text; playback leaves assembly intact; Voice failure leaves Home Center/local commissioned work alive; transport timeout preserves the exact sacred session; ChatGPT quota exhaustion parks new ChatGPT work while local commissioned lanes continue. Safety gates still fail closed and degraded operation never invents success.

Append-only session/job/finding/receipt events and rolling checkpoints prevent a context event horizon. A checkpoint is required before handoff, transport timeout, context compaction, or lane switch and binds the exact queue revision, compaction watermark, active leases, unresolved gates, sacred sessions/resume commands, and evidence pointers. A new Voice context advances nothing until it rebuilds from the durable queue, registry, and pending receipts at the exact watermark.

Here, local `multitask` means one supervisory Voice over many independently fenced local lanes—not one chat doing every job and not a promise of unmetered provider work. Adam remains the sole state owner; every lane has a unique owner/path/branch, a one-transition budget, and explicit operations. One failed lane parks while independent lanes keep rolling.

## Verification

```sh
npm test
npm run check
```

The package uses Node built-ins only and intentionally has no lockfile, network client, executable entry point, production route, adapter implementation, or deployment configuration.
