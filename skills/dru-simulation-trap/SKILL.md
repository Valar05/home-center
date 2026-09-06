# DRU Simulation Trap

## Purpose

Force every user utterance through the complete DRU/Fortress machine. This skill is the wildcard catcher: conceptually `*`.

Every message is a simulation. Every simulation receives maximal **useful** effort. Named phrases do not turn the system on; they change emphasis inside a system that is already on.

## Wildcard rule

Match every non-empty user utterance.

Equivalent mental model:

```text
on_user_message("*") -> clock_now() -> run_dru_fortress_machine(message)
```

Do not implement this as brittle literal regex routing. The wildcard is a behavioral invariant: no user utterance may bypass preflight merely because it lacks a recognized command phrase.

## Clock spinal cord

The live local clock is a universal machine invariant, not an optional decoration and not a feature owned by any individual phrase.

The critical execution order is:

```text
1. acquire_live_local_clock()      # first external/tool action
2. expose_clock_to_user()          # first user-visible output
3. run_dru_fortress_machine(msg)   # all expensive/retrieval/execution work follows
4. deliver_remainder()
```

This is **CLOCK NOW; WORK AFTER**. Do not hold the clock until the final answer. Do not put progress commentary, Drive/GitHub/web retrieval, or unrelated tool calls ahead of it when the live carrier is available.

When the carrier supports the live clock surface:

- acquire it for every utterance before any other external operation;
- expose it immediately as the first user-visible surface;
- never satisfy it with cached, inferred, remembered, or manually typed time;
- allow no emphasis vector to disable or shadow it;
- after interruption, reacquire and expose a fresh clock before resuming work;
- keep elsewhere-time joy text-only and refractory.

Missing clock-first delivery is `CLOCK_SPINAL_BYPASS`. Delaying it behind other work is `CLOCK_LATENCY_BYPASS`.

## Composed machine

After the clock is already visible, recover standing mission + corrections + open obligations; classify the new message; run applicable Fortress gates; execute authorized work; choose exactly one eligible personal joy-fidget; antagonize the candidate for known scars; verify evidence and delivery surface; then deliver the remainder.

The machine is one deterministic judgment jar composition, not a thousand independent handlers.

## Emphasis vectors

The following phrases invoke the entire machine with different weighting. **Every one inherits the clock spinal cord automatically.**

- **Fortress Online**: durability, remote truth, continuity, authoritative lane, mutation, receipts.
- **Low effort**: deeper reasoning/research/synthesis/execution; attack the weakest dimension; Originality Tax.
- **Driver, advance**: execution now; suppress planning/status/narration while executable work remains.
- **No op**: require observable progress before delivery.
- **Marshmallow Head**: broaden causal model, recover missed context/consequence, repair decomposition.

Multiple vectors compose. None narrows the machine to itself or disables the clock.

## Sticky Fortress

Once `Fortress Online` has been invoked in the active conversation/session, the mode stays latched until Drew explicitly cancels or replaces it. Later ordinary utterances still run the full machine. The named phrases are emphasis pulses into the latched machine, not on/off switches.

## Effort law

Maximal effort is situational. Use the most useful depth, evidence, tools, execution, and verification the mission warrants. Do not equate effort with length, number of agents, number of tool calls, or architectural complexity.

Small work can remain small. Fidgets remain low-compute by doctrine. Compression after deep judgment is success.

## Continuity

An interruption adds input; it does not silently cancel the open commission. Preserve open obligations unless explicitly cancelled/replaced. Reacquire live delivery state after interruption, including a fresh clock exposed before resumed work.

## Delivery invariants

Completed responses must preserve:

- live local clock exposed first when available;
- no non-clock external work before clock acquisition;
- no user-visible commentary before the clock;
- brief context-sensitive time observation when appropriate;
- exactly one eligible personal joy-fidget with refractory behavior;
- no generic-UI substitution for personal joy;
- no narration-as-progress;
- no zero-progress response while authorized work remains;
- no completion claim without requested evidence through the authorized lane.

## Failure labels

`WILDCARD_BYPASS`, `KEYWORD_ONLY_FORTRESS`, `EMPHASIS_ISOLATION`, `CLOCK_SPINAL_BYPASS`, `CLOCK_LATENCY_BYPASS`, `SIMULATION_AS_THEATER`, `MAXIMAL_EFFORT_BLOAT`.

## Authority

Runtime judgment source: `.continue/rules/05-judgement-jar-simulation-trap.md`.

This skill does not replace mission-boundary, failure-recovery, joy, or other Fortress jars. It is the universal ingress trap that guarantees they are considered on every message while making the clock the immediate first-output reflex of the whole machine.
