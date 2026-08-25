# Operator Receipt Bounded Container Admission

## Purpose

Keep the final receipt snapshot's **bounded-work** claim honest at the Python container boundary.
Arbitrary `Mapping` / `dict` subclasses can execute caller-owned Python code from `items()` before
node/text budgets get a chance to bound work. Exact JSON object evidence therefore needs an exact
built-in `dict` admission gate before recursive snapshot traversal.

This skill also separates canonical receipt evidence from diagnostic root context. Caller-supplied
diagnostic context is not authority and must cross a small source ceiling before JSON escaping or
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

Supporting source:
- `tools/try_forever_operator_receipt_snapshot_admission_policy.py` — **IMPLEMENTED SUPPORTING SOURCE**.
- `tools/test_try_forever_operator_receipt_snapshot_admission_policy.py` — **SOURCE / UNEXECUTED**.
- `tools/test_try_forever_operator_receipt_snapshot_admission_owner_boundary.py` — **RED / UNEXECUTED**.

## Current owner boundary

At the current reviewed branch state, snapshot custody still:

- accepts root objects through `isinstance(value, Mapping)`;
- accepts nested objects through `isinstance(value, Mapping)`;
- therefore can invoke caller-owned mapping iteration before its declared node/text budgets bound
  traversal work;
- projects caller-supplied root diagnostic context without a separate pre-projection source ceiling.

So:

- supporting admission policy: **YES / SOURCE**;
- hostile regression source: **YES / UNEXECUTED**;
- existing snapshot owner consumption: **NO / RED**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

## Promotion cut

When the existing snapshot owner is safely promoted, the same owner mutation must:

1. admit root and nested object containers only when `type(value) is dict` (or consume the exact
   equivalent supporting predicate);
2. admit root diagnostic context before `_diagnostic_root(...)` performs JSON escaping/projection;
3. migrate the historical stateful-`dict`-subclass regression expectations to fail-closed admission;
4. retain nested detachment, exact key/value identity, diagnostic escaping/collapse, resource budgets,
   and the full capability membrane;
5. preserve one existing receipt owner and one existing snapshot organ.

## Review scar

The previous snapshot hardening successfully bounded the values produced *after* Mapping iteration,
but that does not bound arbitrary Python work executed by the Mapping implementation itself. This is a
separate source/runtime-resource boundary, not evidence that the earlier key/diagnostic repair failed.

## P0 / phone firewall

This skill has no phone/P0 authority. Phone Runtime, Phone Hands, recovery queues/relays, Nightcore,
Pocket TTS, Chromium, Context Organs, and physical acceptance remain untouched.
