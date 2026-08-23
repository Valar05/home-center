# Operator Owner Surgery Shadow Receipt Integrity

## Purpose
Keep descriptor-shadow evidence honest at the operator/temporal-binding boundary without creating a second custody authority or receipt projector.

This skill owns four distinctions:

1. **comparison false != comparison unavailable**;
2. **matching canonical-result SHA != complete shadow receipt context**;
3. **claimed comparison booleans != recomputed artifact/metric evidence**;
4. **SHADOW_MATCH != temporal content binding**.

It does not own patch promotion, canonical v10 custody, descriptor backend selection, Android runtime, phone/P0 execution, deployment, delivery, or acceptance.

## Core laws
`FALSE COMPARISON = COMPLETED DIVERGENCE`.

`NULL COMPARISON = COMPARISON NOT COMPLETED`.

`WOUND / UNAVAILABLE STATE != SHADOW_DIVERGED`.

`SHADOW_DIVERGED REQUIRES THREE COMPLETED BOOLEAN COMPARISONS + AT LEAST ONE FALSE`.

`SHADOW MATCH REQUIRES THREE TRUE COMPARISONS`.

`CLAIMED MATCH != RECOMPUTED ARTIFACT / METRIC MATCH`.

`CANONICAL RESULT SHA MATCH != SHADOW RECEIPT CONTEXT ADMITTED`.

`COMPLETED SHADOW COMPARISON CONTEXT = EXACT CANONICAL V10 SCHEMA + EXACT EVIDENCE-COMPLETE BOOLEAN + CANONICAL PORTABLE AUTHORITY BACKEND + EXACT SUPPORTED DESCRIPTOR CAPABILITY`.

`SHADOW_MATCH != TEMPORAL_CONTENT_BOUND`.

`TEMPORAL BINDING TRUE REQUIRES TEMPORAL_CONTENT_BOUND + STRICT RECEIPT-INTEGRITY CONTEXT`.

`SHADOW RECEIPT INTEGRITY != TEMPORAL BINDING != PROMOTION AUTHORITY`.

`SUPPORTING SOURCE != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Source organs
`tools/try_forever_owner_surgery_shadow_receipt_projection.py` is the existing operator-facing display projector. It requires:
- `SHADOW_MATCH` => `(True, True, True)`;
- `SHADOW_DIVERGED` => three non-null booleans with at least one `False`;
- wound/unavailable comparison states => `(None, None, None)` because comparison did not complete.

The upstream descriptor-shadow v3 owner now follows that tri-state contract: descriptor custody failure before comparison emits `null/null/null`. Historical doctrine claiming this remained RED is stale and must not be reused.

`tools/try_forever_owner_surgery_shadow_temporal_receipt_integrity.py` is the strict temporal receipt-context gate already consumed by the descriptor-shadow owner after completed comparison. It requires exact canonical v10 schema/completeness/backend/capability context before delegating to the existing temporal-binding policy. Only `SHADOW_MATCH` can later earn temporal proof.

`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` is new **supporting source**. It does not replace the existing display projector. Before delegating to it, this gate:
- recomputes artifact-set and exact content-identity truth from the raw portable/descriptor artifact evidence;
- recomputes work-metric truth from canonical and descriptor directory/candidate counters;
- rejects completed comparison booleans that contradict those recomputed values;
- requires the exact completed-comparison context already used by the temporal gate;
- requires the nested temporal receipt to carry exact receipt-integrity schema, exact canonical result identity, no authority/owner/test promotion, and proof-status consistency;
- rejects stale temporal evidence on wound/unavailable states.

Its returned operator receipt adds only bounded semantic fields: self-integrity schema, whether comparison evidence was recomputed, temporal status, temporal proof boolean, and temporal receipt-context admission. Raw failure prose remains outside routine display.

## Regression source
`tools/test_try_forever_owner_surgery_shadow_receipt_projection.py` is **SOURCE / UNEXECUTED**. Its stale wound fixture was repaired: wound/unavailable comparison fields are null, not false. Its SHADOW_DIVERGED error expectation now matches the current projector contract.

`tools/test_try_forever_owner_surgery_shadow_receipt_self_integrity.py` is **SOURCE / UNEXECUTED**. It attacks lying path/content/metric booleans, counterfeit completed-comparison context, temporal receipt-integrity mismatch, proof/status disagreement, valid divergence, and stale temporal evidence on wounds.

`tools/test_try_forever_owner_surgery_shadow_receipt_comparison_semantics.py`, `tools/test_try_forever_owner_surgery_shadow_temporal_receipt_integrity.py`, and the descriptor-shadow owner boundary regressions remain source-only until an authorized execution receipt exists.

Do not call any regression passed merely because source exists.

## Current capability truth
- descriptor-shadow comparison tri-state owner wiring: **YES / SOURCE_WIRED**;
- temporal receipt-context owner composition: **YES / SOURCE_WIRED**;
- operator display projector: **YES / SOURCE**;
- receipt self-integrity gate: **YES / SUPPORTING SOURCE**;
- hostile regression source: **YES / UNEXECUTED**;
- Android/TalkBack runtime consumption of these operator receipts: **NO**;
- canonical descriptor authority/backend integration: **NO**;
- TESTED: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / touch
Operator-facing receipts must not describe a failed comparison as a negative measurement. If comparison did not complete, expose the wound/status and leave comparison fields unavailable. A visible receipt must also not repeat a raw SHADOW_MATCH claim when its own artifact lists, work counters, or temporal receipt contradict it.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.

## Duplicate-architecture law
Do not create a second descriptor authority, temporal-binding owner, or receipt projector. Strengthen the existing receipt projection by composing supporting integrity gates around the existing shadow/temporal organs.
