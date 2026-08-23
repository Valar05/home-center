# Operator Owner Surgery Shadow Receipt Integrity

## Purpose
Keep descriptor-shadow operator receipts honest without creating a second custody authority or a second receipt projector.

The raw descriptor-shadow result remains machine evidence. The operator receipt path must consume the existing self-integrity gate before the existing bounded display projector is allowed to speak.

## Core laws
`FALSE COMPARISON = COMPLETED DIVERGENCE`.

`NULL COMPARISON = COMPARISON NOT COMPLETED`.

`WOUND / UNAVAILABLE STATE != SHADOW_DIVERGED`.

`SHADOW_MATCH = RECOMPUTED PATH SET + RECOMPUTED WORK METRICS + RECOMPUTED EXACT CONTENT IDENTITY`.

`METRICS MATCH != AUDITABLE METRICS WITHOUT THE EXACT COMPARED COUNTS`.

`COMPLETED OPERATOR RECEIPT EXPOSES CANONICAL + DESCRIPTOR DIRECTORY-ENTRY / CANDIDATE COUNTS`.

`CANDIDATE COUNT <= DIRECTORY-ENTRY COUNT`.

`COMPLETED PORTABLE ARTIFACT COUNT = CANONICAL CANDIDATE COUNT`.

`COMPLETED DESCRIPTOR ARTIFACT COUNT = DESCRIPTOR CANDIDATE COUNT`.

`EQUAL IMPOSSIBLE COUNTERS != VALID METRIC EVIDENCE`.

`CANONICAL RESULT SHA MATCH != SHADOW RECEIPT CONTEXT ADMITTED`.

`COMPLETED SHADOW CONTEXT = EXACT CANONICAL V10 + evidenceComplete=true + PORTABLE_PATHNAME_REVALIDATION + SUPPORTED_POSIX_PRIMITIVES`.

`SHADOW_MATCH != TEMPORAL_CONTENT_BOUND`.

`WOUND RECEIPT MUST NOT RETAIN STALE TEMPORAL PROOF`.

`RAW MACHINE EVIDENCE != OPERATOR RECEIPT`.

`OPERATOR RECEIPT SHA = DETERMINISTIC BOUNDED OPERATOR-PAYLOAD IDENTITY`.

`OPERATOR RECEIPT SHA != CANONICAL ARTIFACT IDENTITY != PROMOTION AUTHORITY != TESTED != RUNTIME IDENTITY != FILESYSTEM ATOMICITY`.

`OPERATOR RECEIPT COMMAND != SECOND RECEIPT PROJECTOR != SECOND DESCRIPTOR AUTHORITY`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Existing organs
`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw non-authoritative descriptor-shadow evidence producer.

`tools/try_forever_owner_surgery_shadow_temporal_receipt_integrity.py` remains the strict temporal receipt-context gate already consumed by completed shadow comparisons.

`tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector. It owns path privacy, boundary-digest projection, comparison true/false/null display semantics, and now exposes the exact bounded work counters for completed comparisons while verifying the `metricsMatch` claim against those counters.

`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the self-audit gate. It recomputes completed comparison truth from raw artifact lists/counters, validates exact completed-comparison and temporal receipt context, preserves legitimate wound contact, and delegates display to the existing projector.

## Operator receipt owner command
`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains **SOURCE_WIRED** as the bounded operator command surface.

It composes the existing organs in one direction:

`raw descriptor shadow -> receipt self-integrity -> existing bounded display projector -> operator receipt`.

The complete bounded operator payload receives deterministic `operatorReceiptSha256` identity after projection. The digest excludes itself, is stable for identical bounded payloads, and changes when material receipt evidence changes. It is an operator-receipt checkpoint only; it grants no authority, execution, testing, runtime, deployment, delivery, or acceptance.

The command does not reinterpret or mutate the raw result, does not emit promotion authority, and does not create a second projector, backend, controller, or descriptor authority. The raw audit remains separately callable for machine evidence.

## Regression source
`tools/test_try_forever_owner_surgery_shadow_receipt_projection.py` remains **SOURCE / UNEXECUTED**.

`tools/test_try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains **SOURCE / UNEXECUTED** and attacks lying comparison booleans, impossible counters, cardinality drift, counterfeit context, stale temporal proof, and legitimate wound preservation.

`tools/test_try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains **SOURCE / UNEXECUTED**. It now pins actual operator-command consumption of self-integrity, exact completed work-metric visibility, deterministic bounded receipt identity, receipt-identity change under material evidence change, raw-boundary non-leakage, no authority/runtime promotion, rejection of contradictory raw evidence, and rejection of stale temporal proof on wounds.

Do not call any regression passed merely because source exists.

## Current capability truth
- descriptor-shadow comparison tri-state owner: **YES / SOURCE_WIRED**;
- temporal receipt-context owner: **YES / SOURCE_WIRED**;
- receipt self-integrity gate: **YES / SUPPORTING SOURCE**;
- completed comparison work metrics visible/audited: **YES / SOURCE_WIRED**;
- operator receipt command consumes self-integrity: **YES / SOURCE_WIRED**;
- deterministic bounded operator receipt identity: **YES / SOURCE_WIRED**;
- sole display projector: **YES / SOURCE**;
- hostile regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED: **NO**;
- Android/TalkBack runtime consumption: **NO**;
- canonical descriptor authority/backend integration: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / touch
Operator display must expose failed comparison as unavailable rather than counterfeit negative measurement, never echo raw failure prose, never let impossible work counters or incomplete artifact lists manufacture MATCH, never leave a completed `metricsMatch` claim without its exact bounded compared counts, and never retain temporal proof on a wound.

The operator receipt command is a source delivery surface only. Its fingerprint is source evidence identity for the bounded receipt, not Android/TalkBack runtime proof.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.

## Duplicate-architecture law
Do not create a second descriptor authority, temporal-binding owner, receipt projector, overlay controller, or recovery organ. Strengthen the existing chain by composition.
