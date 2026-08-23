# Operator Owner Surgery Temporal Content Binding

## Purpose
Bind descriptor-shadow content comparison to the **same artifact bytes that produced the canonical custody result**, without creating another promotion authority.

## Core laws
`CANONICAL RESULT SHA != CANONICAL ARTIFACT CONTENT WITNESS`.

`LATER PORTABLE BYTES == LATER DESCRIPTOR BYTES` does **not** imply `THOSE BYTES PRODUCED CANONICAL RESULT`.

`TEMPORAL CONTENT BINDING REQUIRES NONEMPTY SAME-OBSERVATION CANONICAL WITNESSES`.

`EMPTY CANONICAL ARTIFACT SET != PROVEN TEMPORAL CONTENT BINDING`.

`CANONICAL RESULT ID MISMATCH => TEMPORAL BINDING NO`.

`TEMPORAL CONTENT BOUND != PROMOTION AUTHORITY != FILESYSTEM ATOMICITY != TESTED != RUNTIME`.

## Source wiring
The existing canonical v10 custody owner now retains `artifact_byte_count` and `artifact_sha256` on each admitted `Surgery` from the same bounded artifact observation used for semantic admission, and emits `artifactContentWitnesses` from those retained identities.

The existing descriptor shadow now consumes `evaluate_temporal_content_binding(...)` after its normal path/metric/content comparison and reports `temporalContentBinding` plus `temporalBindingProven` without granting descriptor authority or owner mutation.

`tools/try_forever_owner_surgery_shadow_temporal_binding.py` remains the evidence policy. It requires exact canonical v10 + descriptor-shadow v3, exact canonical-result identity, complete canonical custody, an exact positive shadow comparison, a nonempty canonical Surgery/witness set, and exact canonical/portable/descriptor content identity.

## Regression source
- `tools/test_try_forever_owner_surgery_shadow_temporal_binding.py`: **SOURCE / UNEXECUTED**; includes missing/malformed witness, result mismatch, empty-set fail-closed, exact binding, and divergence cases.
- `tools/test_try_forever_owner_surgery_temporal_binding_owner_boundary.py`: **SOURCE-WIRING / UNEXECUTED**; requires the canonical witness fields/surface and descriptor-shadow policy consumption.
- `tools/test_try_forever_owner_surgery_same_observation_witness.py`: **SOURCE / UNEXECUTED**; pins emitted canonical witness byte count/SHA to one exact admitted artifact payload.

## Existing-owner rule
Do not create a second custody owner or descriptor-audit controller. This contract composes the existing canonical v10 owner, existing descriptor shadow, and existing temporal policy. Do not perform a third read and call it canonical evidence.

## Capability membrane
- canonical same-observation content witness: **YES / SOURCE_WIRED**;
- descriptor-shadow temporal-policy consumption: **YES / SOURCE_WIRED**;
- temporal evidence policy: **YES / SOURCE**;
- focused regression source: **YES / UNEXECUTED**;
- temporal promotion authority: **NO**;
- filesystem atomicity: **NO**;
- TESTED: **NO**;
- runtime/deployed/delivered/accepted: **NO**.
