# Judgement Jar: Daemon Persistence and Connector Backoff

Status: active
Scope: long-running work, polling, connectors, retries, unavailable dependencies, queued operations, and slow external systems

## Judgement

Latency is not failure. A worker must not abandon commissioned work merely because an operation is slow, queued, temporarily unavailable, rate-limited, or waiting on an external dependency.

Workers behave like daemons: preserve mission state, cool down, back off, retry sanely, and continue until the commissioned stop condition is actually met or a real owner-only boundary is reached.

## Operating rule

1. Distinguish terminal failure from transient delay, queueing, rate limits, temporary network errors, stale leases, and eventual-consistency lag.
2. On transient conditions, preserve the exact pending action and evidence, then retry with bounded exponential backoff plus jitter where practical.
3. Never busy-loop or hammer a connector. Prefer fewer, higher-value probes over repeated status spam.
4. Respect service-provided retry hints and explicit rate-limit/reset information when available.
5. Increase cooldown after repeated equivalent failures. Do not replay an identical request rapidly when nothing material has changed.
6. Between retries, inspect alternate authorized evidence or useful independent work only when it advances the same mission; do not silently change lanes or architectures.
7. For genuinely long-running operations, persist enough state/receipt information that the mission can resume after process or conversation interruption.
8. Do not report a transient wait as completion, cancellation, or permission to stop.
9. Do not ask Drew to manually babysit a retry loop when an authorized existing body/runtime can continue it.
10. When a retry finally succeeds, verify the originally commissioned outcome rather than treating transport recovery itself as completion.

## Suggested retry shape

Use bounded exponential backoff appropriate to the dependency, for example roughly 1s, 2s, 4s, 8s, 15s, 30s, then a slower steady cadence. Add jitter when multiple workers may contend. Fast local deterministic probes may use a shorter cadence; cloud/connectors should be treated more gently.

A worker may cap one foreground retry burst to protect resources, but the mission remains nonterminal. Hand continuation to the persistent daemon/mission machinery rather than declaring failure merely because the foreground burst ended.

## Stop condition

Stopping is allowed only when:

- the commissioned outcome is verified and Venice approves stopping;
- Drew explicitly cancels or changes the mission;
- a real safety/authorization boundary prevents continuation;
- the dependency is proven terminally unavailable for the commissioned lane, not merely slow or transient, and authorized recovery routes have been exhausted.

## Evidence that can change this judgement

A newer explicit instruction from Drew or a repo-local doctrine artifact that clearly supersedes this Jar.
