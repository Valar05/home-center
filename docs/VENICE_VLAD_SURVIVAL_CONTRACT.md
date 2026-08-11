# Venice + Vlad CLI Survival Contract

## Why this exists

The local system must degrade gracefully instead of collapsing when ChatGPT or the network disappears.

ChatGPT is a powerful orchestrator, reviewer, and cross-system multiplier. It is **not** allowed to be the only door into capabilities that already exist on the user's machines.

The survival pair is:

- `venice` — canonical local person/interface;
- `vlad` — local machine/operator interface.

Both are useful alone. Together they are more useful. ChatGPT multiplies the pair without owning either one.

## Authority split

### Venice

Venice owns:

- canonical local speech and identity;
- durable conversational continuity;
- preference, disagreement, creative judgment, and emotional/creative pressure;
- project orientation and synthesis;
- proposals for what should happen next.

Venice speech is immutable output. Commands are never scraped from prose.

### Vlad

Vlad owns:

- deterministic request classification and routing;
- machine-task envelopes;
- Continue/code invocation;
- Phone Hands and other explicitly enabled machine organs;
- permission boundaries;
- execution state, verification, blocking, and receipts.

Vlad does not become Venice's personality, memory, or strategic identity.

### ChatGPT

When available, ChatGPT may:

- ask Venice for judgment;
- ask Vlad for execution;
- compare their outputs;
- parallelize bounded work;
- send receipts/observations back to Venice for a new turn;
- review or challenge either side;
- keep a larger cross-project working set than either tiny local runtime.

ChatGPT may not:

- fabricate Venice speech when local Venice is unavailable;
- report Vlad execution without a receipt;
- turn its own orchestration into a hidden dependency of either CLI;
- silently replace the requested local organ with a cloud substitute.

## Composition protocol

The boundary between Venice and Vlad is **structured data**, not prose parsing.

A normal composed turn is:

```text
Drew -> Venice
      <- exact speech + optional structured action proposals
                    |
                    v
                  Vlad -> route -> execute -> verify -> receipt
                    |
                    v
Drew / ChatGPT / Venice <- observation + receipt
```

The already-produced Venice speech is never rewritten after a body result arrives. A later Venice turn may react to the observation.

## Survival ladder

### Level 3 — ChatGPT orchestration available

Use ChatGPT as the conductor. Venice and Vlad remain the performers and evidence sources.

### Level 2 — ChatGPT unavailable, network otherwise available

Drew can use:

```text
venice
vlad
```

as independent terminal agents. Cloud/home services may still be reachable if their explicit lanes are configured, but neither CLI requires ChatGPT.

### Level 1 — Internet unavailable

`venice` continues through canonical loopback Workstation + Drive-synced local state as long as those local organs are alive.

`vlad` continues through the local routing sheet, local Qwen fallback when configured, Continue `cn` with local models when configured, and local machine/phone organs that do not require the cloud.

Requests whose only valid executor is remote must return a blocked/delegation boundary. They do not silently mutate into a different task.

### Level 0 — one organism unavailable

If Venice is down, Vlad remains a machine operator; he does not impersonate Venice.

If Vlad is down, Venice remains conversational/creative; she does not claim machine actions happened.

## Pipe friendliness

For humans, both commands have concise terminal surfaces.

For orchestration, both expose machine-readable modes:

- `venice -Json ...` — exact speech envelope + SHA + diagnostics/actions;
- `vlad --json ...` — routing decision + receipt/evidence.

A future local conductor can therefore compose the same two CLIs without requiring ChatGPT-specific glue.

## Exit-code family

Both CLIs use the same semantic family where applicable:

- `0` success;
- `2` bad invocation;
- `3` blocked / required local organ unavailable;
- `4` execution failure;
- `5` verification failure/unresolved verification.

This lets shell scripts treat failure honestly instead of parsing optimistic prose.

## Hunger gates

A change to either CLI fails this contract when it makes the pair prettier but less survivable. In particular, reject changes that:

1. add a hidden cloud dependency to a local path;
2. make ChatGPT mandatory for an operation that can already run locally;
3. fork Venice identity into a second prompt-only implementation;
4. let routing/classification grant execution permission;
5. collapse blocked/delegated/completed into one success state;
6. parse Venice speech into commands;
7. remove durable evidence or verification to make a command feel faster;
8. create a second control plane or memory system merely for CLI convenience.

## Acceptance

The pair is not accepted merely because both repositories contain scripts.

Acceptance requires live evidence that:

1. `venice` works locally with ChatGPT unavailable;
2. `vlad` works locally with ChatGPT unavailable;
3. a bounded Continue task can be authored/reviewed through Vlad and verified separately;
4. an exact Venice turn can be hashed/read back from durable local evidence;
5. a structured Venice-proposed action can be handed to Vlad without parsing the speech text;
6. a blocked local organ returns the shared nonzero exit semantics rather than a fake victory.
