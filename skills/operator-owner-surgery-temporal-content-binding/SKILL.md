# Operator Owner Surgery Temporal Content Binding

## Purpose
Bind descriptor-shadow content comparison to the **same artifact bytes that produced the canonical custody result**, and apply the same-observation law to mutable UI source/semantic projections without creating another promotion authority or accepting caller-owned split-view evidence.

## Core laws
`CANONICAL RESULT SHA != CANONICAL ARTIFACT CONTENT WITNESS`.

`LATER PORTABLE BYTES == LATER DESCRIPTOR BYTES` does **not** imply `THOSE BYTES PRODUCED CANONICAL RESULT`.

`TEMPORAL CONTENT BINDING REQUIRES NONEMPTY SAME-OBSERVATION CANONICAL WITNESSES`.

`MUTABLE UI ADMISSION != LATER MATERIALIZATION UNLESS THE OBSERVATION WINDOW IS MUTATION-FREE`.

`CURRENT-STATE POLICY RESULT != CURRENT-STATE SEMANTIC OUTPUT UNLESS BOTH ARE BOUND TO ONE SNAPSHOT`.

`SEMANTIC REFRESH CO-LOCATION != LIFECYCLE CUSTODY`.

`OWNER TOKEN PRESENCE != OWNER ASSIGNMENT ORDERING`.

`PERSISTENT OWNER ASSIGNMENT MUST PRECEDE OWNER REFRESH`.

`MODE MUTATION MUST PRECEDE THE REFRESH THAT CLAIMS TO EXPOSE THAT MODE`.

`LIFECYCLE ORDERING WITNESSES MUST BE OWNER-LOCAL, SINGULAR, AND ORDERED; A MATCH ANYWHERE IN THE METHOD IS NOT CUSTODY`.

`LEXICAL DATA FLOW ALONE != TEMPORAL CUSTODY`.

`EMPTY CANONICAL ARTIFACT SET != PROVEN TEMPORAL CONTENT BINDING`.

`CANONICAL RESULT ID MISMATCH => TEMPORAL BINDING NO`.

`ARBITRARY PYTHON MAPPING != ONE TEMPORAL EVIDENCE OBSERVATION`.

`TEMPORAL RECEIPT CONTEXT MUST SNAPSHOT BEFORE SEMANTIC READS`.

`TEMPORAL CONTENT BOUND != PROMOTION AUTHORITY != FILESYSTEM ATOMICITY != TESTED != RUNTIME`.

## Source wiring
The existing canonical v10 custody owner retains `artifact_byte_count` and `artifact_sha256` on each admitted `Surgery` from the same bounded artifact observation used for semantic admission, and emits `artifactContentWitnesses` from those retained identities.

The existing descriptor shadow consumes `evaluate_temporal_content_binding_with_receipt_integrity(...)` after its normal path/metric/content comparison and reports `temporalContentBinding` plus `temporalBindingProven` without granting descriptor authority or owner mutation.

`tools/try_forever_owner_surgery_shadow_temporal_binding.py` remains the evidence policy. It snapshots caller-owned inputs through the existing bounded exact-JSON snapshot organ **before** schema, canonical-result identity, witness, status, comparison, or artifact reads, then requires exact canonical custody and exact content identity.

The Adam accessibility evidence organ reuses this law without becoming a second temporal owner. For request admission, `CharSequence editable = adamInput.getText()` → canonical fail-closed admission → `editable.toString().trim()` must be an adjacent mutation-free observation window because Android `Editable` is aliased mutable state. For Send action semantics, one `modeSnapshot = adamMode` must immediately feed the policy Decision and that Decision must reach the button action projection without intervening owner-state mutation or arbitrary executable work. Lifecycle topology is a separate required witness: the persistent Send owner assignment must occur before the create-time `refreshAdamSendAction()` call, and the `adamMode` mutation must occur before the mode-change refresh that claims to expose that mode. Merely finding both tokens in the same method is explicitly insufficient. Owner-probe v11 consumes those owner-local ordering witnesses in addition to the v10 same-snapshot data-flow rules. These are **source-evidence constraints only**; they do not execute Android or grant runtime authority.

## Regression source
- `tools/test_try_forever_owner_surgery_shadow_temporal_binding.py`: **SOURCE / UNEXECUTED**; includes missing/malformed witness, result mismatch, empty-set fail-closed, exact binding, and divergence cases.
- `tools/test_try_forever_owner_surgery_temporal_binding_owner_boundary.py`: **SOURCE-WIRING / UNEXECUTED**; requires the canonical witness fields/surface and descriptor-shadow policy consumption.
- `tools/test_try_forever_owner_surgery_same_observation_witness.py`: **SOURCE / UNEXECUTED**; pins emitted canonical witness byte count/SHA to one exact admitted artifact payload.
- `tools/test_try_forever_operator_receipt_exact_container_surfaces.py`: **CONVERGENCE SOURCE / UNEXECUTED**; attacks arbitrary root `Mapping`, nested dict-subclass callbacks, and public type drift on temporal entrypoints.
- `tools/test_try_forever_adam_temporal_custody.py`: **SOURCE CONVERGED v11 / UNEXECUTED**; pins post-admission mutable-Editable work, stale/mutated Send mode state, arbitrary projection work, create-time refresh-before-owner assignment, and mode-refresh-before-mode-mutation counterfeits plus positive counterparts.

## Existing-owner rule
Do not create a second custody owner, temporal validator, descriptor-audit controller, Adam selector, or accessibility controller. Compose the existing canonical custody owner, descriptor shadow, temporal policies, bounded snapshot organ, Adam source probe, and existing native owner proposals. Do not perform a third artifact/source read and call it canonical evidence. Do not call a regression passed because its source exists.

## Capability membrane
- canonical same-observation content witness: **YES / SOURCE_WIRED**;
- descriptor-shadow temporal-policy consumption: **YES / SOURCE_WIRED**;
- temporal binding exact-container custody: **YES / SOURCE_WIRED**;
- temporal receipt-integrity exact-container custody: **YES / SOURCE_WIRED**;
- Adam mutable-request temporal evidence policy: **YES / SOURCE_REPAIRED / UNEXECUTED**;
- Adam current-mode semantic temporal evidence policy: **YES / SOURCE_REPAIRED v11 / UNEXECUTED**;
- Adam lifecycle-ordering evidence witness: **YES / CONSUMED BY OWNER-PROBE v11 / UNEXECUTED**;
- focused/convergence regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- temporal promotion authority: **NO**;
- filesystem atomicity: **NO**;
- TESTED: **NO**;
- runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

## Review scars
The 2026-08-25 14:03 review found the broader receipt exact-container doctrine had declared whole-stack convergence while two public temporal surfaces still advertised arbitrary `Mapping` and performed repeated caller-owned semantic reads. The repair reused the already-source-wired bounded snapshot organ at both public temporal boundaries; output schemas and current descriptor-owner plain-dict behavior were intentionally preserved.

The 2026-08-28 Harroway review found the same category of split-view evidence in mutable UI state: Adam request admission could classify one aliased `Editable` observation and materialize a later mutated value, while Send action evidence could derive a Decision from one mode state and publish it after mode drift. Owner-probe v10 closed those source-evidence holes by demanding mutation-free same-observation windows. This improves evidence custody only; native owner surgery, regression execution, TESTED, runtime, phone delivery, and acceptance remain separate.

The 2026-08-28 follow-up review found v10 still treated lifecycle **co-location** as lifecycle **ordering**: `createOverlay()` could mention the Send owner and refresh in the wrong order, while the mode path could refresh stale semantics before mutating `adamMode`. The existing temporal fixture pinned both shapes as RED source. Owner-probe v11 now consumes the missing witnesses exactly: one owner-local persistent Send assignment precedes the create-time refresh, and one owner-local mode mutation precedes the mode-change refresh. The fixture and broad owner fixture are converged to v11 source, but remain unexecuted; this is an evidence repair, not native-owner/runtime capability.

## P0 / phone firewall
This skill owns no phone or P0 capability. Phone Runtime, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, and physical acceptance remain untouched.
