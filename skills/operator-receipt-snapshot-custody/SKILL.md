# Operator Receipt Snapshot Custody

## Purpose

Keep receipt verification bound to one caller-input observation **and one bounded exact JSON shape**. A verifier must not validate semantic/capability fields from one view of caller-owned evidence, later hash/derive from a second view, or let Python JSON conveniences normalize caller evidence before verification.

Exact evidence and error/report prose are separate contracts. Caller keys remain exact JSON identity inside the detached snapshot, while diagnostic field paths are bounded ASCII-safe projections. Hostile line breaks, bidi/control/surrogate text, or giant/deep names must not become raw operator/log text or a second unbounded resource throat. Definitely-long diagnostic segments collapse to a whole-identity digest **before** JSON escaping so projection does not create a larger temporary allocation merely to decide that the segment must collapse.

## Authority chain

1. Capture the caller-owned receipt object once into a bounded plain JSON-shaped snapshot.
2. If raw machine evidence participates, capture it once in the same verification entrypoint.
3. Admit only exact JSON null/boolean/number/string/list/object values; every object level requires the exact built-in `dict` container and non-empty string keys.
4. Enforce depth/node/text/integer-magnitude/encoded-byte budgets before later semantic/digest/linkage work.
5. Preserve accepted mapping keys exactly in canonical evidence; project only diagnostic context and error paths.
6. Collapse definitely-overlong diagnostic segments before JSON escaping; do not pay escaping expansion merely to discover that a digest marker is required.
7. Run field-set, semantic, capability, digest, raw-linkage, and derivation checks against the captured snapshots only.
8. Never use a later read of the original caller-owned object as stronger evidence.

## Fail-closed laws

- **SEMANTIC VIEW != SIGNED VIEW** is a custody wound.
- **RAW LINKAGE VIEW != DERIVATION VIEW** is a custody wound.
- **PUBLIC MAPPING TYPE != EXACT BUILT-IN DICT CONTRACT**: developer-facing type hints must not advertise arbitrary `Mapping` capability that runtime admission deliberately rejects.
- **ARBITRARY PYTHON MAPPING != BOUNDED JSON OBJECT OBSERVATION**: custom `Mapping` implementations and `dict` subclasses are rejected before caller-owned traversal callbacks can run.
- **PYTHON JSON CONVENIENCE != EXACT JSON EVIDENCE**: tuples and non-string mapping keys are rejected rather than normalized.
- **NESTED KEY NORMALIZATION != IDENTITY PRESERVATION**: non-empty string-key admission applies at every admitted built-in object level, not only the root.
- **EXACT EVIDENCE KEY != RAW DIAGNOSTIC TEXT**: newline, bidi/control/format, lone-surrogate, and other hostile key text remains exact evidence but must be escaped or whole-identity-collapsed before entering an error/log path.
- **DIAGNOSTIC PATH != AUTHORITY**: bounded path/digest markers are operator evidence only and never replace the exact mapping key stored in the snapshot.
- **ARBITRARY PARTIAL PREFIX != SAFE DIAGNOSTIC IDENTITY**: overlong diagnostic segments collapse as whole identities with a deterministic digest instead of exposing an arbitrary partial Unicode prefix.
- **BOUNDED DIAGNOSTIC OUTPUT != PERMISSION FOR PRE-COLLAPSE ESCAPE EXPANSION**: if exact source length already proves a segment will collapse, choose the digest before `ensure_ascii` expansion.
- **DEEP KEY PATH != UNBOUNDED ERROR PROSE**: nested diagnostic paths have an independent hard ceiling even while canonical evidence remains under the source text budget.
- **EXACT JSON INTEGER SHAPE != UNBOUNDED DECIMAL CONVERSION RIGHT**: one integer scalar must fit the declared pre-serialization magnitude throat.
- **SOURCE CEILING != GUARANTEED SERIALIZER ACCEPTANCE**: a stricter process-global integer conversion policy may still reject evidence and remains a valid independent fail-closed boundary.
- **UNBOUNDED SNAPSHOT WORK != VERIFICATION**: over-depth, over-node, over-text, over-integer-magnitude, or over-encoded-byte evidence fails before semantic/hash/linkage work.
- Duplicate JSON member detection belongs at the JSON/parser boundary before a Python `dict` exists; snapshot custody must not pretend a hostile `Mapping.items()` stream is an admitted duplicate-member channel.
- Nested caller-owned plain lists and exact built-in dicts must be detached as part of the snapshot; a shallow top-level copy is insufficient.
- Non-finite, non-JSON-shaped, recursion/over-nesting, or caller-observation failures are contained as typed snapshot-custody wounds rather than escaping the verifier.
- Hostile surrogate-shaped strings may remain exact evidence; snapshot custody must not turn them into an encoding crash or replacement text.
- Snapshotting grants no authority, TESTED/runtime state, deployment, callability, execution, delivery, acceptance, phone, or P0 mutation right.

## Resource authority

Current source constants in `tools/try_forever_operator_receipt_snapshot_custody.py`:

- depth: 64;
- nodes: 50,000;
- total canonical string code points: 1,048,576;
- integer magnitude: 14,284 binary bits (conservative source ceiling for at most 4,300 decimal digits);
- detached deterministic JSON serialization: 8 MiB;
- one diagnostic segment: 96 projected characters, with definitely-long exact source collapsing to a whole-identity digest before JSON escaping;
- one diagnostic path: 256 characters before whole-path digest collapse.

The integer throat is checked with `int.bit_length()` before decimal JSON serialization, so it does not rely on process-global `sys.set_int_max_str_digits` state. A stricter process policy may reject smaller values later; that is fail-closed, not a source guarantee violation. Diagnostic ceilings constrain only error/report surfaces and do not truncate or rewrite canonical evidence. These are source resource ceilings, not runtime throughput claims.

## Current repository state

- Supporting source: `tools/try_forever_operator_receipt_snapshot_custody.py` — **IMPLEMENTED SOURCE / v2**; exact built-in-object admission, exact evidence, resource throats, pre-escape long-diagnostic collapse, bounded diagnostic projection, and public `dict[str, object]` typing are source-wired in the same organ.
- Public type contract now matches runtime exact built-in `dict` admission for `snapshot_json_mapping(...)` and `snapshot_verification_inputs(...)` — **SOURCE_WIRED**.
- Hostile regression: `tools/test_try_forever_operator_receipt_snapshot_custody.py` — **SOURCE / UNEXECUTED**; it pins callback-free rejection of `dict` subclasses/custom `Mapping`, ordinary large-integer acceptance, over-ceiling rejection, exact hostile-key preservation, escaped control/bidi/surrogate diagnostics, whole-identity collapse, pre-escape collapse of definitely-long diagnostic source, and bounded deep paths.
- Public type-contract regression: `tools/test_try_forever_exact_json_public_type_contract.py` — **SOURCE / UNEXECUTED**; it pins exact built-in-dict typing across snapshot custody and canonical fingerprint entrypoints.
- Existing-owner boundary: `tools/test_try_forever_operator_receipt_snapshot_custody_owner_boundary.py` — **SOURCE_WIRED / UNEXECUTED**.
- Existing owner: `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` — **SOURCE_WIRED**; it already consumes `snapshot_verification_inputs(...)`, so the strengthened resource/diagnostic/public-contract behavior stays on the existing owner path without creating another receipt owner.
- Existing owner consumption: **YES / SOURCE_WIRED**.
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.
- Phone/P0 mutation authority: **NO**.

## Review scars

- The first owner-boundary AST walker descended into nested functions after merely skipping the nested function node itself. That evidence bug was corrected with an explicit recursive visitor that stops descent at nested function/lambda boundaries.
- The original snapshot helper used `dict(value)` plus a JSON round-trip. That detached nested structure, but it let JSON normalize tuples and non-string nested keys and had no pre-serialization resource throat. v2 replaces that shape with one bounded recursive observation into exact JSON values.
- The encoded-byte ceiling alone is too late to bound giant integer decimal-conversion work. Integer magnitude is now admitted before serialization using a deterministic bit-length ceiling.
- The first integer regression incorrectly assumed the source ceiling itself must serialize under every process-wide integer conversion policy. Review corrected it: the source ceiling prevents larger inputs, while a stricter runtime policy may still fail closed sooner.
- Diagnostic review found a separate evidence channel after the resource work: exact mapping keys were being concatenated directly into recursive `field` prose, so hostile line breaks/bidi/surrogates or deep names could contaminate logs and expand diagnostics independently of canonical evidence. The source now keeps the exact key in the snapshot while bounding/escaping only the diagnostic projection.
- Cross-pollination from the semantic producer found a second diagnostic resource scar: `_diagnostic_segment(...)` bounded its final output but still called `json.dumps(..., ensure_ascii=True)` on definitely-overlong exact source first. That could multiply a bounded source key into a larger temporary escape allocation even though the final result was inevitably a digest marker. The same existing snapshot organ now collapses definitely-long segments before escaping, and the hostile source fixture guards the call order.
- After exact built-in `dict` admission became source-wired, older doctrine about hostile `Mapping` implementations emitting duplicate fields became stale. That wording was retired instead of preserving a fictional traversal channel; duplicate JSON member custody belongs upstream of Python object materialization.
- The 08:00 public-contract audit found runtime exact-container custody stricter than its developer-facing `Mapping` annotations. Fingerprint and snapshot public signatures are now narrowed to the exact built-in-dict contract without changing runtime acceptance semantics.
- Source wiring is not regression execution. The direct owner methods consume snapshot custody, but the hostile regression suite remains unexecuted in authenticated CI evidence.

## Duplicate-architecture rule

Compose the existing final-v4 receipt owner. Do not create a second receipt owner, projector, descriptor authority, validation daemon, or phone execution lane.
