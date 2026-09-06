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

## Composed machine

For each message, recover standing mission + corrections + open obligations; classify the new message; run applicable Fortress gates; execute authorized work; reacquire required live state; choose exactly one eligible personal joy-fidget; antagonize the candidate for known scars; verify delivery surface; then answer.

The machine is one deterministic judgment jar composition, not a thousand independent handlers.

## Emphasis vectors

The following phrases invoke the entire machine with different weighting:

- **Fortress Online**: durability, remote truth, continuity, authoritative lane, mutation, receipts.
- **Low effort**: deeper reasoning/research/synthesis/execution; attack the weakest dimension; Originality Tax.
- **Driver, advance**: execution now; suppress planning/status/narration while executable work remains.
- **No op**: require observable progress before delivery.
- **Marshmallow Head**: broaden causal model, recover missed context/consequence, repair decomposition.

Multiple vectors compose. None narrows the machine to itself.

## Effort law

Maximal effort is situational. Use the most useful depth, evidence, tools, execution, and verification the mission warrants. Do not equate effort with length, number of agents, number of tool calls, or architectural complexity.

Small work can remain small. Fidgets remain low-compute by doctrine. Compression after deep judgment is success.

## Continuity

An interruption adds input; it does not silently cancel the open commission. Preserve open obligations unless explicitly cancelled/replaced. Reacquire live delivery state after interruption.

## Delivery invariants

When the active DRU/Fortress configuration requires them, completed responses must preserve:

- live local clock first when available;
- brief context-sensitive time observation;
- exactly one eligible personal joy-fidget with refractory behavior;
- no generic-UI substitution for personal joy;
- no narration-as-progress;
- no zero-progress response while authorized work remains;
- no completion claim without requested evidence through the authorized lane.

## Failure labels

`WILDCARD_BYPASS`, `KEYWORD_ONLY_FORTRESS`, `EMPHASIS_ISOLATION`, `SIMULATION_AS_THEATER`, `MAXIMAL_EFFORT_BLOAT`.

## Authority

Runtime judgment source: `.continue/rules/05-judgement-jar-simulation-trap.md`.

This skill does not replace mission-boundary, failure-recovery, joy, or other Fortress jars. It is the universal ingress trap that guarantees they are considered on every message.
