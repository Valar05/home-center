# Operator Owner Surgery Temporal Content Binding

## Purpose
Bind descriptor-shadow content comparison to the **same artifact bytes that produced the canonical custody result**, without creating another promotion authority or accepting caller-owned split-view evidence.

## Core laws
`CANONICAL RESULT SHA != CANONICAL ARTIFACT CONTENT WITNESS`.

`LATER PORTABLE BYTES == LATER DESCRIPTOR BYTES` does **not** imply `THOSE BYTES PRODUCED CANONICAL RESULT`.

`TEMPORAL CONTENT BINDING REQUIRES NONEMPTY SAME-OBSERVATION CANONICAL WITNESSES`.

`EMPTY CANONICAL ARTIFACT SET != PROVEN TEMPORAL CONTENT BINDING`.

`CANONICAL RESULT ID MISMATCH => TEMPORAL BINDING NO`.

`ARBITRARY PYTHON MAPPING != ONE TEMPORAL EVIDENCE OBSERVATION`.

`TEMPORAL RECEIPT CONTEXT MUST SNAPSHOT BEFORE SEMANTIC READS`.

`TEMPORAL CONTENT BOUND != PROMOTION AUTHORITY != FILESYSTEM ATOMICITY != TESTED != RUNTIME`.

## Source wiring
The existing canonical v10 custody owner retains `artifact_byte_count` and `artifact_sha256` on each admitted `Surgery` from the same bounded artifact observation used for semantic admission, and emits `artifactContentWitnesses` from those retained identities.

The existing descriptor shadow consumes `evaluate_temporal_content_binding_with_receipt_integrity(...)` after its normal path/metric/content comparison and reports `temporalContentBinding` plus `temporalBindingProven` without granting descriptor authority or owner mutation.

`tools/try_forever_owner_surgery_shadow_temporal_binding.py` remains the evidence policy. It now advertises exact built-in `dict` canonical/shadow evidence and snapshots both caller-owned inputs through the existing bounded exact-JSON snapshot organ **before** schema, canonical-result identity, witness, status, comparison, or artifact reads. After that custody gate it requires exact canonical v10 + descriptor-shadow v3, exact canonical-result identity, complete canonical custody, an exact positive shadow comparison, a nonempty canonical Surgery/witness set, and exact canonical/portable/descriptor content identity.

`tools/try_forever_owner_surgery_shadow_temporal_receipt_integrity.py` remains the receipt-context gate already consumed by descriptor-shadow owner flow. It now exposes the same exact built-in-dict public contract and snapshots both caller-owned inputs before canonical schema/completeness/backend/status/capability reads. It delegates only after that context custody succeeds. Re-snapshotting the already-detached plain dict inside the underlying temporal policy is bounded defensive composition, not a second temporal owner.

## Regression source
- `tools/test_try_forever_owner_surgery_shadow_temporal_binding.py`: **SOURCE / UNEXECUTED**; includes missing/malformed witness, result mismatch, empty-set fail-closed, exact binding, and divergence cases.
- `tools/test_try_forever_owner_surgery_temporal_binding_owner_boundary.py`: **SOURCE-WIRING / UNEXECUTED**; requires the canonical witness fields/surface and descriptor-shadow policy consumption.
- `tools/test_try_forever_owner_surgery_same_observation_witness.py`: **SOURCE / UNEXECUTED**; pins emitted canonical witness byte count/SHA to one exact admitted artifact payload.
- `tools/test_try_forever_operator_receipt_exact_container_surfaces.py`: **CONVERGENCE SOURCE / UNEXECUTED**; now attacks arbitrary root `Mapping`, nested dict-subclass callbacks, and public type drift on both temporal entrypoints.

## Existing-owner rule
Do not create a second custody owner, temporal validator, or descriptor-audit controller. This contract composes the existing canonical v10 owner, existing descriptor shadow, existing temporal policies, and the existing snapshot-custody organ. Do not perform a third artifact read and call it canonical evidence. Do not call a regression passed because its source exists.

## Capability membrane
- canonical same-observation content witness: **YES / SOURCE_WIRED**;
- descriptor-shadow temporal-policy consumption: **YES / SOURCE_WIRED**;
- temporal binding exact-container custody: **YES / SOURCE_WIRED**;
- temporal receipt-integrity exact-container custody: **YES / SOURCE_WIRED**;
- focused/convergence regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- temporal promotion authority: **NO**;
- filesystem atomicity: **NO**;
- TESTED: **NO**;
- runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

## Review scar
The 2026-08-25 14:03 review found the broader receipt exact-container doctrine had declared whole-stack convergence while these two public temporal surfaces still advertised arbitrary `Mapping` and performed repeated caller-owned semantic reads. The repair reused the already-source-wired bounded snapshot organ at both public temporal boundaries; output schemas and current descriptor-owner plain-dict behavior were intentionally preserved. Source convergence is real; regression execution and TESTED remain separate.

## P0 / phone firewall
This skill owns no phone or P0 capability. Phone Runtime, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, and physical acceptance remain untouched.