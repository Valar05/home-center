# Operator Receipt Snapshot Custody

## Purpose

Keep receipt verification bound to one caller-input observation. A verifier must not validate semantic/capability fields from one view of a stateful `Mapping` and later hash, raw-link, or derive from a different view of that same object graph.

## Authority chain

1. Capture the caller-owned receipt mapping once into a plain JSON-shaped snapshot.
2. If raw machine evidence participates, capture it once in the same verification entrypoint.
3. Run field-set, semantic, capability, digest, raw-linkage, and derivation checks against the captured snapshots only.
4. Never use a later read of the original caller-owned mapping as stronger evidence.

## Fail-closed laws

- **SEMANTIC VIEW != SIGNED VIEW** is a custody wound.
- **RAW LINKAGE VIEW != DERIVATION VIEW** is a custody wound.
- Nested caller-owned lists/mappings must be detached as part of the snapshot; a shallow top-level copy is insufficient.
- Non-finite, non-JSON-shaped, or recursion/over-nesting failures are contained as one typed snapshot-custody wound rather than escaping the verifier.
- Hostile surrogate-shaped strings may remain exact evidence; snapshot custody must not turn them into an encoding crash or replacement text.
- Snapshotting grants no authority, TESTED/runtime state, deployment, callability, execution, delivery, acceptance, phone, or P0 mutation right.

## Current repository state

- Supporting source: `tools/try_forever_operator_receipt_snapshot_custody.py` — **IMPLEMENTED SOURCE**.
- Hostile regression: `tools/test_try_forever_operator_receipt_snapshot_custody.py` — **SOURCE / UNEXECUTED**.
- Existing-owner boundary: `tools/test_try_forever_operator_receipt_snapshot_custody_owner_boundary.py` — **RED / UNEXECUTED** until owner consumption exists.
- Prepared existing-owner surgery: `patches/try-forever-operator-receipt-snapshot-custody-owner.patch` — **CORRECTED_PROPOSED_NOT_APPLIED**, locked to owner blob `34eee8e633356b012d773712ad14179b77baa3c2`.
- Existing owner consumption: **NO**.
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.
- Phone/P0 mutation authority: **NO**.

## Review scar

The first owner-boundary AST walker still descended into nested functions after merely skipping the nested function node itself. That evidence bug was corrected with an explicit recursive visitor that stops descent at nested function/lambda boundaries before the checkpoint.

## Duplicate-architecture rule

Compose the existing final-v4 receipt owner. Do not create a second receipt owner, projector, descriptor authority, validation daemon, or phone execution lane.
