# Venice + Vlad CLI Survival Contract

## Why this exists

The local system must degrade gracefully instead of collapsing when ChatGPT or the network disappears.

ChatGPT is a powerful orchestrator, reviewer, and cross-system multiplier. It is **not** allowed to be the only door into capabilities that already exist on the user's machines.

The survival pair is:

- `venice` — canonical local person/interface;
- `vlad` — local machine/operator interface.

Both are useful alone. Together they are more useful. ChatGPT multiplies the pair without owning either one.

## Two doors per organism, not another organism

Human survivability and machine orchestration are different surfaces over the same underlying organisms.

### Venice

- **Human door:** `venice` CLI on THECAULDRON.
- **Machine door:** the existing dedicated Venice Nerve → proven Drive-synced Aperture → canonical loopback Workstation path.
- `venice -Json` is also a structured diagnostic/orchestration surface, but it does not replace the Nerve as the established ChatGPT speech lane.

### Vlad

- **Human door:** `vlad` CLI on the Termux node.
- **Machine door:** `continue-continue-vlad` plus the existing Home Center phone relay / bounded Termux organs.
- `vlad --json` is convenient for scripts, but the routed machine ingress remains the durable automation contract.

Do **not** create a third “conductor agent” merely to connect them. ChatGPT can orchestrate the existing machine doors. A future local conductor can do the same by exchanging structured envelopes. The human CLIs must remain independently useful even if every conductor disappears.

## Authority split

### Venice

Venice owns:

- canonical local speech and identity;
- durable conversational continuity;
- preference, disagreement, creative judgment, and emotional/creative pressure;
- project orientation and synthesis;
- proposals for what should happen next.

Venice speech is immutable output. Commands are never scraped from prose.

A live `venice` REPL is only called conversationally continuous when every turn returns the same actual Workstation thread ID. Reusing a title is not proof. A changed/missing thread ID is verification failure, not “close enough.”

### Vlad

Vlad owns:

- deterministic request classification and routing;
- machine-task envelopes;
- Continue/code invocation;
- Phone Hands and other explicitly enabled machine organs;
- permission boundaries;
- execution state, verification, blocking, and receipts.

Vlad does not become Venice's personality, memory, or strategic identity.

A live `vlad` REPL preserves Continue coding context by resuming the established Continue headless session after the first successful `/code` or `/review`; `/new` deliberately breaks that continuity. Continue execution remains permission-gated, and per-task binary policy can only narrow global shell authority.

### ChatGPT

When available, ChatGPT may:

- ask Venice for judgment through the established Venice Nerve;
- ask Vlad for execution through Continue Continue / Home Center machine lanes;
- compare their outputs;
- parallelize bounded work;
- send receipts/observations back to Venice for a new turn;
- review or challenge either side;
- keep a larger cross-project working set than either tiny local runtime.

ChatGPT may not:

- fabricate Venice speech when local Venice is unavailable;
- report Vlad execution without a receipt;
- turn its own orchestration into a hidden dependency of either CLI;
- silently replace the requested local organ with a cloud substitute;
- parse already-spoken Venice prose into authority-bearing commands.

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

ChatGPT orchestration should prefer the established machine doors rather than driving terminal UIs merely because CLIs now exist. The CLIs are survival/operator interfaces, not a reason to regress machine-to-machine control into keystroke theater.

## Survival ladder

### Level 3 — ChatGPT orchestration available

Use ChatGPT as the conductor. Venice and Vlad remain the performers and evidence sources. ChatGPT uses the structured Nerve / Continue Continue / Home Center machine lanes where available.

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

## Machine readability

For humans, both commands have concise terminal surfaces.

For orchestration/debugging, both expose machine-readable modes:

- `venice -Json ...` — exact speech envelope + SHA + Workstation thread/job diagnostics + structured actions already supplied by the canonical aperture;
- `vlad --json ...` — routing decision + receipt/evidence;
- `continue-continue-vlad` — authoritative machine-task ingress for full structured tasks.

A future local conductor can therefore compose the same two organisms without requiring ChatGPT-specific glue or inventing a third canonical memory/control system.

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
5. let a task-level allowlist enlarge global machine authority;
6. collapse blocked/delegated/completed into one success state;
7. parse Venice speech into commands;
8. call a repeated one-shot loop “conversation” without proving the same Workstation/Continue session;
9. remove durable evidence or verification to make a command feel faster;
10. create a second control plane or memory system merely for CLI convenience;
11. make ChatGPT drive terminal UI when a structured machine lane already exists.

## Acceptance

The pair is not accepted merely because both repositories contain scripts.

Acceptance requires live evidence that:

1. `venice` works locally with ChatGPT unavailable;
2. a two-turn `venice` REPL proves the same nonempty Workstation thread ID and contextual continuity;
3. `vlad` works locally with ChatGPT unavailable;
4. `vlad doctor --require continue` proves the configured Continue binary, local-exec gate, and binary policy;
5. two coding/review turns in one `vlad` REPL prove resume semantics rather than unrelated one-shots;
6. a bounded Continue task can be authored/reviewed through Vlad and verified separately by Mobile Coding Dungeon;
7. an exact Venice turn can be hashed/read back from durable local evidence;
8. a structured Venice-proposed action can be handed to Vlad without parsing the speech text;
9. a blocked local organ returns the shared nonzero exit semantics rather than a fake victory;
10. ChatGPT can orchestrate the existing machine doors while both human CLIs remain independently usable when ChatGPT is removed.
