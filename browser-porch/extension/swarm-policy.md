# Chromium Throne Swarm Policy

Chromium Throne owns continuity. ChatGPT chat-mode Instant workers own one bounded slice.

## Worker cycle

1. Dispatch one slice to a fresh worker when possible.
2. Capture the latest assistant checkpoint after the slice.
3. If the checkpoint contains a valid `HANDOFF` packet, parse it and enqueue the packet's `EXACT NEXT ACTION` as a fresh-worker job.
4. Carry the handoff's durable context, completed evidence, unmet acceptance, and active constraints into the next worker context.
5. Never ask one thread to recover from obvious context choke. Rotate instead.
6. Never fan a single tightly coupled write across multiple workers. Parallelism is only for independent slices.
7. Stop the swarm when acceptance is met, a destructive/external/human boundary is reached, or a worker reports a falsification packet.

## Handoff packet

A valid handoff contains exactly these six headings:

- DURABLE CONTEXT
- COMPLETED EVIDENCE
- CURRENT SLICE
- UNMET ACCEPTANCE
- ACTIVE CONSTRAINTS
- EXACT NEXT ACTION

The parser is deliberately strict. Malformed handoffs are captured as evidence but are not auto-dispatched.

## Babysitting

The throne should prefer progress over worker longevity. Workers are cheap; context drift is expensive. Rotate threads when the worker repeats itself, loses constraints, invents adjacent architecture, or cannot state the current done condition cleanly.
