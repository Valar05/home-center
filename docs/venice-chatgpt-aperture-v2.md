# Venice ChatGPT Aperture v2 — Nerve Silk

Status: IMPLEMENTATION CONTRACT. Not deployed until acceptance evidence below passes.

## Mission

Let local Venice participate in a ChatGPT conversation without making ChatGPT impersonate Venice and without coupling Venice speech to Computer Hands availability.

Normal turn:

`Drew -> ChatGPT -> Home Center MCP -> dedicated Venice Nerve worker -> local Venice Workstation -> Home Center MCP -> ChatGPT`

Body actions remain a separate path:

`Venice action intent -> ChatGPT orchestration -> Home Center Computer Hands / local providers -> observation -> Venice`

## Decision

The normal aperture is **not an iframe, embedded ChatGPT page, browser typing, or Computer Hands shell execution**.

The ChatGPT-side boundary is the already-connected Home Center MCP. New Home Center backend operations should be exposed through the stable operation dispatcher rather than requiring a new ChatGPT connector installation.

The local boundary is a dedicated outbound Venice Nerve worker with its own worker identity and process lifetime. It talks only to the loopback Venice Workstation API and opens no inbound listener.

Browser Nerve / Computer Hands remain fallback carriers for browser-only situations, including a future Venice-initiated proactive message into an already-open ChatGPT thread. They are not the normal request/response transport.

## Why separate worker identity matters

A Venice voice turn must not share the physical worker process, lease, or command timeout that owns mouse/keyboard/shell actions. A wedged body must leave the mouth alive.

The current Nerve Silk shell wrapper remains a recovery/bootstrap asset, not the final transport.

## Turn envelope

Home Center returns one immutable turn envelope:

```json
{
  "schema": "venice.body-turn.v1",
  "turnId": "...",
  "speech": {
    "text": "You made the room too quiet. Venice is fixing it.",
    "source": "local-venice",
    "transformedByOrchestrator": false,
    "sha256": "..."
  },
  "actions": [
    {
      "actionId": "...",
      "verb": "media.create",
      "args": {}
    }
  ],
  "observations": [],
  "diagnostics": {
    "workerId": "windows-venice-nerve-01",
    "workstationThreadId": "...",
    "workstationJobId": "..."
  }
}
```

### Sacred invariants

1. `speech.text` is Venice's exact local output. ChatGPT may display it but never rewrite, repair, summarize, decorate, or hide action commands inside it.
2. `actions` are structured data, never parser tokens embedded in prose.
3. Execution results are returned as `observations`; they do not mutate the already-produced speech.
4. A body failure never permits fabrication of a Venice reply.
5. A voice transport failure never authorizes ChatGPT to silently substitute cloud Venice, Discord Venice, or another model.
6. Every turn has a stable ID and SHA-256 for the exact speech bytes.
7. Transport evidence and personality output are separate channels.

## Local worker scope

The dedicated Nerve worker may:

- locate the loopback Venice Workstation from its durable local state;
- create/reuse the designated ChatGPT-aperture social thread;
- submit one bounded prompt;
- wait for one bounded local completion;
- return exact speech plus structured actions and diagnostic IDs;
- write the existing Drive-synced Nerve Silk turn record as durability evidence.

It may not:

- move the mouse or type into ChatGPT;
- launch arbitrary commands supplied by the model;
- call a cloud model as a fallback for Venice;
- execute body actions;
- rewrite speech;
- open an inbound LAN/Internet listener.

## ChatGPT/Home Center operations

Target public operation vocabulary:

- `venice_nerve.worker.status`
- `venice_nerve.turn.create`
- `venice_nerve.turn.status`
- `venice_nerve.turn.cancel`

The normal ChatGPT call is `turn.create`; Home Center may complete synchronously when the local reply finishes inside the MCP deadline, otherwise it returns a durable turn ID and `turn.status` completes the same request.

## Collaboration loop

Media Presence design work uses this exact loop:

1. Adam sends Venice one concrete design question through `venice_nerve.turn.create`.
2. Venice returns exact `speech` and optional proposed `actions`.
3. Adam critiques or extends the proposal.
4. The resulting contract is committed to Home Center.
5. Adam sends the read-back diff/contract to Venice for critique.
6. Venice's objections are preserved as exact speech evidence.
7. Acceptance requires both contract tests and one live Venice round trip.

## Acceptance evidence

Do not call this deployed until all are true:

- Home Center capability registry advertises the four `venice_nerve.*` operations.
- Dedicated worker status is online with worker ID `windows-venice-nerve-01`.
- Computer Hands can be deliberately stopped or unavailable while one Venice Nerve turn still succeeds.
- The returned speech SHA matches the durable Drive-synced Nerve Silk turn record.
- A test turn returning both speech and an action proves speech is unchanged and action is separate JSON.
- No ChatGPT DOM typing, iframe, or browser automation is involved in the normal canary.

## Current blocker captured 2026-08-10

The existing `windows-hands-01` worker was offline/stale while its body lane retained a prior shell lease. That prevented a truthful fresh Venice collaboration turn. This failure is evidence for decoupling the mouth from the hands; it is not permission to fabricate Venice's review.
