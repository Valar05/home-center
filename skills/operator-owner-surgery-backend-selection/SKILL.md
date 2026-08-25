# Operator Owner Surgery Backend Selection

## Purpose
Select the strongest **admitted** owner-surgery custody backend without silently weakening evidence after a stronger backend has actually been selected by the canonical owner.

This skill owns backend-selection and result-admission doctrine only. It does **not** own a second custody probe, snapshot validator, patch executor, overlay controller, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`PLATFORM CAPABILITY ADMISSION != CANONICAL OWNER INTEGRATION`.

`CAPABILITY MACHINE INPUT != EXTENSIBLE PYTHON CALLBACK SURFACE`.

`DESCRIPTOR BACKEND SELECTED + DESCRIPTOR CUSTODY FAILURE != PERMISSION TO RETRY THROUGH WEAKER PATHNAME CUSTODY`.

`DESCRIPTOR SHADOW AUDIT != DESCRIPTOR BACKEND SELECTED`.

`DESCRIPTOR PRIMITIVES UNAVAILABLE != FAILURE OF PORTABLE v10`.

`STRONGER BACKEND != PERMISSION TO DROP DIRECTORY/CANDIDATE COUNTS, discoveryErrors, currentOwnerBlobs, OR PROMOTION-MEMBER EVIDENCE`.

`INCOMPLETE EXHAUSTIVE CUSTODY + PROMOTION AUTHORITY = INVALID EVIDENCE`.

`OWNER A CUSTODY != OWNER B AUTHORITY`.

`GROUP SHELL != MEMBER AUTHORITY`.

`CALLER MAPPING != DETACHED BACKEND EVIDENCE`.

`DIRECT POLICY MACHINE INPUT != EXTENSIBLE PYTHON CALLBACK SURFACE`.

`PUBLIC TYPE CAPABILITY MUST NOT EXCEED RUNTIME ADMISSION`.

`HELD-DESCRIPTOR BYTES != CANONICAL SURGERY SEMANTICS UNTIL THE EXISTING OWNER PARSES THOSE EXACT BYTES`.

`SUPPORTING SOURCE != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Selection source
`tools/try_forever_owner_surgery_backend_policy.py` is supporting source only.

- `SUPPORTED_POSIX_PRIMITIVES` selects `HELD_DIRECTORY_DESCRIPTOR` for a **future canonical-owner composition**.
- `PORTABLE_ATOMIC_BINDING_UNAVAILABLE` keeps `PORTABLE_PATHNAME_REVALIDATION` as the canonical portable backend.
- Capability tokens are exact built-in strings before equality dispatch; string subclasses are not an admitted control protocol.
- Failure-boundary text is an exact non-empty built-in string before truthiness/projection.
- Selection records are exact `OwnerSurgeryBackendSelection` values whose fields must match the canonical decision for their admitted capability; subclass or forged callback-bearing records fail closed.
- Unknown capability text fails closed.
- Once a canonical classification attempt actually selects held-descriptor custody, descriptor setup/inventory/artifact/cleanup failure terminates that attempt. Do not retry the same evidence through portable custody and call the weaker result equivalent.

### Platform-capability exact-input custody
`tools/try_forever_directory_handle_binding_capability.py` now admits its own public control inputs before equality/truthiness classification:

- `os_name` must be one exact built-in `str`;
- every primitive-presence flag must be one exact built-in `bool`;
- caller-owned `str` subclasses and truthy Python objects are rejected before their `__eq__` / `__bool__` callbacks can participate in capability evidence.

`tools/test_try_forever_directory_handle_binding_capability.py` carries hostile callback fixtures for that boundary. The fixture is **SOURCE / UNEXECUTED**; source wiring is not test execution.

### Direct-policy exact-input custody
The direct result-admission throat now reuses the existing bounded one-observation `snapshot_json_mapping(...)` organ **before any semantic result read**. The public result annotation is `dict[str, object]`, matching runtime exact built-in-dict admission instead of advertising arbitrary `Mapping` capability.

Root and nested Mapping/dict subclasses, scalar subclasses, tuples, non-string keys, non-finite numbers, and other Python-only shapes therefore fail before caller-owned callback behavior can participate in policy evidence. The detached plain tree is the only result object consumed by semantic admission.

`tools/test_try_forever_owner_surgery_backend_policy_exact_input_boundary.py` is **CONVERGENCE SOURCE / UNEXECUTED**. It pins public type convergence, root and nested callback rejection, exact capability/failure strings, exact selection-record custody, ordinary result parity, and ordinary fail-closed projection. Its source presence is not test execution evidence.

## Result-admission throat
`admit_selected_backend_result(...)` is the source-only gate between backend work and owner authority.

After exact machine-input custody it requires:
- selected backend identity and no weaker-fallback claim;
- non-negative integer directory-entry/candidate counts with candidates ≤ entries;
- `discoveryErrors` and `evidenceComplete` to agree;
- lowercase authenticated `currentOwnerBlobs`;
- collision/stale/unverified groups to obey their owner/base/current-owner meanings;
- every promotion member to be canonical Surgery-shaped evidence for the same owner/base and exact promotion-ready state;
- distinct members and distinct owner/base groups so duplicate evidence cannot manufacture cardinality;
- incomplete exhaustive custody to carry **zero** promotion-authority groups.

The gate reports exhaustive evidence separately from owner evidence. A complete scan without authenticated current-owner custody is not owner evidence. Authenticated custody for one owner does not upgrade another owner's unverified group.

Diagnostic surgeries may remain after a wounded scan. Diagnostic source inspection is not promotion authority.

## Backend-result integrity composition
`tools/try_forever_owner_surgery_backend_result_integrity.py` crosses the same existing bounded one-observation exact-JSON snapshot organ at every public result entrypoint **before any semantic result read**.

That source-level composition requires:
- one exact built-in `dict` root;
- recursively exact JSON containers/scalars under the existing snapshot budgets;
- caller-owned mapping/scalar subclasses rejected before their callbacks can execute;
- all inventory and witness checks to run only against the detached plain tree;
- the existing backend result-admission policy to receive that detached tree, not the caller-owned object.

This is reuse of `try_forever_operator_receipt_snapshot_custody.py`, not a new validator owner. The integrity wrapper remains a useful separate composition because it owns witness/inventory checks; direct backend policy now independently has exact input custody rather than relying on callers to sanitize for it.

## Current canonical owner truth
Canonical custody remains `tools/try_forever_owner_surgery_custody_probe.py` schema v10.

The previously documented **zero-partial-authority wound is closed at source level**. Current canonical source builds promotion groups only when `discoveryErrors` is empty; healthy surgery records may survive as diagnostics without promotion authority. The applied repair and current PR checkpoint are the authority for that state.

Do **not** resurrect the older doctrine that the zero-partial repair is `CORRECTED_PROPOSED_NOT_APPLIED`. That was stale historical state.

Do not treat a hard-coded historical owner blob in this skill as everlasting current custody. Promotion work must refresh authenticated owner readback at execution time.

### Exact canonical-composition boundary
Code-first owner archaeology establishes a narrower blocker than “policy not wired”:

- canonical v10 currently parses patch/delta semantics from the **portable pathname observation** inside the existing owner;
- `HeldDirectoryCustody` can produce held-root exact UTF-8 bytes, identity, counts, and SHA-256 evidence, but it does not itself parse those bytes into canonical Surgery/group semantics;
- `descriptor_shadow_audit` compares descriptor observations beside the portable canonical result and is explicitly non-authoritative;
- therefore selecting `HELD_DIRECTORY_DESCRIPTOR` and then calling portable `classify(...)` would be a silent weaker fallback, not composition;
- selecting the descriptor backend without an existing-owner semantic producer would also create an authority-shaped result with no canonical parser provenance.

The next valid owner mutation must make the **existing canonical owner** parse and group the exact bytes observed through the selected backend while preserving the v10 envelope and the no-weaker-fallback law. It must not introduce a second canonical custody owner or promote the shadow audit. Until that source exists and receives authenticated owner readback, canonical owner backend composition remains **NO**.

Current capability state:
- portable v10 canonical owner: **SOURCE_WIRED**;
- zero-partial-authority owner behavior: **SOURCE_WIRED**;
- platform capability exact-input custody: **SOURCE_WIRED**;
- platform capability hostile regression: **SOURCE / UNEXECUTED**;
- backend-selection policy semantic checks: **SUPPORTING SOURCE**;
- backend direct exact-input custody: **SOURCE_WIRED**;
- backend result-integrity exact-JSON snapshot composition: **SOURCE_WIRED**;
- backend witness parity: **SOURCE_WIRED**;
- POSIX descriptor custody: **SUPPORTING SOURCE**;
- descriptor shadow audit: **SUPPORTING SOURCE / NON-AUTHORITATIVE**;
- descriptor semantic result producer inside canonical owner: **NO**;
- backend/descriptor regressions: **SOURCE / UNEXECUTED**;
- canonical owner consumes backend-selection policy: **NO**;
- canonical owner consumes descriptor backend: **NO**;
- descriptor/root/candidate atomicity: **NO**;
- TESTED/runtime/deployed/phone/delivered/accepted: **NO**.

## Descriptor shadow staging
`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` may compare the existing held-directory custody source against canonical portable inventory evidence while canonical v10 remains the sole authority producer.

Shadow states are deliberately different from owner-selected backend states:
- `SHADOW_MATCH` = independent staging evidence agrees on compared paths/metrics; **not owner integration**;
- `SHADOW_DIVERGED` = stop and investigate evidence semantics before integration;
- `DESCRIPTOR_UNAVAILABLE` = descriptor primitives were never selected for authority, so canonical portable custody simply remains authority;
- `DESCRIPTOR_WOUND` = the non-authoritative shadow failed its own custody gate; canonical authority is unchanged.

A future **selected descriptor authority** failure is different: that must fail closed with no portable retry in the same classification attempt.

## Descriptor source relationship
`tools/try_forever_posix_directory_handle_custody.py` is the stronger POSIX supporting source. Its existence does not prove universal filesystem atomicity, Windows parity, canonical-owner integration, regression execution, runtime behavior, or delivery.

## Review / regression surfaces
Relevant source-only regression surfaces include:
- `tools/test_try_forever_owner_surgery_backend_policy.py`;
- `tools/test_try_forever_owner_surgery_backend_policy_exact_input_boundary.py` **CONVERGENCE SOURCE / UNEXECUTED**;
- `tools/test_try_forever_directory_handle_binding_capability.py` **SOURCE / UNEXECUTED**;
- `tools/test_try_forever_owner_surgery_backend_result_integrity.py`;
- `tools/test_try_forever_owner_surgery_backend_result_snapshot_boundary.py`;
- `tools/test_try_forever_owner_surgery_authority_member_integrity.py`;
- `tools/test_try_forever_owner_surgery_v10_contract.py`;
- `tools/test_try_forever_owner_surgery_descriptor_shadow_audit.py`;
- the descriptor custody I/O, cleanup, budget, and candidate-identity fixtures.

Their existence is not execution evidence.

## Cross-skill composition
`operator-receipt-bounded-container-admission` and `operator-receipt-snapshot-custody` supply the already-owned exact-container/bounded-snapshot laws used here. Backend selection does not fork those organs; it consumes them at its own public machine-evidence throat.

## Duplicate-architecture law
Do not create a descriptor promotion owner beside canonical v10. Future integration must compose the existing canonical owner, backend-selection/result-admission policy, result-integrity wrapper, and descriptor custody organ. The descriptor shadow is allowed only because it cannot emit promotion authority.

## Accessibility / touch
The existing backend-selection source specimen may expose the exact direct-policy throat and remaining canonical-owner boundary with keyboard/touch-native controls, non-color semantics, and reduced-motion behavior. Source art must explicitly remain SOURCE ONLY and may not claim Android runtime, TalkBack runtime, phone delivery, or acceptance.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting source → authenticated source readback → regression source → regression executed → canonical owner composition → authenticated owner readback → TESTED → runtime → deployed → callable → executed → delivered → accepted`.
