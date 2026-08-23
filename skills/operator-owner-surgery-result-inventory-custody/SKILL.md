# Operator Owner Surgery Result Inventory Custody

## Purpose
Prevent a future owner-surgery backend/result adapter from inventing authority by dropping canonical schema custody, by emitting promotion-group members that are not exact members of the admitted `surgeries` inventory, or by carrying an `artifactContentWitnesses` surface that disagrees with the exact Surgery content evidence it supposedly witnesses.

This skill owns a **supporting evidence gate only**. It does not replace canonical v10, `admit_selected_backend_result(...)`, the descriptor backend, the overlay owner, deployment, or acceptance.

## Core laws
`BACKEND RESULT WITHOUT EXACT CANONICAL SCHEMA != AUTHORITY INPUT`.

`GROUP MEMBER != PROMOTION EVIDENCE UNLESS IT EXISTS EXACTLY IN surgeries`.

`EXACT SURGERY MEMBERSHIP INCLUDES SAME-OBSERVATION artifact_byte_count + artifact_sha256`.

`artifactContentWitnesses MUST EQUAL THE CANONICAL surgeries PATH + BYTE COUNT + SHA-256 SET`.

`SAME METADATA + DIFFERENT CONTENT EVIDENCE != EXACT SURGERY MEMBER`.

`WITNESS AGREEMENT LATER IN DESCRIPTOR SHADOW != PERMISSION TO ADMIT A CONTRADICTORY CANONICAL RESULT EARLIER`.

`SAME PATH + DIFFERENT ARTIFACT KIND != TWO SURGERIES`.

`artifact_kind MUST AGREE WITH .patch / .delta.json PATH IDENTITY`.

`promotion_candidate MUST AGREE WITH EXACT ADMITTED STATE`.

`INVENTORY CUSTODY != WITNESS PARITY != AUTHORITY ADMISSION != TESTED != RUNTIME != DELIVERED`.

## Supporting source
`tools/try_forever_owner_surgery_backend_result_integrity.py` is the existing source-only inventory/group integrity gate.

It requires:
- exact schema `try-forever-owner-surgery-custody.v10`;
- list-shaped `surgeries`;
- unique surgery path identity;
- exact patch/delta path-kind agreement;
- admitted owner/base/state/promotion evidence;
- canonical non-negative artifact byte count and lowercase SHA-256 content evidence; and
- every collision/stale/unverified promotion member to exist exactly in the surgeries inventory, including content evidence.

`tools/try_forever_owner_surgery_witness_parity.py` is a new supporting source-only parity gate. It deliberately reuses the existing inventory audit, then requires:
- one list-shaped `artifactContentWitnesses` surface;
- unique witness path identity;
- exact path-set equality with canonical `surgeries`;
- non-negative `byteCount` and lowercase SHA-256; and
- exact per-path byte-count/SHA-256 equality with each Surgery's same-observation content evidence.

The separate descriptor-shadow temporal policy may validate the same canonical witness set later in the evidence timeline, but that later agreement does not repair a canonical result that crossed an earlier backend admission boundary with contradictory witnesses.

## Regression surfaces
`tools/test_try_forever_owner_surgery_backend_result_integrity.py` pins schema drift, missing inventory, duplicate paths, kind/path mismatch, state/promotion contradictions, missing/malformed content evidence, phantom members, changed-state aliases, changed-content aliases, malformed members, and diagnostic non-promotion records.

`tools/test_try_forever_owner_surgery_witness_parity.py` pins missing/phantom/duplicate witnesses plus byte-count, SHA-256, and malformed-content drift.

`tools/test_try_forever_owner_surgery_current_witness_inventory.py` is the repository-level v10 witness-parity fixture.

`tools/test_try_forever_owner_surgery_backend_witness_owner_boundary.py` is intentionally **RED** against the current branch: the existing `admit_backend_result_with_inventory_custody(...)` wrapper does not yet call the witness-parity gate before delegating to authority admission.

Regression execution = **NO**. TESTED = **NO**.

## Current capability state
- canonical v10 same-observation Surgery content evidence: **YES / SOURCE_WIRED**;
- canonical v10 `artifactContentWitnesses`: **YES / SOURCE_WIRED**;
- supporting inventory/group integrity implementation: **YES / SOURCE**;
- supporting canonical witness-parity implementation: **YES / SOURCE**;
- authenticated repository readback: **YES**;
- hostile regression source: **YES / UNEXECUTED**;
- current-inventory witness regression source: **YES / UNEXECUTED**;
- existing backend result-integrity/admission wrapper consumes witness parity: **NO / RED OWNER BOUNDARY**;
- canonical descriptor owner integration: **NO**;
- TESTED/runtime/deployed/delivered/accepted: **NO**.

## Duplicate-architecture law
Do not create Backend Admission II. The next safe source promotion is to make the **existing** `admit_backend_result_with_inventory_custody(...)` call the witness-parity gate before it delegates to `admit_selected_backend_result(...)`, or fold the same invariant directly into that existing gate. Canonical v10 remains the sole custody authority producer.
