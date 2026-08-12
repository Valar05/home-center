# Hands Router

## Product center

Hands is Drew's deterministic remote execution tool first. Vlad, Venice, Adam, and Fortress are secondary producer adapters over the same contract.

The primary interface is `hands`.

## Execution seam

Phone Hands and Computer Hands execute finite scripted jobs. They are not agents.

Hands MUST NOT:

- inspect screenshots and decide what to do next
- guess and check
- invent follow-up actions
- convert a goal into actions at execution time
- run a model in the routing or safety path

A model or human may author a finite job before enqueue. After enqueue, the exact signed script is the work.

## Job contract

`hands-router-job-v2` contains a producer, target, finite ordered steps, transport preference, TTL, and total runtime bound. Every step names an allowed operation and structured arguments, with an optional mechanical expectation.

Unknown operations, excess steps, oversized jobs, invalid runtime bounds, expired jobs, and invalid signatures are rejected deterministically.

## Transport

Default preference:

1. SSH
2. direct WLAN adapter
3. Computer Hands fallback

Fallback changes transport only. It never changes or expands the job.

## Safety

Hands is not a permission gate. Ordinary work proceeds without model judgment, warnings, or moralizing.

The router blocks only explicit/high-confidence objectively destructive mechanics in its deterministic signature set. Queue entries are HMAC-signed locally so network presence alone cannot mint executable work.

`hands off` pauses queued jobs without deleting them. `hands on` resumes. The daemon can also be stopped entirely.

## User CLI

- `hands status`
- `hands on`
- `hands off`
- `hands exec TARGET -- COMMAND...`
- `hands op TARGET OPERATION --args JSON [--expect JSON]`
- `hands run TARGET job.json`

Direct user jobs have producer identity `drew`.

## Adapters

- `vlad_hands.py` fixes producer identity to `vlad`.
- `venice_hands.py` fixes producer identity to `venice`.
- Adam/Fortress may submit through the router without becoming the executor.

## Evidence states

Repository presence is implemented only. Tests establish tested. Device receipts through the selected transport establish deployed/callable/delivered. Do not launder one state into another.
