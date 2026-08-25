# Operator Receipt Snapshot Custody

## Purpose

Keep receipt verification bound to one caller-input observation **and one bounded exact JSON shape**. A verifier must not validate semantic/capability fields from one view of a stateful `Mapping`, later hash/derive from a second view, or let Python JSON conveniences normalize caller evidence before verification.

## Authority chain

1. Capture the caller-owned receipt mapping once into a bounded plain JSON-shaped snapshot.
2. If raw machine evidence participates, capture it once in the same verification entrypoint.
3. Admit only exact JSON null/boolean/number/string/list/object values; every mapping level requires non-empty string keys.
4. Enforce depth/node/text/integer-magnitude/encoded-byte budgets before later semantic/digest/linkage work.
5. Run field-set, semantic, capability, digest, raw-linkage, and derivation checks against the captured snapshots only.
6. Never use a later read of the original caller-owned mapping as stronger evidence.

## Fail-closed laws

- **SEMANTIC VIEW != SIGNED VIEW** is a custody wound.
- **RAW LINKAGE VIEW != DERIVATION VIEW** is a custody wound.
- **PYTHON JSON CONVENIENCE != EXACT JSON EVIDENCE**: tuples and non-string mapping keys are rejected rather than normalized.
- **NESTED KEY NORMALIZATION != IDENTITY PRESERVATION**: non-empty string-key admission applies at every mapping level, not only the root.
- **EXACT JSON INTEGER SHAPE != UNBOUNDED DECIMAL CONVERSION RIGHT**: one integer scalar must fit the declared pre-serialization magnitude throat.
- **SOURCE CEILING != GUARANTEED SERIALIZER ACCEPTANCE**: a stricter process-global integer conversion policy may still reject evidence and remains a valid independent fail-closed boundary.
- **UNBOUNDED SNAPSHOT WORK != VERIFICATION**: over-depth, over-node, over-text, over-integer-magnitude, or over-encoded-byte evidence fails before semantic/hash/linkage work.
- Duplicate fields emitted by a hostile Mapping implementation fail closed instead of becoming first/last-wins evidence.
- Nested caller-owned lists/mappings must be detached as part of the snapshot; a shallow top-level copy is insufficient.
- Non-finite, non-JSON-shaped, recursion/over-nesting, or caller-observation failures are contained as typed snapshot-custody wounds rather than escaping the verifier.
- Hostile surrogate-shaped strings may remain exact evidence; snapshot custody must not turn them into an encoding crash or replacement text.
- Snapshotting grants no authority, TESTED/runtime state, deployment, callability, execution, delivery, acceptance, phone, or P0 mutation right.

## Resource authority

Current source constants in `tools/try_forever_operator_receipt_snapshot_custody.py`:

- depth: 64;
- nodes: 50,000;
- total string code points: 1,048,576;
- integer magnitude: 14,284 binary bits (conservative source ceiling for at most 4,300 decimal digits);
- detached deterministic JSON serialization: 8 MiB.

The integer throat is checked with `int.bit_length()` before decimal JSON serialization, so it does not rely on process-global `sys.set_int_max_str_digits` state. A stricter process policy may reject smaller values later; that is fail-closed, not a source guarantee violation. These are source resource ceilings, not runtime throughput claims.

## Current repository state

- Supporting source: `tools/try_forever_operator_receipt_snapshot_custody.py` — **IMPLEMENTED SOURCE / v2**.
- Hostile regression: `tools/test_try_forever_operator_receipt_snapshot_custody.py` — **SOURCE / UNEXECUTED**; it pins ordinary large-integer acceptance and over-ceiling rejection without assuming the process-wide integer conversion limit equals the source ceiling.
- Existing-owner boundary: `tools/test_try_forever_operator_receipt_snapshot_custody_owner_boundary.py` — **SOURCE_WIRED / UNEXECUTED**.
- Existing owner: `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` — **SOURCE_WIRED**; it already consumes `snapshot_verification_inputs(...)`, so the strengthened integer/resource contract is on the existing owner path without creating another receipt owner.
- Existing owner consumption: **YES / SOURCE_WIRED**.
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.
- Phone/P0 mutation authority: **NO**.

## Review scars

- The first owner-boundary AST walker descended into nested functions after merely skipping the nested function node itself. That evidence bug was corrected with an explicit recursive visitor that stops descent at nested function/lambda boundaries.
- The original snapshot helper used `dict(value)` plus a JSON round-trip. That detached nested structure, but it let JSON normalize tuples and non-string nested keys and had no pre-serialization resource throat. v2 replaces that shape with one bounded recursive observation into exact JSON values.
- The encoded-byte ceiling alone is too late to bound giant integer decimal-conversion work. Integer magnitude is now admitted before serialization using a deterministic bit-length ceiling.
- The first integer regression incorrectly assumed the source ceiling itself must serialize under every process-wide integer conversion policy. Review corrected it: the source ceiling prevents larger inputs, while a stricter runtime policy may still fail closed sooner.
- Source wiring is not regression execution. The direct owner methods consume snapshot custody, but the hostile regression suite remains unexecuted in authenticated CI evidence.

## Duplicate-architecture rule

Compose the existing final-v4 receipt owner. Do not create a second receipt owner, projector, descriptor authority, validation daemon, or phone execution lane.
