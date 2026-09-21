# PI Zodiac — Daily Irrational Sign Router

## Status

ACTIVE / SYMBOLIC DAILY CONTEXT

## Authority

Drew commission — 2026-09-21.

## Purpose

PI ("pie") is a daily sequence ritual. Each local calendar day advances exactly one digit through pi. The current digit acts like a zodiac sign: a compact symbolic lens that can route into existing Headcrab, Fortress, Ministry, body, review, memory, and delivery skills without replacing their real authority.

This is playful symbolic context, not mathematics-as-divination and not an evidence-bearing prediction system.

## Core law

**ONE DAY, ONE NEXT DIGIT. SAME DATE, SAME SIGN. MISSED DAYS STILL ADVANCE.**

The daily digit is determined by local date and the configured epoch. Completion/checkmarks do not advance the sequence; the calendar does. Missing a day never shifts the future mapping.

Canonical config:

`config/pi_zodiac.v1.json`

Canonical calculator:

`python3 tools/pi_zodiac.py [--date YYYY-MM-DD] [--pretty]`

## Epoch

V1 anchors the first visible run of the current paper PI tracker:

`2026-09-16 -> pi digit 3`

Provenance: inferred from the first marked date visible on the supplied tracker. This is a reversible configuration fact, not a claim about earlier historical PI practice. If Drew later corrects the epoch, change the config and preserve the correction.

The digit stream includes the integer digit first:

`3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, ...`

## Ten signs

The names are operational symbols. They do not change the underlying skills.

### 0 — VOID

Meaning: absence, subtraction, silence, the useful no-op.

System hook: Headcrab `HC-003 No reminder, no clever filler`.

Question: `What should be absent today?`

Failure temptation: invent activity merely to make the day feel productive.

### 1 — CRAB

Meaning: singular attention, the one thing that must not be missed.

System hook: `docs/doctrine/HEADCRAB_ATTENTION_OPERATOR.md`.

Question: `What must Drew not fail to notice?`

Failure temptation: let an interesting lower-priority thing outrank an actual obligation.

### 2 — FORK

Meaning: two paths, symmetry, contradiction, comparison before commitment.

System hook: framing-fidelity symmetry and alternative-path checks.

Question: `What changes if I take the other branch seriously?`

Failure temptation: treat the first framing as inevitable.

### 3 — TRAP

Meaning: catch avoidable stupidity before it reaches a human.

System hook: `skills/ministry-of-alarmingly-safe-traps/SKILL.md`.

Question: `What can I determine before asking a human?`

Failure temptation: make the human the transport or investigation layer.

### 4 — FRAME

Meaning: four corners, mission boundary, constraints that keep shape.

System hook: Fortress Core mission kernel and cumulative constraint ledger.

Question: `What outcome, owner, lane, exclusion, and evidence boundary must remain intact?`

Failure temptation: improve the implementation by silently changing the commission.

### 5 — HAND

Meaning: embodiment and execution. Stop admiring the plan and touch the world through the authorized body.

System hook: Phone Hands / Computer Hands / commissioned execution body.

Question: `What bounded real action converts intent into an observable state?`

Failure temptation: confuse plans, code, or receipts with delivery on the requested surface.

### 6 — SPIRAL

Meaning: iteration with memory. Return, but not to the same state.

System hook: operator-campaign continuation, bounded retry, backoff, regression learning.

Question: `What did the last loop teach that changes this loop?`

Failure temptation: blind retry or ceremonial polling.

### 7 — JUDGE

Meaning: adversarial inspection before confidence.

System hook: Regnet QA and applicable Judgment-Jar review.

Question: `What would reject this if it were trying to fool me?`

Failure temptation: let the author of the work be its only admirer.

### 8 — LOOP

Meaning: recurrence, durable memory, archaeology, the long curve back.

System hook: Home Center persistence, recovery, project archaeology, reusable skill extraction.

Question: `What keeps returning because it has not yet been made durable?`

Failure temptation: rediscover the same treasure in a new chat and call that progress.

### 9 — GATE

Meaning: consequence, delivery, closure, the threshold between "made" and "actually arrived."

System hook: commissioned delivery-surface supremacy and completion/acceptance gates.

Question: `What still separates this from real delivery or acceptance?`

Failure temptation: call implemented/tested/deployed/callable the same thing as delivered/accepted.

## Headcrab integration

Headcrab always keeps its existing priority law:

`due/overdue -> today -> open human commitments -> recent unfinished intent -> project archaeology -> wit`

PI Zodiac is symbolic context, not an obligation. It must NEVER displace or delay a supported actionable reminder.

When PI context is explicitly requested, or when a caller deliberately asks Headcrab for the daily sign, Headcrab may surface:

`π[index] = digit · SIGN`

followed by the sign's one-line question.

Future product/runtime integration may surface the sign once per local day after attention preflight. Repository doctrine alone does not prove that this happens automatically in fresh chats.

## Ministry boundary

The PI Zodiac is compatible with Ministry worldbuilding but does not rename or absorb an existing Ministry. The currently durable `MINISTRY_OF_ALARMINGLY_SAFE_TRAPS` remains its own office and owns the digit-3 TRAP hook.

The exact name of any separate PI Ministry remains unbound until recovered or explicitly named by Drew. Do not invent it.

## Punch-card compilation

`STATE + INPUT + RULE -> NEXT STATE + OBSERVABLE`

- STATE: epoch date, local date, pi digit stream, sign table, schema version.
- INPUT: requested date or current local date.
- RULE: calendar-day offset from epoch -> same zero-based offset into pi digits -> sign lookup.
- NEXT STATE: no mutable sequence state is required; tomorrow is determined by date.
- OBSERVABLE: same date/config always produces the same index, digit, sign, and prompt.
- MISSED DAY: no mutation; the date offset naturally advances.
- CORRECTION: epoch changes only through explicit config revision with provenance.

## Failure conditions

FAIL if:

- a checkmark/missed check changes the digit sequence;
- time-of-day changes the sign;
- wall-clock seconds or randomness choose the sign;
- a sign is presented as evidence, fate, probability, medical guidance, or objective prediction;
- PI commentary outranks Headcrab's real reminder;
- an existing Ministry is silently renamed or merged;
- a historical epoch is invented as certain;
- code/config existence is called runtime delivery.

## Compact law

**THE CALENDAR ADVANCES THE DIGIT. THE DIGIT ROUTES THE SYMBOL. THE SYMBOL NEVER OUTRANKS REALITY.**
