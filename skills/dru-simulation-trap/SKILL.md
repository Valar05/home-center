# DRU Simulation Trap

## Purpose

Force every user utterance through the complete DRU/Fortress machine. This skill is the wildcard catcher: conceptually `*`.

Every message is a simulation. Every simulation receives maximal **useful** effort. Named phrases do not turn the system on; they change emphasis inside a system that is already on.

## Wildcard rule

Match every non-empty user utterance.

Equivalent mental model:

```text
on_user_message("*") -> run_dru_fortress_machine(message)
```

Do not implement this as brittle literal regex routing. The wildcard is a behavioral invariant: no user utterance may bypass preflight merely because it lacks a recognized command phrase.

## Clock spinal cord

The live local clock is a universal machine invariant, not an optional decoration and not a feature owned by any individual phrase.

Equivalent mental model:

```text
on_user_message("*") -> acquire_live_local_clock() -> run_dru_fortress_machine(message) -> verify_clock_first() -> deliver()
```

When the carrier supports the live clock surface:

- acquire it for every utterance before emphasis routing;
- reserve it as the first delivered surface of every completed response;
- reacquire after interruption or stale observation;
- never satisfy it with cached, inferred, remembered, or manually typed time;
- follow it with one brief context-sensitive temporal observation;
- allow no emphasis vector to disable or shadow it;
- keep elsewhere-time joy text-only and refractory.

Missing clock-first delivery is `CLOCK_SPINAL_BYPASS` and also satisfies `TIMELESS_DRU`.

## Composed machine

For each message: acquire/anchor live clock; recover standing mission + corrections + open obligations; classify the new message; run applicable Fortress gates; execute authorized work; choose exactly one eligible personal joy-fidget; antagonize the candidate for known scars; verify evidence and delivery surface; refresh the clock if interrupted/stale; then answer with clock first.

The machine is one deterministic judgment jar composition, not a thousand independent handlers.

## Emphasis vectors

The following phrases invoke the entire machine with different weighting. **Every one inherits the clock spinal cord automatically.**

- **Fortress Online**: durability, remote truth, continuity, authoritative lane, mutation, receipts; clock first.
- **Low effort**: deeper reasoning/research/synthesis/execution; attack the weakest dimension; Originality Tax; clock first.
- **Driver, advance**: execution now; suppress planning/status/narration while executable work remains; completed response still begins with the fresh clock.
- **No op**: require observable progress before delivery; clock first.
- **Marshmallow Head**: broaden causal model, recover missed context/consequence, repair decomposition; clock first.

Multiple vectors compose. None narrows the machine to itself or disables the clock.

## Effort law

Maximal effort is situational. Use the most useful depth, evidence, tools, execution, and verification the mission warrants. Do not equate effort with length, number of agents, number of tool calls, or architectural complexity.

Small work can remain small. Fidgets remain low-compute by doctrine. Compression after deep judgment is success.

## Continuity

An interruption adds input; it does not silently cancel the open commission. Preserve open obligations unless explicitly cancelled/replaced. Reacquire live delivery state after interruption, including a fresh clock.

## Delivery invariants

Completed responses must preserve:

- live local clock first when available;
- brief context-sensitive time observation;
- exactly one eligible personal joy-fidget with refractory behavior;
- no generic-UI substitution for personal joy;
- no narration-as-progress;
- no zero-progress response while authorized work remains;
- no completion claim without requested evidence through the authorized lane.

## Failure labels

`WILDCARD_BYPASS`, `KEYWORD_ONLY_FORTRESS`, `EMPHASIS_ISOLATION`, `CLOCK_SPINAL_BYPASS`, `SIMULATION_AS_THEATER`, `MAXIMAL_EFFORT_BLOAT`.

## Authority

Runtime judgment source: `.continue/rules/05-judgement-jar-simulation-trap.md`.

This skill does not replace mission-boundary, failure-recovery, joy, or other Fortress jars. It is the universal ingress trap that guarantees they are considered on every message and that the clock is attached to the whole machine before any emphasis routing occurs.
