# Operator Owner Surgery Result Inventory Custody

## Purpose
Prevent an owner-surgery backend/result adapter from inventing authority by dropping canonical schema custody, by emitting promotion-group members that are not exact members of the admitted `surgeries` inventory, or by carrying an `artifactContentWitnesses` surface that disagrees with the exact Surgery content evidence it supposedly witnesses.

This skill governs an **existing backend-result integrity boundary**. It does not replace canonical v10, `admit_selected_backend_result(...)`, the descriptor backend, the overlay owner, deployment, or acceptance.

## Core laws
`BACKEND RESULT WITHOUT EXACT CANONICAL SCHEMA != AUTHORITY INPUT`.

`GROUP MEMBER != PROMOTION EVIDENCE UNLESS IT EXISTS EXACTLY IN surgeries`.

`EXACT SURGERY MEMBERSHIP INCLUDES SAME-OBSERVATION artifact_byte_count + artifact_sha256`.

`artifactContentWitnesses MUST EQUAL THE CANONICAL surgeries PATH + BYTE COUNT + SHA-256 SET BEFORE AUTHORITY ADMISSION`.

`SAME METADATA + DIFFERENT CONTENT EVIDENCE != EXACT SURGERY MEMBER`.

`WITNESS AGREEMENT LATER IN DESCRIPTOR SHADOW != PERMISSION TO ADMIT A CONTRADICTORY CANONICAL RESULT EARLIER`.

`SAME PATH + DIFFERENT ARTIFACT KIND != TWO SURGERIES`.

`artifact_kind MUST AGREE WITH .patch / .delta.json PATH IDENTITY`.

`promotion_candidate MUST AGREE WITH EXACT ADMITTED STATE`.

`SUPPORTING FACADE TYPE CONTRACT != BROADER Mapping THAN THE REAL OWNER ADMITS`.

`INVENTORY CUSTODY != WITNESS PARITY != AUTHORITY ADMISSION != TESTED != RUNTIME != DELIVERED`.

## Existing owner source
`tools/try_forever_owner_surgery_backend_result_integrity.py` is the existing inventory/group integrity and witness-parity gate consumed before backend authority admission.

It now requires, in one stronger owner path:
- exact schema `try-forever-owner-surgery-custody.v10`;
- list-shaped `surgeries`;
- unique surgery path identity;
- exact patch/delta path-kind agreement;
- admitted owner/base/state/promotion evidence;
- canonical non-negative Surgery artifact byte count and lowercase SHA-256 content evidence;
- every collision/stale/unverified promotion member to exist exactly in the surgeries inventory, including content evidence;
- one list-shaped `artifactContentWitnesses` surface;
- unique witness path identity;
- exact witness path-set equality with canonical `surgeries`; and
- exact per-path `byteCount`/SHA-256 equality with each Surgery's same-observation content evidence.

`admit_backend_result_with_inventory_custody(...)` consumes that stronger audit before it delegates to the unchanged `admit_selected_backend_result(...)` authority policy. Canonical inventory/group custody is audited once; parity does not create Backend Admission II or a second parser/authority owner.

`tools/try_forever_owner_surgery_witness_parity.py` remains a supporting/review facade. It delegates to the existing stronger owner gate, advertises the same exact built-in `dict[str, object]` container contract that the downstream owner actually admits, and preserves focused witness-regression receipt vocabulary; it grants no additional authority. A broader `Mapping` annotation is a capability lie because it promises caller-owned callback surfaces the real owner rejects before semantic reads.

The separate descriptor-shadow temporal policy may validate the same canonical witness set later in the evidence timeline, but that later agreement does not repair a canonical result that crossed an earlier backend admission boundary with contradictory witnesses.

## Regression surfaces
`tools/test_try_forever_owner_surgery_backend_result_integrity.py` pins schema drift, missing inventory, duplicate paths, kind/path mismatch, state/promotion contradictions, missing/malformed content evidence, phantom members, changed-state aliases, changed-content aliases, malformed members, and diagnostic non-promotion records.

`tools/test_try_forever_owner_surgery_witness_parity.py` pins missing/phantom/duplicate witnesses plus byte-count, SHA-256, and malformed-content drift through the supporting facade.

`tools/test_try_forever_owner_surgery_witness_parity_public_contract.py` pins that the supporting facade advertises exact built-in `dict` evidence rather than a broader callback-capable `Mapping` contract.

`tools/test_try_forever_owner_surgery_current_witness_inventory.py` is the repository-level v10 witness-parity fixture.

`tools/test_try_forever_owner_surgery_backend_witness_owner_boundary.py` now pins the **existing owner** directly: valid exact witness parity must admit through the wrapper, while missing/phantom/byte-count/SHA drift must reject before authority admission.

Regression execution = **NO**. TESTED = **NO**.

## Current capability state
- canonical v10 same-observation Surgery content evidence: **YES / SOURCE_WIRED**;
- canonical v10 `artifactContentWitnesses`: **YES / SOURCE_WIRED**;
- existing inventory/group integrity implementation: **YES / SOURCE_WIRED**;
- existing canonical witness-parity implementation: **YES / SOURCE_WIRED**;
- existing backend result-integrity/admission wrapper consumes witness parity: **YES / SOURCE_WIRED**;
- supporting witness-parity review facade: **YES / SOURCE**;
- supporting facade exact built-in-dict public contract: **YES / SOURCE**;
- authenticated repository readback: **YES**;
- hostile regression source: **YES / UNEXECUTED**;
- current-inventory witness regression source: **YES / UNEXECUTED**;
- canonical descriptor owner integration: **NO**;
- TESTED/runtime/deployed/delivered/accepted: **NO**.

## Duplicate-architecture law
Do not create Backend Admission II. The canonical v10 custody producer remains the sole source of canonical Surgery/witness evidence, the existing backend-result integrity wrapper owns pre-admission parity, and `admit_selected_backend_result(...)` remains the authority-admission policy.
