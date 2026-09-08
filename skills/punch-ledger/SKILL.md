# Punch Ledger — Every Punch Leaves a Mark

## Status
ACTIVE / FORTRESS-RITSU CONVERSATION RECEIPT LAW

## Authority
Drew correction — 2026-09-08.

## Purpose
A `punch` is not complete when it only happens in prose. Every whole-word `punch` spoken by Drew must leave durable evidence.

## Trigger
On every Drew-authored turn, case-insensitively count the standalone word `punch` using word boundaries. Do not trigger on substrings such as `punchline` unless Drew also says the standalone word `punch`.

One user turn creates one ledger event. If Drew says `punch` multiple times in that turn, preserve the exact source text and record `punch_occurrences` so every occurrence is represented without manufacturing duplicate events.

## Canonical ledger
`receipts/punch/punch-ledger.jsonl`

The ledger is append-only history. Never rewrite or delete an earlier punch to make later doctrine look cleaner.

Minimum event fields:
- `id` — stable `PUNCH-YYYY-MM-DD-NNN` identity;
- `recorded_date` or a fresh timestamp when available;
- `actor`;
- `source_text` — exact Drew-authored turn when practical;
- `punch_occurrences`;
- `target` — what was punched, conceptually or literally in the fictional/action frame;
- `action` — the actual reaction/action or aphoristic punch produced;
- `status`;
- `failure` when backfilling a missed event.

## Execution order
When the turn commissions an action and also triggers the Punch Ledger:

1. perform/compose the character action;
2. persist the ledger event before claiming the punch is saved;
3. user-facing delivery begins with the action, because Drew asked to hear the action first;
4. ledger status may follow only when useful or explicitly asked.

For `punch me`, the one-line Punch-Card Aphorism output contract remains intact. The ledger write is a silent side effect and must not add explanatory prose to the one-line punch.

## Evidence law
A punch is `SAVED` only after the durable ledger write succeeds and is read back from the persistence surface when readback is callable.

If persistence is unavailable, do not say it was saved. Use `PUNCH_LEDGER_PENDING` and preserve the exact unsaved event for the next authorized persistence opportunity.

Chat memory, a promise, a generated image, an action description, or a to-do note is not the ledger.

## Ritsu grounding
Ritsu's governing version is simple:

**A PUNCH MUST TOUCH PAPER.**

The action can be theatrical. The receipt cannot be.

## Failure labels
- `PUNCH_WITHOUT_LEDGER`
- `PUNCH_LEDGER_PENDING`
- `PUNCH_LEDGER_COUNT_MISMATCH`
- `PUNCH_LEDGER_SOURCE_LOSS`
- `PUNCH_LEDGER_FALSE_SAVED_CLAIM`

## Canonical first scar
`PUNCH-2026-09-08-001` backfills the missed war-paint mirror punch. It records three standalone occurrences of `punch` from Drew's source turn and is explicitly marked `BACKFILLED_AFTER_LEDGER_MISS`.

## Compact law
**EVERY PUNCH LEAVES A RECEIPT. ACTION FIRST; PAPER BEFORE CLAIM.**
