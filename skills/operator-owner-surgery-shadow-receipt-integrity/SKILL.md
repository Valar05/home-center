# Operator Owner Surgery Shadow Receipt Integrity

## Purpose
Keep descriptor-shadow evidence honest at the operator/temporal-binding boundary without creating a second custody authority.

This skill owns two distinctions:

1. **comparison false != comparison unavailable**;
2. **matching canonical-result SHA != complete shadow receipt context**.

It does not own patch promotion, canonical v10 custody, descriptor backend selection, Android runtime, phone/P0 execution, deployment, delivery, or acceptance.

## Core laws
`FALSE COMPARISON = COMPLETED DIVERGENCE`.

`NULL COMPARISON = COMPARISON NOT COMPLETED`.

`WOUND / UNAVAILABLE STATE != SHADOW_DIVERGED`.

`SHADOW_DIVERGED REQUIRES THREE COMPLETED BOOLEAN COMPARISONS + AT LEAST ONE FALSE`.

`SHADOW MATCH REQUIRES THREE TRUE COMPARISONS`.

`CANONICAL RESULT SHA MATCH != SHADOW RECEIPT CONTEXT ADMITTED`.

`COMPLETED SHADOW COMPARISON CONTEXT = EXACT CANONICAL V10 SCHEMA + EXACT EVIDENCE-COMPLETE BOOLEAN + CANONICAL PORTABLE AUTHORITY BACKEND + EXACT SUPPORTED DESCRIPTOR CAPABILITY`.

`SHADOW RECEIPT INTEGRITY != TEMPORAL BINDING != PROMOTION AUTHORITY`.

`SUPPORTING SOURCE != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Source organs
`tools/try_forever_owner_surgery_shadow_receipt_projection.py` is existing operator-facing source. It now requires:
- `SHADOW_MATCH` => `(True, True, True)`;
- `SHADOW_DIVERGED` => three non-null booleans with at least one `False`;
- `CANONICAL_SCHEMA_WOUND`, `CANONICAL_WOUND`, `PORTABLE_SHADOW_WOUND`, `DESCRIPTOR_UNAVAILABLE`, `CAPABILITY_WOUND`, and `DESCRIPTOR_WOUND` => `(None, None, None)` because comparison did not complete.

This intentionally exposes a current upstream wound: descriptor-shadow v3 currently emits `(False, False, False)` on `DESCRIPTOR_WOUND`. The receipt projector now rejects that legacy shape instead of displaying unavailable comparison as measured divergence. Upstream shadow-owner correction is **not** claimed in this skill.

`tools/try_forever_owner_surgery_shadow_temporal_receipt_integrity.py` is supporting source. Before a **completed comparison state** (`SHADOW_MATCH` or `SHADOW_DIVERGED`) can enter the existing temporal-binding policy it requires the shadow receipt to carry:
- exact canonical custody schema v10;
- the exact canonical `evidenceComplete` boolean;
- canonical authority backend `PORTABLE_PATHNAME_REVALIDATION`;
- descriptor capability `SUPPORTED_POSIX_PRIMITIVES`.

Only `SHADOW_MATCH` can later earn temporal proof. `SHADOW_DIVERGED` remains temporally unbound, but it still must prove the descriptor comparison context it claims actually existed. Wound/unavailable states remain non-comparison states.

The helper delegates actual temporal proof to `try_forever_owner_surgery_shadow_temporal_binding.py`; it never grants authority.

## Regression source
`tools/test_try_forever_owner_surgery_shadow_receipt_comparison_semantics.py` is **SOURCE / UNEXECUTED**. It pins completed divergence versus unavailable comparison, including rejection of the current legacy `DESCRIPTOR_WOUND -> false/false/false` shape.

`tools/test_try_forever_owner_surgery_shadow_temporal_receipt_integrity.py` is **SOURCE / UNEXECUTED**. It pins counterfeit schema/completeness/backend/capability context for completed comparison states and a valid same-observation temporal-binding path.

`tools/test_try_forever_owner_surgery_descriptor_shadow_wound_owner_boundary.py` is an intentionally **RED OWNER-BOUNDARY REGRESSION / UNEXECUTED**. It requires the descriptor-shadow owner itself to report null comparisons when held-directory custody fails before comparison.

Do not call any regression passed until an authorized execution lane produces a receipt.

## Current capability truth
- receipt comparison tri-state policy: **SOURCE_WIRED**;
- temporal receipt-context integrity helper: **SUPPORTING SOURCE**;
- descriptor-shadow v3 upstream wound semantics corrected: **NO / RED**;
- temporal owner composition consumes strict helper: **NO**;
- regressions executed: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / touch
Operator-facing receipts must not describe a failed comparison as a negative measurement. If comparison did not complete, expose the wound/status and leave comparison fields unavailable. This prevents TalkBack or visible operator surfaces from saying “different” when the system only knows “could not compare.”

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.

## Duplicate-architecture law
Do not create a second descriptor authority or temporal-binding owner. Strengthen the existing receipt projection and compose existing shadow/temporal organs.
