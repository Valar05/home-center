# Overclock Frontier

Status: executable v1
Owner: Drew
Purpose: measure speed **and** durable value, then estimate when additional speed stops paying.

This is a productivity and decision instrument. It is not a medical diagnostic and it does not infer mania from repository activity.

## Why this exists

Raw activity is not the target. Commits, messages, documents, and edits are events. They can represent productive refinement, duplicated work, or churn.

The model therefore separates:

- **event speed**: raw durable actions per hour;
- **outcome speed**: distinct value-bearing lineages per hour;
- **durable value power**: expected 72-hour-retained value per hour;
- **waste rate**: effort spent on branches that are discarded or superseded without inheritance;
- **breadth**: the effective number of active domains, calculated from Shannon entropy;
- **frontier**: the outcome speed at which the fitted durable-value curve reaches its maximum.

The governing question is:

> How much durable value is being produced per unit time, and where does more speed stop helping?

## Outcome value

Each outcome is scored on five explicit 0..1 dimensions:

- `utility`
- `quality`
- `durability`
- `leverage`
- `novelty`

Weights default to equal. Alternate weights must be supplied explicitly in input.

Evidence status modifies the score:

- `verified`: 1.00
- `provisional`: 0.75
- `failed`: 0.00

This prevents a fast but unverified artifact from being priced as if it already survived contact.

## Delayed value

Young work has not yet proved durability.

For outcomes whose 72-hour retention is unknown, the model uses a Beta(1,1) posterior mean learned from all outcomes whose 72-hour retention is already known:

\[
p_{\text{survive}} = \frac{s+1}{s+f+2}
\]

where `s` is known survived outcomes and `f` is known failed outcomes.

Therefore current work contributes **expected** durable value, not fictional certainty.

Once 72-hour retention is known, observed retention replaces the expectation.

## Refinement is not churn

A superseded result can set:

```json
"disposition": "superseded",
"inherits_prior": true
```

That effort is not counted as waste. It is an ancestor of the surviving result.

Only abandoned work and supersession without inheritance contribute to waste.

This matters because an eleven-commit repair lineage is one evolving outcome, not eleven independent successes and not automatically eleven failures.

## Core metrics

For a window of duration \(T\):

\[
S_e = \frac{\text{event count}}{T}
\]

\[
S_o = \frac{\text{distinct value-bearing lineages}}{T}
\]

\[
P = \frac{\sum_i E[V_i^{72h}]}{T}
\]

`P` is **durable value power**.

For domain fractions \(p_j\):

\[
H = -\sum_j p_j \ln p_j
\]

\[
B=e^H
\]

`B` is the effective number of simultaneously active domains.

## State classifier

The latest window is compared with the previous window using a 5% default deadband.

| Outcome speed | Durable value power | State |
|---|---|---|
| up | up | `productive_overclock` |
| flat/down | up | `compression` |
| up | flat/down | `empty_acceleration` |
| down | down | `loss_of_productive_power` |
| otherwise | otherwise | `mixed_or_flat` |

**Compression is intentionally treated as a first-class success state.**
Fewer moves that create more durable value are better than maximal velocity.

## Frontier theorem

For matured historical windows, the tool fits:

\[
P(S) = aS^2+bS+c
\]

If the fitted curve is concave (\(a<0\)), the estimated value-maximizing speed is:

\[
S^*=-\frac{b}{2a}
\]

The marginal value of additional outcome speed at the current point is:

\[
\frac{dP}{dS}=2aS+b
\]

Interpretation:

- positive: additional speed is still associated with increased durable value;
- zero: estimated frontier;
- negative: more speed is associated with lower durable value.

The tool refuses to fabricate a frontier when it has fewer than three matured windows with three distinct speeds or when the observed fit is not concave.

## Time-to-frontier

If:

1. a concave frontier exists,
2. the current speed is below it,
3. at least two windows have real `end_time` timestamps,
4. recent outcome speed is increasing,

then:

\[
\tau^* = \frac{S^*-S_{\text{now}}}{dS/dt}
\]

is reported as the estimated hours until the present speed trend reaches the value frontier.

If those conditions are absent, the tool reports the forecast as unidentified rather than inventing a number.

## Input contract

```json
{
  "weights": {
    "utility": 1,
    "quality": 1,
    "durability": 1,
    "leverage": 1,
    "novelty": 1
  },
  "state_tolerance": 0.05,
  "windows": [
    {
      "id": "example-window",
      "duration_hours": 1,
      "end_time": "2026-09-13T18:00:00+00:00",
      "event_count": 11,
      "outcomes": [
        {
          "id": "artifact-v1",
          "lineage_id": "artifact",
          "domain": "code",
          "disposition": "accepted",
          "evidence_status": "verified",
          "retained_72h": null,
          "effort_units": 1,
          "dimensions": {
            "utility": 0.9,
            "quality": 0.8,
            "durability": 0.7,
            "leverage": 0.9,
            "novelty": 0.6
          }
        }
      ]
    }
  ]
}
```

Valid dispositions:

- `accepted`
- `pending`
- `discarded`
- `superseded`

A `superseded` outcome must provide `inherits_prior: true|false`.

## Commands

From the repository root:

```bash
python tools/overclock_frontier.py --self-test
python tools/overclock_frontier_test.py
python tools/overclock_frontier.py --input path/to/windows.json
```

Or pipe JSON through stdin:

```bash
cat windows.json | python tools/overclock_frontier.py
```

## Acceptance contract

The model is load-bearing only if all of these remain true:

1. raw event count cannot masquerade as accepted outcome count;
2. value is evaluated alongside speed;
3. young work is marked as expected value rather than observed durable value;
4. inherited refinement is not automatically charged as waste;
5. abandoned work is charged as waste;
6. the model can classify `empty_acceleration` when speed rises but value falls;
7. frontier prediction requires matured historical value;
8. insufficient evidence produces `unidentified`, not false precision;
9. all output is deterministic for identical input;
10. the regression contract passes before any consumer treats model output as authoritative.

## Compact law

**Speed is evidence of motion. Durable value is evidence of progress.**

The frontier is where another unit of speed stops buying another unit of durable value.
