# Operator Receipt Bounded Container Admission

## Purpose

Keep the final receipt snapshot's **bounded-work** claim honest at the Python container boundary.
Arbitrary `Mapping` / `dict` subclasses can execute caller-owned Python code from `items()` before
node/text budgets get a chance to bound work. Exact JSON object evidence therefore uses an exact
built-in `dict` admission gate before recursive snapshot traversal.

This skill also separates canonical receipt evidence from diagnostic root context. Caller-supplied
diagnostic context is not authority and crosses a small source ceiling before JSON escaping or
projection can allocate work on its behalf.

## Laws

- **ARBITRARY PYTHON MAPPING != BOUNDED JSON OBJECT OBSERVATION**.
- **EXACT JSON OBJECT != DICT SUBCLASS WITH CALLER CODE**.
- **LIST IS ALREADY EXACT; OBJECT ADMISSION MUST BE EQUALLY EXACT**.
- **DIAGNOSTIC CONTEXT != CANONICAL RECEIPT IDENTITY**.
- **UNBOUNDED DIAGNOSTIC INPUT != BOUNDED DIAGNOSTIC PROJECTION**.
- Reject unsupported container shape; do not normalize it into authority.
- Preserve accepted diagnostic text exactly; only the existing diagnostic projector may escape or
  whole-identity-collapse it for prose.
- This admission layer owns no semantic receipt authority, digest authority, TESTED/runtime state,
  deployment, callability, execution, delivery, acceptance, phone, or P0 mutation.

## Existing organs

Compose the existing `tools/try_forever_operator_receipt_snapshot_custody.py`. Do not create another
receipt owner, snapshot owner, projector, verifier daemon, or phone execution lane.

Current source surfaces:
- `tools/try_forever_operator_receipt_snapshot_admission_policy.py` — **IMPLEMENTED SOURCE**.
- `tools/try_forever_operator_receipt_snapshot_custody.py` — **EXISTING OWNER SOURCE_WIRED**.
- `tools/test_try_forever_operator_receipt_snapshot_admission_policy.py` — **SOURCE / UNEXECUTED**.
- `tools/test_try_forever_operator_receipt_snapshot_admission_owner_boundary.py` — **SOURCE-WIRED BOUNDARY / UNEXECUTED**.

## Current owner truth

The existing snapshot-custody owner now:

- admits root objects only through exact built-in-dict admission;
- admits nested objects through the same exact gate before `items()` traversal;
- rejects Mapping subclasses/custom mappings without invoking caller-owned iteration;
- admits root diagnostic context before `_diagnostic_root(...)` performs escaping/projection;
- preserves the existing nested detachment, exact key/value identity, resource budgets, capability
  membrane, and one-owner architecture.

So:

- supporting admission policy: **YES / SOURCE**;
- existing snapshot owner consumption: **YES / SOURCE_WIRED**;
- hostile regression source: **YES / UNEXECUTED**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

## Review scar

Earlier snapshot hardening bounded values produced *after* Mapping iteration, but that did not bound
arbitrary Python work executed by the Mapping implementation itself. The repair moved admission ahead
of traversal and moved diagnostic-context admission ahead of projection. Source wiring is real;
regression execution and runtime proof are still separate gates.

## P0 / phone firewall

This skill has no phone/P0 authority. Phone Runtime, Phone Hands, recovery queues/relays, Nightcore,
Pocket TTS, Chromium, Context Organs, and physical acceptance remain untouched.
