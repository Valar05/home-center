# Operator Receipt Capability Closure

## Purpose
Make the bounded descriptor-shadow operator receipt close the complete commissioned capability membrane without repairing contradictory upstream evidence, silently overwriting final-command metadata, consuming a drifting upstream receipt contract, or treating digest equality as capability authority.

This skill does not create descriptor authority, runtime capability, deployment, phone execution, or a second receipt projector. It makes the existing bounded operator envelope more auditable.

## Core laws
`MISSING CORE CAPABILITY STATE != FALSE`.

`UPSTREAM TRUE/UNKNOWN != SOMETHING THE FINAL RECEIPT MAY SANITIZE TO FALSE`.

`FINAL OPERATOR RECEIPT CORE + LATER CAPABILITY STATES = EXACT FALSE`.

`FINAL-COMMAND METADATA NAMESPACE != UPSTREAM PROJECTOR NAMESPACE`.

`FINAL v4 != PERMISSION TO CONSUME DRIFTING UPSTREAM RECEIPT CONTRACTS`.

`PROJECTOR SCHEMA + RAW SOURCE SCHEMA + SELF-INTEGRITY SCHEMA = EXACT COMPOSITION CUSTODY`.

`BUILD-TIME COMPOSITION CUSTODY != PERMISSION TO SKIP THE SAME CUSTODY DURING LATER RECEIPT REVERIFICATION`.

`FALSE-SHAPED CAPABILITY STATE CANNOT REPAIR A WRONG OR MISSING UPSTREAM SOURCE CONTRACT`.

`OPERATOR RECEIPT SHA BINDS THE COMPLETE BOUNDED CAPABILITY ENVELOPE`.

`MATCHING OPERATOR RECEIPT SHA != PERMISSION TO LAUNDER FINAL CAPABILITY, UPSTREAM CONTRACT, OR RAW-EVIDENCE BINDING STATE`.

`RAW-ONLY MACHINE EVIDENCE DRIFT MUST CHANGE RAW EVIDENCE IDENTITY AND THEREFORE FINAL OPERATOR RECEIPT IDENTITY`.

`INTERNALLY VALID RECEIPT IDENTITY != PROOF THAT A LATER SUPPLIED RAW MACHINE-EVIDENCE MAPPING IS THE SAME RAW EVIDENCE`.

`HASHABLE RAW MAPPING != DESCRIPTOR-SHADOW RAW EVIDENCE WITHOUT EXACT RAW SOURCE SCHEMA`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != EXECUTED != DELIVERED != ACCEPTED`.

## Existing owners
`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the sole bounded operator receipt command and owns the narrow v4 receipt reverification helpers.

`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the self-integrity owner.

`tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.

`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw descriptor-shadow source owner.

No second receipt owner, projector, descriptor authority, overlay controller, recovery daemon, or phone path is created.

## Exact upstream composition custody
Before final capability closure, the existing v4 operator command requires:
- `schema == try-forever-owner-surgery-descriptor-shadow-receipt.v2` from the sole bounded projector;
- `sourceSchema == try-forever-owner-surgery-descriptor-shadow.v3` from the raw descriptor-shadow owner;
- `receiptSelfIntegritySchema == try-forever-owner-surgery-shadow-receipt-self-integrity.v2` from the self-integrity owner.

Those values are imported from the existing owning modules rather than duplicated as free-standing literals. Missing or drifting contract identity rejects before final capability closure. A mapping cannot preserve conservative false fields while changing the upstream source contract and still become a valid v4 operator receipt.

As of the 08:04 hardening, `verify_operator_receipt_identity(...)` rechecks those exact upstream contract identities too. A caller cannot change one of the three upstream schema fields, recompute a self-consistent final digest, and use digest equality to launder the drift during later reverification.

This is composition custody, not a new schema owner. Operator receipt v4 output shape did not change and therefore does not get a cosmetic version bump.

## Full final capability closure
The bounded projector already owns these core receipt states:
- `authorityAdmitted`;
- `ownerMutation`;
- `regressionExecuted`;
- `tested`;
- `runtimeUi`;
- `runtimeTalkBack`;
- `phoneDelivered`.

The final operator command requires every core field to be present and exact false before finalization. Missing core state is unknown evidence, not permission to invent a denial.

The later capability fields remain additive below the final operator envelope:
- `deployed`;
- `callable`;
- `executed`;
- `delivered`;
- `accepted`.

If any later field is present upstream it must already be exact false. The v4 final envelope then emits every core and later field as explicit exact false, and all of them are inside `operatorReceiptSha256`.

`callable` / `executed` here describe the commissioned descriptor-shadow result, not Python function invocability.

## Final receipt identity custody
`verify_operator_receipt_identity(...)` lives in the existing final owner. It:
- requires exact operator receipt schema v4;
- rechecks exact projector receipt / raw shadow / self-integrity upstream source contracts;
- rechecks final raw-evidence separation/binding flags and architecture/phone denials;
- requires canonical lowercase SHA-256 raw-machine evidence identity;
- requires every final capability state to remain explicit exact false;
- recomputes `operatorReceiptSha256` over the complete bounded payload after removing only the digest field itself;
- rejects a stale or counterfeit digest rather than repairing it.

Digest equality is not a capability or contract gate. A caller that rewrites `tested=true`, `rawMachineEvidenceBound=false`, or any upstream source-contract identity and then recomputes a matching digest still fails the semantic/custody membrane before digest equality can legitimize the counterfeit.

## Raw machine-evidence linkage reverification
`verify_operator_receipt_against_raw_evidence(...)` lives in the same final owner. It first requires the complete v4 receipt identity/custody contract, then requires the supplied raw mapping itself to carry exact `try-forever-owner-surgery-descriptor-shadow.v3` source identity, recomputes the deterministic raw machine-evidence SHA-256, and compares it to `rawMachineEvidenceSha256`.

This makes two useful distinctions explicit:
- a receipt can remain internally identity-valid after the raw machine-evidence source has changed, but that old receipt must fail if somebody later tries to bind it to the changed raw evidence;
- a mapping being hashable and digest-matching is not permission to call it descriptor-shadow raw evidence if its own source contract is wrong.

The helper does not embed raw machine evidence in the operator receipt and does not grant descriptor authority, TESTED state, runtime capability, deployment, callability, execution, delivery, or acceptance.

The normal build path now invokes this stronger same-owner reverification before returning the final receipt.

## Operator-owned namespace custody
The final command owns these fields and upstream bounded projection may not pre-populate them:
- `operatorReceiptSchema`;
- raw machine-evidence inclusion/binding metadata and `rawMachineEvidenceSha256`;
- `secondReceiptProjectorCreated`;
- `secondDescriptorAuthorityCreated`;
- `phoneP0MutationAuthority`;
- `operatorReceiptSha256`.

Reject namespace collisions before dictionary merge. Final dictionary ordering is not an evidence-repair mechanism.

## Source wiring
Operator receipt schema v4 remains **YES / SOURCE_WIRED**; the output shape did not need a schema bump.

Authenticated branch readback after the 08:04 receipt reverification review:
- operator receipt owner blob: `a4f20c8d5c0e8a6c33664b0ed74550d3f5d2e78a`;
- identity/raw-linkage regression blob: `62ab34b12fcd45d12a88d6245989f2f4677be38a`;
- self-integrity owner remains the existing owner;
- bounded projector remains the existing sole display owner;
- raw descriptor-shadow audit remains the existing raw evidence owner.

## Regression source
Two focused source regressions exist and are **UNEXECUTED**:

`tools/test_try_forever_descriptor_shadow_operator_receipt_capability_closure.py`
- exact projector receipt schema, raw source schema, and self-integrity schema are required;
- missing or drifting upstream contract identity rejects before finalization;
- all core + later final capability fields are explicit false;
- missing core state rejects rather than being invented;
- positive core/later state rejects rather than being sanitized;
- exact upstream false remains compatible;
- upstream collision with any operator-owned final field rejects rather than being silently overwritten.

`tools/test_try_forever_descriptor_shadow_operator_receipt_identity.py`
- identical raw evidence yields stable raw/final receipt identity;
- raw-only evidence drift changes `rawMachineEvidenceSha256` and `operatorReceiptSha256` while bounded projection remains unchanged;
- an internally valid earlier receipt fails raw-evidence reverification against later changed raw evidence;
- raw-evidence reverification rejects a supplied mapping whose raw descriptor-shadow source schema is wrong;
- stale-digest bounded-payload tampering rejects;
- a recomputed matching digest cannot launder `tested=true` or `rawMachineEvidenceBound=false`;
- a recomputed matching digest cannot launder projector/raw/self-integrity contract drift;
- wrong final schema and normalization-dependent digest spelling reject.

Identity/raw-linkage regression blob: `62ab34b12fcd45d12a88d6245989f2f4677be38a`.

Do not call either source TESTED merely because it exists.

## Current capability truth — 2026-08-24 08:04 CT
- operator receipt v4 source wiring: **YES / SOURCE_WIRED**;
- exact upstream composition-schema custody during build: **YES / SOURCE_WIRED**;
- exact upstream composition-schema custody during later identity reverification: **YES / SOURCE_WIRED**;
- complete core + later capability closure: **YES / SOURCE_WIRED**;
- final operator-owned namespace collision gate: **YES / SOURCE_WIRED**;
- final receipt identity verifier: **YES / SOURCE_WIRED**;
- raw-evidence-to-final-receipt digest chain during build: **YES / SOURCE_WIRED**;
- independent receipt↔supplied-raw-evidence reverification: **YES / SOURCE_WIRED**;
- exact supplied raw source-schema admission during reverification: **YES / SOURCE_WIRED**;
- authenticated repository readback: **YES**;
- regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / evidence consequence
Operator-facing state becomes less ambiguous without adding routine speech. A later evidence reviewer cannot accept a self-consistent final digest whose upstream contract identity drifted, cannot bind an old internally valid receipt to different later raw machine evidence, and cannot treat a different raw source contract as descriptor-shadow evidence merely because its digest is well-formed.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, P0 recovery chain, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
