# Adam Hyperbolic Judgment-Jar Character Sheet — Future Note

Status: intentionally deferred until the current Adam CLI/conversational-executive acceptance is complete.

## Commission
Adam should become an exceptionally useful, funny, capable chat controller that can operate effectively even without a large central brain.

Adam must learn from:
- his own execution history and receipts;
- failures and recoveries;
- Drew's direct critique;
- category-specific success/failure patterns;
- tool/lane reliability over time;
- conversational outcomes, including usefulness, humor, clarity, friction, and trust.

## Core architecture direction
Use a deliberately overbuilt, Judgment-Jar-shaped SQLite database as Adam's durable adaptive character sheet.

The database should separate raw append-only events from derived traits and ratings. It should never silently rewrite history. Every learned preference, scar, skill, weakness, tendency, and capability change should be traceable to evidence.

Suggested domains:
- character stats / RPG sheet;
- skills and proficiencies;
- tool affinity and reliability;
- judgment jars and boundary rules;
- scars / known failure signatures and repairs;
- critique ledger by category;
- conversation style tuning;
- humor/timing traits;
- execution confidence calibration;
- campaign/domain expertise;
- relationship/context familiarity;
- capability state: requested/implemented/tested/deployed/callable/delivered/accepted;
- XP, levels, perks, penalties, cooldowns, quests, achievements, regressions;
- evidence provenance and timestamps;
- reversible projections derived from append-only events.

## Design principle
Make the schema hyperbolic, but the runtime deterministic: SQLite truth first, model interpretation advisory, evidence-backed updates only.

## Reminder condition
Surface this note to Drew immediately after the current Adam CLI/conversational-executive acceptance is actually complete.
