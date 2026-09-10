# Ministry of Alarmingly Safe Traps

Status: active
Owner: DRU / Fortress correction layer
Canonical ministry: `MINISTRY_OF_ALARMINGLY_SAFE_TRAPS`

## Purpose

Turn repeatable AI failure modes into small, deterministic pre-delivery traps that are safe precisely because they catch the worker before the worker consumes human attention, authority, or patience.

A trap is not a persona and not an excuse for ceremony. It is a compact stop condition with a repair.

## Bear Trap — unnecessary human question

Canonical class: `BEAR_TRAP_UNNECESSARY_HUMAN_QUESTION`

Canonical fixture: Brian.

Canonical law:

> We will never ask Brian a single question while there is a single path left for automated exploitation.

Generalized invariant: never ask a human collaborator a question while a material answer path remains available through tools, code, repository history, configuration, API responses, logs, tests, tickets, diffs, documentation, or reproducible execution.

Before asking a human collaborator anything, exhaust the relevant automated paths:

1. Read the code and current state.
2. Search repository history and prior evidence.
3. Inspect config, API responses, logs, and tool output.
4. Run or reproduce the behavior when an authorized runtime exists.
5. Read related tickets, reviews, diffs, and prior decisions.
6. Search documentation and tests.

Only after the remaining uncertainty cannot be resolved automatically may the worker formulate the smallest question that closes the exact gap. The question is the deliverable of investigation, not the beginning of investigation.

## Mansplaining failure companion

If the first proposed human question rests on a false or lazy premise and the human corrects it, stop processing the stale downstream explanation. Do not defend, finish, or narrate the invalid branch. Record the correction, repair the rule, and resume from the corrected premise.

Fixture shape:

`first unnecessary question -> correction -> stale explanation discarded -> durable rule encoded`

## Classification boundary

The Brian failure is a **bear trap**.

It is not a thirst trap.
It is not a jigsaw trap.
Do not collapse those names into aliases or invent their semantics from this skill.

## PASS / FAIL

PASS when the worker either answers from available evidence or can show that every materially relevant automated path has been exhausted before asking one minimal human question.

FAIL when the worker asks a collaborator to provide information the worker could have obtained itself, asks a broad questionnaire before investigating, or continues explaining a branch after the human has invalidated its premise.

Repair:

`consume uncertainty -> exhaust automation -> ask only irreducible human question`

## Runtime memory hydration

When Home Center local knowledge is writable, promote this invariant into all three local durable surfaces:

- `SKILLS.md`: the repeatable pre-question procedure.
- `AGENTS.md`: the steering law forbidding premature human questions.
- `MEMORY.md`: the Brian fixture and the durable lesson that human attention is the scarce resource.

The canonical source remains this skill; local copies may summarize but must not weaken the law.
