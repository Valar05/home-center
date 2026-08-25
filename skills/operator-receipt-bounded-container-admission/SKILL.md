# Operator Receipt Bounded Container Admission

## Purpose

Keep receipt verification's **bounded-work** claim honest at every Python container boundary that
owns evidence, not only at the first snapshot entrypoint. Arbitrary `Mapping`, `dict` subclasses, or
caller-defined iterable families can execute caller-owned Python code before node/text/field budgets
get a chance to bound work. Exact JSON object evidence therefore uses exact built-in containers before
traversal.

This skill also separates canonical receipt evidence from diagnostic root context. Caller-supplied
diagnostic context is not authority and crosses a small source ceiling before JSON escaping or
projection can allocate work on its behalf.

## Laws

- **ARBITRARY PYTHON MAPPING != BOUNDED JSON OBJECT OBSERVATION**.
- **EXACT JSON OBJECT != DICT SUBCLASS WITH CALLER CODE**.
- **ARBITRARY ITERABLE FAMILY != BOUNDED FIELD VOCABULARY**.
- **LIST IS ALREADY EXACT; OBJECT ADMISSION MUST BE EQUALLY EXACT**.
- **PUBLIC TYPE CAPABILITY MUST NOT EXCEED RUNTIME ADMISSION**.
- **DIAGNOSTIC CONTEXT != CANONICAL RECEIPT IDENTITY**.
- **UNBOUNDED DIAGNOSTIC INPUT != BOUNDED DIAGNOSTIC PROJECTION**.
- Reject unsupported container shape; do not normalize it into authority.
- Preserve accepted diagnostic text exactly; only the existing diagnostic projector may escape or
  whole-identity-collapse it for prose.
- This admission layer owns no semantic receipt authority, digest authority, TESTED/runtime state,
  deployment, callability, execution, delivery, acceptance, phone, or P0 mutation.

## Existing organs

Compose the existing snapshot/receipt organs. Do not create another receipt owner, snapshot owner,
projector, verifier daemon, or phone execution lane.

Current source surfaces:
- `tools/try_forever_operator_receipt_snapshot_admission_policy.py` — **IMPLEMENTED SOURCE**.
- `tools/try_forever_operator_receipt_snapshot_custody.py` — **EXISTING OWNER SOURCE_WIRED**.
- `tools/try_forever_operator_receipt_derivation_custody.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/try_forever_operator_receipt_identity_fieldset.py` — **EXACT-CONTAINER SOURCE_WIRED**.
- `tools/test_try_forever_operator_receipt_exact_container_surfaces.py` — **SOURCE / UNEXECUTED**.
- earlier snapshot admission regressions — **SOURCE / UNEXECUTED**.

## Current source truth

The snapshot-custody owner:

- admits root objects only through exact built-in-dict admission;
- admits nested objects through the same exact gate before `items()` traversal;
- rejects Mapping subclasses/custom mappings without invoking caller-owned iteration;
- admits root diagnostic context before `_diagnostic_root(...)` performs escaping/projection;
- preserves nested detachment, exact key/value identity, resource budgets, capability membrane, and
  one-owner architecture.

The derivation-custody surface now:

- advertises exact built-in `dict` receipt/raw inputs rather than arbitrary `Mapping` capability;
- snapshots both caller inputs before schema/field/nested-evidence reads;
- admits `allowed_extra_fields` only as one exact tuple of exact strings before iteration;
- preserves the existing self-integrity/projector owner and grants no new authority.

The identity-fieldset surface now:

- advertises and admits one exact built-in `dict` receipt before `keys()` traversal;
- admits operator-owned and denied-capability field families only as exact tuples of exact strings;
- preserves intentional exact-false field reassertion and the existing final-v4 namespace law.

Current known boundary still open:

- `tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` and
  `tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` still expose some public/supporting
  `Mapping` contracts. Their real final-owner path often reaches them with already-detached exact dicts,
  but those public type/evidence surfaces must not be called fully converged until they are separately
  reviewed and, where justified, tightened. Do not promote this heartbeat's two repaired surfaces into
  blanket receipt-stack exactness.

So:

- supporting admission policy: **YES / SOURCE**;
- snapshot owner consumption: **YES / SOURCE_WIRED**;
- derivation exact-container custody: **YES / SOURCE_WIRED**;
- fieldset exact-container custody: **YES / SOURCE_WIRED**;
- hostile regression source: **YES / UNEXECUTED**;
- whole receipt stack exact-container convergence: **NO / PARTIAL**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

## Review scar

Earlier snapshot hardening bounded values produced *after* Mapping iteration, but that did not bound
arbitrary Python work executed by the Mapping implementation itself. The first repair moved admission
ahead of snapshot traversal. The 2026-08-25 09:00 review found the same contract smell in neighboring
receipt derivation and final-fieldset custody. Those two surfaces now use exact containers and bounded
snapshot custody, while broader Mapping contracts elsewhere remain an explicit follow-up boundary
rather than being silently green-painted.

## P0 / phone firewall

This skill has no phone/P0 authority. Phone Runtime, Phone Hands, recovery queues/relays, Nightcore,
Pocket TTS, Chromium, Context Organs, and physical acceptance remain untouched.
