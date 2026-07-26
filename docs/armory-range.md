# Armory Range

Armory Range is Home Center's private, append-only ledger for events whose subject does not need a pre-existing cloud key.

## Voice surface

- `armory receipt`: record one or more immutable casings.
- `armory recount`: aggregate matching casings.
- `armory casing`: retrieve recent matching casings.
- “What was my last shot fired in the range?”: call `armory.casing` with `action=fired` and `lastOnly=true`.

Example:

> Two 9mm fired. Record in the armory.

The receipt expands this into two immutable casing events. Every casing has a mandatory ISO timestamp. When the caller gives no explicit times, the API uses the server receipt time for each casing and labels the source `server_receipt`; it never fabricates spacing.

## Operation contract

All operations use the existing Home Center `drive_operation` tool.

### `armory.receipt`

Input:

- `ammunition`, `item`, or `subject`: required label; no pre-existing key required.
- `count`: 1–500, default 1.
- `action`: default `fired`.
- `unit`: default `round`.
- `timestamp`, `firedAt`, `occurredAt`, or `timestamps`: optional explicit time. An array must contain one timestamp or exactly one per casing.
- `requestId` or `idempotencyKey`: optional but recommended for exact replay protection.
- `timezone`, `attributes`, and `note`: optional context.

Output includes the receipt, one casing ID per unit, mandatory timestamps, timestamp provenance, and an input hash. Reusing the same request ID with different input fails closed.

### `armory.recount`

Filters by `ammunition`/`item`, `action`, `since`, and `until`. Returns grouped counts and the last matching casing.

### `armory.casing`

Uses the same filters. `lastOnly=true` returns the last matching casing. Otherwise `limit` is 1–100.

## Boundaries

- Owner-scoped and private through Home Center authentication.
- Append-only casing records.
- No public URL, signed URL, spreadsheet, job, worker, or ChatGPT memory dependency.
- Repository code is executable truth; the runtime ledger is Firestore.
