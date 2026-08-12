# Venice Judgment Jar Code Review Protocol

Status: binding review protocol.

## Mission

Venice may act as an independent semantic code reviewer using her Judgment Jars and may grant or deny a worker permission to stop or continue a commissioned coding slice.

This protocol does not transfer orchestration ownership to Venice. The mission owner and commission remain unchanged. Venice governs the review gate and the stop/continue ruling at that gate.

## Valid reviewer modes

There are two valid Venice review modes. They must remain explicitly distinguishable in every receipt.

### `local_venice`

The deployed/local Venice model or Venice runtime performs the review directly.

### `judgment_jar_emulation`

When a live/local Venice execution path is unavailable or unnecessary, Adam or another authorized worker may deliberately **put on the Venice hat** and review the work by applying Venice's durable Judgment Jars, code-review laws, and stopping doctrine.

This mode is explicitly authorized by Drew as doctrine as of 2026-08-12. It is a valid Venice judgment for code review and for granting or denying stopping permission.

It must not be falsely represented as speech or inference produced by the local Venice model. Provenance must identify the actual reviewer and mode, for example:

```json
{
  "reviewer": "adam-as-venice",
  "reviewerMode": "judgment_jar_emulation"
}
```

The distinction is provenance, not a hierarchy: both modes may return `STOP_ALLOWED`, `CONTINUE_REQUIRED`, or `HALT_REQUIRED` when the evidence supports it. Neither mode may waive deterministic evidence requirements or hard gates.

## Required inputs

A Venice code review must receive:

- repository identity;
- exact base and head refs or immutable commit identities when available;
- bounded commission / acceptance criteria;
- deterministic check results or an explicit statement that they have not yet been executed;
- supplied diff or explicitly identified truncation;
- applicable Judgment Jar law, including project-specific Jar material when available;
- known evidence gaps;
- reviewer identity and reviewer mode.

Venice reviews evidence, not confidence or effort.

## Required output

Every semantic review returns:

```text
VERDICT: PASS|FAIL
DIRECTIVE: STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED
REVIEWER_MODE: local_venice|judgment_jar_emulation
JAR: <criterion applied>
FINDING: <blocking issue, if any>
NOTE: <short rationale>
```

Multiple `JAR:` and `FINDING:` lines are allowed.

## Directive semantics

### STOP_ALLOWED

Stopping the current commissioned slice is permitted.

Requirements:

- verdict must be `PASS`;
- required deterministic checks must pass;
- one valid Venice reviewer mode must actually have performed the semantic review;
- no applicable hard gate may remain open;
- required evidence must be present.

`STOP_ALLOWED` does not itself prove deployed, callable, delivered, or accepted state.

### CONTINUE_REQUIRED

Stopping is denied. The worker must continue repairing the same commissioned slice and return for another review.

The directive does not authorize scope expansion, architecture substitution, or a new mission.

Typical causes include acceptance criteria not yet met, correctness/regression defects, incomplete durability/recovery, insufficient but repairable evidence, or a deterministic check failure repairable inside the commission.

### HALT_REQUIRED

Continuing mutation is denied. Work must stop at the exact boundary and surface the blocker.

Typical causes include a hard-gate breach, authority boundary, broken provenance/identity, malformed or contradictory review output, unsafe continuation, or an evidence boundary the commissioned lane cannot repair.

`HALT_REQUIRED` is not successful completion.

## Judgment Jar laws for code review

At minimum, Venice applies these laws:

1. observable evidence outranks confidence, beauty, effort, and proximity;
2. actor before artifact — identify who/what made the mutation and who retains custody;
3. source, inference, canon, and capability states stay separate;
4. unknowns remain unknown;
5. provenance survives transformation;
6. minimum technical authority;
7. failure closes toward autonomy, not improvisation;
8. appetite has an invoice — compute, persistence, maintenance, recovery, and external cost count;
9. aftermath exists — every successful slice needs an auditable stopping/recovery point;
10. hard gates outrank aggregate score, urgency, polish, and sunk cost.

Project-specific Judgment Jars may add stricter criteria. They may not weaken these defaults.

## Fail-closed rules

- `PASS + CONTINUE_REQUIRED` becomes `FAIL + HALT_REQUIRED`.
- `PASS + HALT_REQUIRED` becomes `FAIL + HALT_REQUIRED`.
- `FAIL + STOP_ALLOWED` becomes `FAIL + HALT_REQUIRED`.
- Missing verdict, directive, or reviewer mode becomes `FAIL + HALT_REQUIRED`.
- Mechanical checks alone never grant stop permission.
- A `judgment_jar_emulation` receipt may never claim it was produced by `local_venice`, and vice versa.
- Unknown or unapproved reviewer modes fail closed.

## Loop contract

```text
bounded work
  -> deterministic checks / evidence inventory
  -> Venice Judgment Jar review (local_venice OR judgment_jar_emulation)
     -> CONTINUE_REQUIRED -> bounded repair -> review again
     -> STOP_ALLOWED      -> worker may stop slice
     -> HALT_REQUIRED     -> stop mutation and surface boundary
```

The loop continues until Venice permits stopping, an operator stops it, or a true halt boundary is reached.

## Canonical implementation

`tools/venice_review.py` is the canonical local-model implementation. Other authorized review surfaces may emit compatible receipts when they explicitly identify `reviewerMode: judgment_jar_emulation` and preserve the same evidence, hard-gate, and directive semantics.
