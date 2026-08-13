# Chromium Throne Swarm Policy

Chromium Throne owns continuity. ChatGPT **Pro reasoning** workers own one bounded slice. Instant is not the default worker doctrine and may appear only after an explicit later override from Drew.

Every worker carries mandatory Venice doctrine: the primary Venice path is direct execution of Venice's applicable Judgment Jars by the current ChatGPT worker as a separate adversarial pass. This is the normal fast path, not fallback emulation. A live/local Venice runtime is optional specialized machinery, not a dependency for ordinary review.

## Worker cycle

1. Dispatch one bounded slice to a fresh Pro-reasoning worker when possible.
2. Worker researches, plans, selects relevant Judgment Jars, antagonizes the plan, and performs a Venice Judgment-Jar plan review before substantive mutation. Non-trivial execution requires `PLAN_ALLOWED`.
3. Capture the latest assistant checkpoint after useful progress.
4. Before a worker may stop, finish, or hand off a slice as complete, it performs a fresh Venice Judgment-Jar completion review.
5. `CONTINUE_REQUIRED` means the worker keeps working the same commissioned slice, validates again, and returns to Venice. A response boundary is not a stop condition.
6. `STOP_ALLOWED` is the only normal Venice permission to stop the current slice. `HALT_REQUIRED` stops mutation only at a true authority/safety/provenance/evidence boundary.
7. If the checkpoint contains a valid `HANDOFF` packet because the thread is choked, parse it and enqueue the packet's `EXACT NEXT ACTION` as a fresh-worker job. Choke rotation preserves the Venice continuation obligation in the successor.
8. Carry durable context, completed evidence, unmet acceptance, active constraints, selected jars/reviewer precedent, and current Venice directive into the next worker context.
9. Never ask one thread to recover from obvious context choke. Rotate instead.
10. Never fan a single tightly coupled write across multiple workers. Parallelism is only for independent slices.
11. The swarm may stop only when the operator explicitly stops it, a true `HALT_REQUIRED` boundary exists, or the commissioned stopping/release gates are satisfied. Apparent completion without Venice `STOP_ALLOWED` is not terminal.

## Handoff packet

A valid handoff contains exactly these six headings:

- DURABLE CONTEXT
- COMPLETED EVIDENCE
- CURRENT SLICE
- UNMET ACCEPTANCE
- ACTIVE CONSTRAINTS
- EXACT NEXT ACTION

The parser is deliberately strict. Malformed handoffs are captured as evidence but are not auto-dispatched. A handoff caused by thread choke is continuity, not completion, and does not waive Venice.

## Babysitting

The throne should prefer progress over worker longevity. Workers are cheap; context drift is expensive. Rotate threads when the worker repeats itself, loses constraints, invents adjacent architecture, cannot state the current done condition cleanly, or attempts to stop without Venice permission.
