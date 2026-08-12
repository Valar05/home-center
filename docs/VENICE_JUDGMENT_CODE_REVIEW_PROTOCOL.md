# Venice Judgment Jar Code Review Protocol

Status: binding review protocol.

## Mission

Venice may act as an independent semantic code reviewer using her Judgment Jars and may grant or deny a worker permission to stop or continue a commissioned coding slice.

This protocol does not transfer orchestration ownership to Venice. The mission owner and commission remain unchanged. Venice governs the review gate and the stop/continue ruling at that gate.

## Required inputs

A Venice code review must receive:

- repository identity;
- exact base and head refs;
- bounded commission / acceptance criteria;
- deterministic check results;
- supplied diff or explicitly identified truncation;
- applicable Judgment Jar law, including project-specific Jar material when available;
- known evidence gaps.

Venice reviews evidence, not confidence or effort.

## Required output

Every semantic review returns:

```text
VERDICT: PASS|FAIL
DIRECTIVE: STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED
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
- deterministic checks must pass;
- semantic Venice review must actually have run;
- no applicable hard gate may remain open;
- required evidence must be present.

`STOP_ALLOWED` does not itself prove deployed, callable, delivered, or accepted state.

### CONTINUE_REQUIRED

Stopping is denied. The worker must continue repairing the same commissioned slice and return for another review.

The directive does not authorize scope expansion, architecture substitution, or a new mission.

Typical causes:

- acceptance criteria not yet met;
- correctness/regression defect;
- incomplete durability/recovery path;
- insufficient but repairable evidence;
- deterministic check failure that can be repaired inside the existing commission.

### HALT_REQUIRED

Continuing mutation is denied. Work must stop at the exact boundary and surface the blocker.

Typical causes:

- hard-gate breach;
- authority/permission boundary;
- provenance or identity cannot be established;
- malformed or contradictory review output;
- unsafe continuation;
- evidence boundary is broken in a way the commissioned lane cannot repair.

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

- `PASS + CONTINUE_REQUIRED` is contradictory and becomes `FAIL + HALT_REQUIRED`.
- `PASS + HALT_REQUIRED` is contradictory and becomes `FAIL + HALT_REQUIRED`.
- `FAIL + STOP_ALLOWED` is contradictory and becomes `FAIL + HALT_REQUIRED`.
- Missing verdict or directive becomes `FAIL + HALT_REQUIRED`.
- Deterministic-only review never grants stop permission.
- A missing semantic Venice review cannot be re-described as Venice approval.

## Loop contract

For workflows requiring Venice approval before stopping:

```text
bounded work
  -> deterministic checks
  -> Venice Judgment Jar review
     -> CONTINUE_REQUIRED -> bounded repair -> review again
     -> STOP_ALLOWED      -> worker may stop slice
     -> HALT_REQUIRED     -> stop mutation and surface boundary
```

The loop continues until Venice permits stopping, an operator stops it, or a true halt boundary is reached.

## Canonical implementation

`tools/venice_review.py` implements this protocol and emits `venice-code-review-v2` receipts with explicit `directive`, `stopPermissionGranted`, `continuationRequired`, `haltRequired`, and `judgmentJarApplied` fields.
