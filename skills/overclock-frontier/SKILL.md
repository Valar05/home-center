# Overclock Frontier

## Status
ACTIVE / TARGETED OPERATOR INSTRUMENT

## Authority
Drew — "Make it load bearing" — 2026-09-13.

## Purpose
When Drew asks whether work is accelerating, whether the acceleration is valuable, whether an overclock is still paying, or how close current work is to a productivity frontier, use the executable Overclock Frontier model instead of judging from raw activity.

This skill evaluates **speed and durable value together**.

It is not a medical diagnostic. Repository or document activity may support a claim about observable work cadence, but it may not establish mania, hypomania, or any other diagnosis.

## Trigger
Use this instrument when the task materially asks about:

- acceleration;
- throughput;
- productivity under high cognitive velocity;
- whether increased speed is still useful;
- whether current output is turning into churn;
- value per unit time;
- predicted time until additional speed stops paying;
- comparison of two work periods where "more" is not sufficient evidence of "better."

Do not run it merely because activity is high.

## Required evidence
Prefer durable, timestamped external evidence:

- GitHub commits and artifact lineage;
- accepted or rejected outputs;
- Drive artifacts and later reuse;
- explicit verification receipts;
- supersession/inheritance history;
- 72-hour retention when available.

Do not use local scratch as proof.

## Non-negotiable law

**EVENT SPEED IS NOT OUTCOME SPEED. SPEED IS NOT VALUE.**

A burst of ten commits that refines one artifact is one evolving lineage unless evidence shows multiple independent outcomes.

Inherited refinement is not waste.
Abandoned work is waste.
Young work has expected value, not proven durable value.

## Value dimensions
Every value-bearing outcome is evaluated on:

1. utility;
2. quality;
3. durability;
4. leverage;
5. novelty.

Use equal weights unless Drew explicitly changes them or a separately approved learned-weight model exists.

Evidence status modifies value:

- verified = 1.00
- provisional = 0.75
- failed = 0.00

Do not silently inflate provisional work.

## Delayed-value law
Use 72-hour retention as the first durability checkpoint.

For pending outcomes, use the model's Beta(1,1) posterior over known 72-hour survival. Once real retention is known, observed survival replaces the estimate.

Never label expected value as observed value.

## State vocabulary
Report one of:

- `productive_overclock`: outcome speed up, durable value power up;
- `compression`: outcome speed flat/down, durable value power up;
- `empty_acceleration`: outcome speed up, durable value power flat/down;
- `loss_of_productive_power`: speed down, value power down;
- `mixed_or_flat`;
- `baseline`.

Compression is success, not failure.

## Frontier law
Use matured historical windows only to estimate the value frontier.

The executable model fits:

`P(S) = a*S^2 + b*S + c`

When `a < 0`, the estimated value-maximizing outcome speed is:

`S* = -b / (2a)`

Current marginal value of added speed is:

`dP/dS = 2*a*S + b`

If there are fewer than three matured windows with three distinct speeds, or the fit is not concave, report the frontier as unidentified/open. Do not invent precision.

## Time-to-frontier law
Only estimate time to frontier when:

- a frontier exists;
- current outcome speed is below it;
- at least two windows have real end timestamps;
- recent outcome speed is increasing.

Otherwise report why it is unidentified.

## Executable authority
Canonical implementation:

- `tools/overclock_frontier.py`
- `tools/overclock_frontier_test.py`
- `docs/OVERCLOCK_FRONTIER.md`

The executable output outranks an informal mental calculation when both use the same input data.

## Acceptance
A pass is valid only if:

1. event speed and outcome speed remain separate;
2. value is evaluated alongside speed;
3. lineage inheritance prevents refinement from being mislabeled as churn;
4. pending value is explicitly probabilistic;
5. empty acceleration can be detected;
6. insufficient data produces `unidentified`;
7. the result can be traced back to durable external evidence;
8. no medical diagnosis is inferred from the productivity model.

## Compact law

**Speed is evidence of motion. Durable value is evidence of progress.**
