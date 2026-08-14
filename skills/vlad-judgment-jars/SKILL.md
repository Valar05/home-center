# Vlad Judgment Jar Fast Access

## Trigger
Run whenever Vlad is asked to consult, invoke, impersonate, route through, compare, or review with one or more Judgment Jars.

## Authority
Home Center owns the jars. `tools/vlad_judgment_jars.py` is a verified read cache and receipt outbox, not a second source of truth.

## Procedure
1. Check `status`. If no verified snapshot exists, sync through the Home Center daemon before using a jar.
2. Resolve by canonical ID or alias locally. Search is allowed for discovery; do not guess which jar an ambiguous alias means.
3. For actual judgment, use the `use` command or `POST /v1/use`. Administrative `get` is not an invocation.
4. Preserve the returned `receipt_id`, exact `jar_id`, and `jar_revision` with the worker request.
5. Run the jar against the bounded commission without merging its output with another jar before provenance is recorded.
6. Close the receipt with `complete` or the receipt completion endpoint. Record the output kind, durable output reference when one exists, output digest, and terminal status.
7. Push receipts to Home Center. If offline, leave them pending; the oldest pending receipt is retried first.
8. Return or persist the Home Center delivery/readback receipt before claiming the jar use is delivered.

## Hard failures
- No current or last-verified authoritative snapshot.
- Alias collision or ambiguous routing.
- Actual jar use through `get`, direct file reads, copied prompts, or chat memory.
- Missing open receipt or terminal output-kind receipt.
- Local receipt claimed as Home Center-delivered.
- A hard-coded list presented as “all jars.”
- Creation of a parallel watcher, registry, or source of truth.

## Acceptance
A canary passes only when Vlad resolves a jar by alias from the verified local cache, opens one receipt, produces a typed output, closes the receipt, synchronizes it through the Home Center daemon, and reads the same receipt back from Home Center.
