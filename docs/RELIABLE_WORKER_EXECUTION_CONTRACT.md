# Reliable Worker Execution Contract

Status: repository contract candidate  
Schema: `ops/worker_execution_contract.v1.json`  
Validation: `node tools/worker_execution_contract_test.mjs`

## Outcome

Long-running, expensive, externally billed, or failure-prone work returns a durable receipt instead of holding a client connection open. The same contract governs audio, Blender, Codex, media, browser, and future workers.

Worker sizing is defined separately by `ops/worker_profiles.v1.json`. Sizing answers **where and with what resources** work runs. This contract answers **how work remains safe, recoverable, and observable**.

## Exact intent and idempotency

Every submitted job binds:

- `requestId`;
- `operation`;
- canonical normalized input;
- `inputHash`;
- execution policy;
- publication policy.

A repeated `requestId` with the same `inputHash` returns the existing receipt and attaches to the existing job. A repeated `requestId` with a different `inputHash` fails closed with `REQUEST_ID_CONFLICT`.

A request ID identifies one exact intent. It is not a reusable slot.

## Receipt-first submission

Submission validates and durably records the job before returning. The accepted receipt contains at least:

- `jobId`;
- `requestId`;
- `inputHash`;
- `state`;
- `acceptedAt`;
- status resource reference;
- publication policy;
- whether the caller attached to existing work.

An accepted receipt proves durable admission, not completion.

## State machine

Allowed states are:

`accepted -> queued -> leased -> running -> checkpointed -> publishing -> completed`

Terminal alternatives are `failed`, `quarantined`, and `cancelled`.

A terminal job never silently returns to execution. Recovery from `checkpointed` may return to `queued` or `leased` only through an explicit coordinator transition.

## Lease and heartbeat

Only the holder of the current time-bounded lease may mutate active execution state. The lease records worker, lease ID, attempt number, acquisition, heartbeat, and expiration timestamps.

Heartbeats contain bounded status only: stage, checkpoint, counters, last confirmed external operation, worker health, and lease expiration. Heartbeats prove liveness, not correctness.

No heartbeat means unknown. An expired lease is not proof that an external provider did nothing.

## Checkpoints

Workers checkpoint before and after expensive or irreversible boundaries. A checkpoint records completed and pending units, artifact references, provider operation identifiers, billing certainty, resumable state, input hash, and code revision.

Large data remains in referenced artifacts. Checkpoints and status records do not embed full logs, scripts, media, or provider payloads.

## Provider safety

Every external operation is classified as one of:

- `safe_to_retry`;
- `idempotent_with_provider_key`;
- `ambiguous_cost_bearing`;
- `non_retryable`.

When a paid or irreversible provider request may have been accepted but its response was lost, the job enters `quarantined`. It is never retried automatically. Provider IDs, timestamps, checkpoint evidence, and billing certainty are preserved for reconciliation.

Infrastructure retries must not become accidental billing retries.

## Publication policy

Publication is an explicit stage and an enforced boundary. The request names allowed destinations, prefixes, visibility, and retention.

`publishToDrive: false` forbids Drive copies, temporary mirrors, fallback uploads, and convenience publication. Generation may complete while publication fails; those are separate facts.

## Verification boundary

Workers may verify mechanical facts: existence, byte count, checksum, decode, duration, frame count, schema validity, and destination readback.

Workers do not claim visual, editorial, audio-quality, canon, or human acceptance. Execution evidence and human observation remain separate authorities.

## Context protection

Status responses contain only current state, stage, bounded progress, blocking condition, artifact references, and next permitted transition. Diagnostics and large outputs are stored externally and linked.

Conversation context is not an operational log sink.

## Required acceptance tests

1. Long work returns a durable accepted receipt before completion.
2. Identical replay attaches without duplicate execution.
3. Conflicting replay fails closed.
4. Recovery resumes from the newest verified checkpoint without repeating completed units.
5. An expired lease cannot permit two workers to publish one result.
6. Ambiguous paid-provider outcomes quarantine without automatic retry.
7. Safe transient work retries only within declared limits.
8. `publishToDrive: false` creates no Drive artifact.
9. Large output is exposed by resource reference, not inline status.
10. Mechanical verification remains separate from human acceptance.
11. Status remains bounded regardless of log or artifact size.
12. Terminal jobs cannot silently re-execute.

## Promotion order

1. Merge this shared contract and validator.
2. Bind one existing worker as the reference implementation.
3. Pass the complete acceptance suite against that worker.
4. Migrate other workers one at a time.

The audio worker is the strongest current reference candidate because it already has receipts, hashes, leases, heartbeats, publication boundaries, and paid-provider quarantine evidence. Those local mechanisms must be adapted to the shared contract rather than copied into every worker.