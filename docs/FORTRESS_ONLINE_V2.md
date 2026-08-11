# Fortress Online V2

Status: EXPERIMENTAL / ISOLATED
Authority: Drew Clarke
Branch: `fortress-online-v2`
Non-interference lock: V2 must not mutate or replace active Fortress Online V1 until explicitly accepted.

## Purpose

Fortress Online V2 converts Tetsuya/Adam doctrine from advisory prose into deterministic runtime gates. The model may still reason and improvise inside the mission boundary, but it cannot truthfully advance or hand off unless the mission kernel can prove the transition.

## Failure classes V2 is designed to prevent

1. **Context loss** — required lookups are declared and execution is blocked until they are completed.
2. **Assumption instead of retrieval** — unknown source truth produces a retrieval obligation instead of confident synthesis.
3. **Silent substitution** — changes to owner, lane, delivery surface, evidence standard, or other mission boundaries remain proposals until explicitly approved.
4. **Correction amnesia / regression soup** — every revision can be diffed against the cumulative constraint ledger; dropping earlier non-conflicting exclusions, constraints, or corrections fails the gate.
5. **Premature stopping** — arbitrary stop reasons are invalid. Only explicit authority, identity, privacy, purchase, destructive-action, outside-communication, safety, or genuine external blockers may halt an unfinished mission.
6. **Capability laundering** — requested, implemented, tested, deployed, callable, delivered, and accepted are separate states with separate evidence.
7. **Status theater** — implementation alone cannot be reported as delivery. Delivery requires verified evidence on the commissioned persistent surface.
8. **Motivated-mode drift** — adjacent work must remain safe, authorized, tied to the commissioned outcome, and selected only after the next missing evidence gate is satisfied.

## Mission contract

Every nontrivial Fortress V2 task should normalize into this shape:

```json
{
  "outcome": "what Drew actually commissioned",
  "owner": "Drew Clarke",
  "lane": "authorized execution lane",
  "deliverySurface": "persistent commissioned destination",
  "evidenceStandard": "what proves completion",
  "exclusions": [],
  "constraints": [],
  "corrections": [],
  "requiredLookups": [],
  "completedLookups": [],
  "proposedChanges": [],
  "approvedChanges": [],
  "artifacts": [],
  "state": "requested",
  "stopReason": "",
  "nextActions": []
}
```

## State machine

`requested -> implemented -> tested -> deployed -> callable -> delivered -> accepted`

No state implies a later state. Each transition requires its own evidence.

Examples:

- a GitHub commit may prove **implemented**;
- a passing CI run may prove **tested**;
- a deployment receipt may prove **deployed**;
- an end-to-end canary may prove **callable**;
- readback from the commissioned destination may prove **delivered**;
- only Drew or an explicitly authorized acceptance mechanism can prove **accepted**.

## Retrieval gate

A task that depends on project truth, prior corrections, current external state, or a named artifact must enumerate those lookups before action. `requiredLookups - completedLookups` must be empty before preflight passes.

The intended behavior is not “search everything.” It is “search every material uncertainty before betting the mission on it.”

## Boundary gate

The following are mission-boundary fields and may not be silently changed:

- outcome;
- owner;
- lane/tool;
- exclusions;
- evidence standard;
- delivery surface.

Improvements to implementation are welcome. Changes to those fields are proposals until Drew approves them.

## Correction gate

A correction creates a cumulative ledger, not a replacement prompt. Before a revised mission is executed, `correctionDiff(before, after)` must show that every earlier non-conflicting exclusion, constraint, and correction survived.

## Stop gate

An unfinished mission may stop only for a genuine boundary:

- authority;
- identity;
- privacy;
- purchase;
- destructive action;
- outside communication;
- safety;
- genuine external blocker.

“Felt done,” “ran one test,” “documented the blocker,” “too many steps,” and “probably works” are deliberately not stop reasons.

## Test strategy

The dedicated workflow `.github/workflows/fortress-v2-contract.yml` runs only against V2 paths and the V2 branch/PR. It does not deploy V1 or alter the active Fortress runtime.

The initial regression suite covers:

- missing retrieval;
- silent lane substitution;
- correction regression;
- capability laundering;
- arbitrary early stop;
- valid hard stop;
- motivated continuation;
- truthful delivered handoff.

## Acceptance gate for replacing V1

V2 must remain experimental until all of the following are true:

1. deterministic contract suite is green in GitHub Actions;
2. at least five historical Fortress failure incidents are encoded as regression fixtures and pass;
3. at least three live, non-destructive missions are run through V2 in shadow mode while V1 remains authoritative;
4. V2 demonstrates better retrieval, constraint preservation, and truthful completion reporting without materially increasing friction or quota burn;
5. Drew explicitly accepts promotion.

Until then, V1 remains the active operating system and V2 is a quarantined successor candidate.
