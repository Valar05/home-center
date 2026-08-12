# Hands Router

## Product center

Hands is Drew's deterministic remote execution tool first. Adam's existing overlay is Drew's primary surface. Vlad, Venice, Adam, and Fortress are secondary producer adapters over the same execution contract.

The CLI remains the durable contract and debugging surface; it is not the primary UX.

## Contextual intent seam

Natural-language requests belong above Hands.

Example: `find me something to watch`.

Adam may use current conversation context, durable Drive context, deterministic device/app inventory, and current public catalog data when needed to choose an appropriate title and service. That reasoning produces a concrete plan before execution.

The plan is then compiled to a finite Hands job such as an explicit Android VIEW/deep-link operation against a selected package. Hands does not decide what to watch, search screenshots, browse menus, or reinterpret the request.

This separation is mandatory:

`human intent -> contextual planner -> concrete choice -> finite signed Hands job -> deterministic transport -> executor -> receipt`

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

## User surfaces

Primary: Adam overlay natural language.

Durable/debug CLI:

- `hands status`
- `hands on`
- `hands off`
- `hands exec TARGET -- COMMAND...`
- `hands op TARGET OPERATION --args JSON [--expect JSON]`
- `hands run TARGET job.json`

Direct user jobs have producer identity `drew`.

## Media example

For `find me something to watch`:

1. Adam gathers relevant current-chat and Drive context.
2. Adam reads deterministic installed-media-app capability/inventory data.
3. Adam chooses a title/service, using current catalog lookup only if availability is uncertain.
4. Adam resolves the selection to an explicit app package plus URI/deep link.
5. Hands receives only the bounded open operation.
6. Phone Hands executes it and returns a receipt including resulting foreground package/activity.

If no deterministic launch/deep-link route exists, the plan stops at that exact boundary or emits a new explicit bounded script. It does not fall back to screenshot-driven wandering.

## Adapters

- `vlad_hands.py` fixes producer identity to `vlad`.
- `venice_hands.py` fixes producer identity to `venice`.
- Adam/Fortress may submit through the router without becoming the executor.

## Evidence states

Repository presence is implemented only. Tests establish tested. Device receipts through the selected transport establish deployed/callable/delivered. Do not launder one state into another.
