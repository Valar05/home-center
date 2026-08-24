# Operator Owner Surgery Shadow Receipt Integrity

## Purpose
Keep descriptor-shadow operator receipts honest without creating a second custody authority or a second receipt projector.

The raw descriptor-shadow result remains machine evidence. The operator receipt path must consume the existing self-integrity gate before the existing bounded display projector is allowed to speak.

## Core laws
`FALSE COMPARISON = COMPLETED DIVERGENCE`.

`NULL COMPARISON = COMPARISON NOT COMPLETED`.

`WOUND / UNAVAILABLE STATE != SHADOW_DIVERGED`.

`WOUND LABEL != VALID WOUND WITHOUT MATCHING CANONICAL / CAPABILITY CONTEXT`.

`CANONICAL_SCHEMA_WOUND = NON-V10 CANONICAL SCHEMA + NO COMPLETENESS/CAPABILITY ADMISSION`.

`CANONICAL_WOUND = V10 + evidenceComplete=false + NO DESCRIPTOR CAPABILITY ADMISSION`.

`DESCRIPTOR_UNAVAILABLE = V10 + evidenceComplete=true + EXACT PORTABLE-UNAVAILABLE CAPABILITY`.

`PORTABLE_SHADOW_WOUND / DESCRIPTOR_WOUND = V10 + evidenceComplete=true + SUPPORTED DESCRIPTOR CAPABILITY`.

`SHADOW_MATCH = RECOMPUTED PATH SET + RECOMPUTED WORK METRICS + RECOMPUTED EXACT CONTENT IDENTITY`.

`METRICS MATCH != AUDITABLE METRICS WITHOUT THE EXACT COMPARED COUNTS`.

`COMPLETED OPERATOR RECEIPT EXPOSES CANONICAL + DESCRIPTOR DIRECTORY-ENTRY / CANDIDATE COUNTS`.

`CANDIDATE COUNT <= DIRECTORY-ENTRY COUNT`.

`COMPLETED PORTABLE ARTIFACT COUNT = CANONICAL CANDIDATE COUNT`.

`COMPLETED DESCRIPTOR ARTIFACT COUNT = DESCRIPTOR CANDIDATE COUNT`.

`EQUAL IMPOSSIBLE COUNTERS != VALID METRIC EVIDENCE`.

`CANONICAL RESULT SHA = EXACT 64-CHARACTER LOWERCASE HEXADECIMAL SHA-256 IDENTITY`.

`REPEATING THE SAME MALFORMED CANONICAL RESULT ID IN NESTED RECEIPTS != IDENTITY ADMISSION`.

`CANONICAL RESULT SHA MATCH != SHADOW RECEIPT CONTEXT ADMITTED`.

`COMPLETED SHADOW CONTEXT = EXACT CANONICAL V10 + evidenceComplete=true + PORTABLE_PATHNAME_REVALIDATION + SUPPORTED_POSIX_PRIMITIVES`.

`SHADOW_MATCH != TEMPORAL_CONTENT_BOUND`.

`WOUND RECEIPT MUST NOT RETAIN STALE TEMPORAL PROOF`.

`RAW MACHINE EVIDENCE != OPERATOR RECEIPT`.

`RAW MACHINE EVIDENCE SHA = EXACT RAW-SHADOW PAYLOAD LINKAGE WITHOUT RAW PAYLOAD DISCLOSURE`.

`RAW MACHINE EVIDENCE SHA != CANONICAL ARTIFACT IDENTITY != AUTHORITY != TESTED != RUNTIME`.

`OPERATOR RECEIPT SHA = DETERMINISTIC BOUNDED OPERATOR-PAYLOAD IDENTITY`.

`OPERATOR RECEIPT SHA != CANONICAL ARTIFACT IDENTITY != PROMOTION AUTHORITY != TESTED != RUNTIME IDENTITY != FILESYSTEM ATOMICITY`.

`OPERATOR RECEIPT COMMAND != SECOND RECEIPT PROJECTOR != SECOND DESCRIPTOR AUTHORITY`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Existing organs
`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw non-authoritative descriptor-shadow evidence producer.

`tools/try_forever_owner_surgery_shadow_temporal_receipt_integrity.py` remains the strict temporal receipt-context gate already consumed by completed shadow comparisons.

`tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector. It owns path privacy, boundary-digest projection, comparison true/false/null display semantics, and exposes the exact bounded work counters for completed comparisons while verifying the `metricsMatch` claim against those counters.

`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` is self-integrity schema v2. It recomputes completed comparison truth from raw artifact lists/counters, validates exact completed-comparison and temporal receipt context, validates the canonical result identity itself before accepting nested equality, validates wound/unavailable status against the canonical/capability context that can actually produce it, preserves legitimate wound contact, and delegates display to the existing projector.

## Operator receipt owner command
`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains **SOURCE_WIRED** as the bounded operator command surface and is operator receipt schema v3.

It composes the existing organs in one direction:

`raw descriptor shadow -> raw evidence SHA binding -> receipt self-integrity -> existing bounded display projector -> operator receipt`.

The raw audit remains separately callable for machine evidence. The operator receipt carries `rawMachineEvidenceSha256` so the bounded receipt is cryptographically linked to the exact deterministic raw shadow payload without embedding raw machine evidence or raw boundary prose. The complete bounded operator payload then receives deterministic `operatorReceiptSha256` identity after projection. Both digests are evidence/checkpoint identity only; neither grants authority, execution, testing, runtime, deployment, delivery, acceptance, or filesystem atomicity.

The command does not reinterpret or mutate the raw result, does not emit promotion authority, and does not create a second projector, backend, controller, or descriptor authority.

## Regression source
`tools/test_try_forever_owner_surgery_shadow_receipt_projection.py` remains **SOURCE / UNEXECUTED**.

`tools/test_try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains **SOURCE / UNEXECUTED** and attacks lying comparison booleans, impossible counters, cardinality drift, counterfeit completed context, counterfeit wound/capability context, stale temporal proof, and legitimate wound preservation.

`tools/test_try_forever_shadow_canonical_result_identity.py` is **SOURCE / UNEXECUTED** and attacks missing, non-string, short, long, uppercase, leading-space, and trailing-space canonical result identities while repeating each counterfeit through the nested temporal receipt to prove equality alone cannot admit malformed identity.

`tools/test_try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains **SOURCE / UNEXECUTED**. It pins actual operator-command consumption of self-integrity, exact completed work-metric visibility, raw-evidence SHA linkage, raw-only machine-evidence drift changing receipt identity without raw disclosure, deterministic bounded operator receipt identity, raw-boundary non-leakage, no authority/runtime promotion, rejection of contradictory raw evidence, and rejection of stale temporal proof on wounds.

Do not call any regression passed merely because source exists.

## Current capability truth
- descriptor-shadow comparison tri-state owner: **YES / SOURCE_WIRED**;
- temporal receipt-context owner: **YES / SOURCE_WIRED**;
- receipt self-integrity gate v2: **YES / SOURCE_WIRED**;
- canonical result SHA exact-identity admission: **YES / SOURCE_WIRED**;
- wound-context integrity: **YES / SOURCE_WIRED**;
- completed comparison work metrics visible/audited: **YES / SOURCE_WIRED**;
- operator receipt command consumes self-integrity: **YES / SOURCE_WIRED**;
- raw machine-evidence SHA binding: **YES / SOURCE_WIRED**;
- deterministic bounded operator receipt identity: **YES / SOURCE_WIRED**;
- sole display projector: **YES / SOURCE**;
- hostile regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED: **NO**;
- Android/TalkBack runtime consumption: **NO**;
- canonical descriptor authority/backend integration: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / touch
Operator display must expose failed comparison as unavailable rather than counterfeit negative measurement, never echo raw failure prose, never let impossible work counters or incomplete artifact lists manufacture MATCH, never leave a completed `metricsMatch` claim without its exact bounded compared counts, never accept a malformed canonical result identity merely because nested receipts repeat it, never accept a wound label paired with unrelated healthy context, and never retain temporal proof on a wound.

The operator receipt command is a source delivery surface only. Its raw-evidence fingerprint binds exact machine evidence without speaking it; its operator fingerprint identifies the bounded receipt. Neither is Android/TalkBack runtime proof.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.

## Duplicate-architecture law
Do not create a second descriptor authority, temporal-binding owner, receipt projector, overlay controller, or recovery organ. Strengthen the existing chain by composition.
