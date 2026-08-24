# Operator Receipt Capability Closure

## Purpose
Make the bounded descriptor-shadow operator receipt close the complete commissioned capability membrane without repairing contradictory upstream evidence, silently overwriting final-command metadata, or consuming a drifting upstream receipt contract.

This skill does not create descriptor authority, runtime capability, deployment, phone execution, or a second receipt projector. It makes the existing bounded operator envelope more auditable.

## Core laws
`MISSING CORE CAPABILITY STATE != FALSE`.

`UPSTREAM TRUE/UNKNOWN != SOMETHING THE FINAL RECEIPT MAY SANITIZE TO FALSE`.

`FINAL OPERATOR RECEIPT CORE + LATER CAPABILITY STATES = EXACT FALSE`.

`FINAL-COMMAND METADATA NAMESPACE != UPSTREAM PROJECTOR NAMESPACE`.

`FINAL v4 != PERMISSION TO CONSUME DRIFTING UPSTREAM RECEIPT CONTRACTS`.

`PROJECTOR SCHEMA + RAW SOURCE SCHEMA + SELF-INTEGRITY SCHEMA = EXACT COMPOSITION CUSTODY`.

`FALSE-SHAPED CAPABILITY STATE CANNOT REPAIR A WRONG OR MISSING UPSTREAM SOURCE CONTRACT`.

`OPERATOR RECEIPT SHA BINDS THE COMPLETE BOUNDED CAPABILITY ENVELOPE`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != EXECUTED != DELIVERED != ACCEPTED`.

## Existing owners
`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the sole bounded operator receipt command.

`tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py` remains the self-integrity owner.

`tools/try_forever_owner_surgery_shadow_receipt_projection.py` remains the sole bounded display projector.

`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` remains the raw descriptor-shadow source owner.

No second receipt owner, projector, descriptor authority, overlay controller, recovery daemon, or phone path is created.

## Exact upstream composition custody
Before final capability closure, the existing v4 operator command now requires:
- `schema == try-forever-owner-surgery-descriptor-shadow-receipt.v2` from the sole bounded projector;
- `sourceSchema == try-forever-owner-surgery-descriptor-shadow.v3` from the raw descriptor-shadow owner;
- `receiptSelfIntegritySchema == try-forever-owner-surgery-shadow-receipt-self-integrity.v2` from the self-integrity owner.

Those values are imported from the existing owning modules rather than duplicated as free-standing literals. Missing or drifting contract identity rejects before final capability closure. A mapping cannot preserve conservative false fields while changing the upstream source contract and still become a valid v4 operator receipt.

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

Authenticated branch readback after the 06:00 hardening:
- operator receipt owner blob: `fe81fe1a417d36a87b6130db4e84a5a738478db7`;
- self-integrity owner blob: `8bbed4e2e2d12fe9292d94bd400e2e0f3905b085`;
- bounded projector blob: `4cc65f162f600e70a9771d7cf3edac94e45f5344`;
- raw-capability membrane blob: `24cfb9eea54b7295903e5dca248c7ed394b5d237`.

## Regression source
`tools/test_try_forever_descriptor_shadow_operator_receipt_capability_closure.py` is **YES / UNEXECUTED**.

It now pins:
- exact projector receipt schema, raw source schema, and self-integrity schema are required;
- missing or drifting upstream contract identity rejects before finalization;
- all core + later final capability fields are explicit false;
- missing core state rejects rather than being invented;
- positive core/later state rejects rather than being sanitized;
- exact upstream false remains compatible;
- upstream collision with any operator-owned final field rejects rather than being silently overwritten;
- deterministic receipt identity remains present.

Regression source blob: `984713e676c6d063b3bd162b8cc35ffa96ed964e`.

Do not call this TESTED merely because source exists.

## Current capability truth — 2026-08-24 06:00 CT
- operator receipt v4 source wiring: **YES / SOURCE_WIRED**;
- exact upstream composition-schema custody: **YES / SOURCE_WIRED**;
- complete core + later capability closure: **YES / SOURCE_WIRED**;
- final operator-owned namespace collision gate: **YES / SOURCE_WIRED**;
- authenticated repository readback: **YES**;
- regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / evidence consequence
Operator-facing state becomes less ambiguous without adding routine speech. A later renderer can distinguish explicit false from absent/unknown, and it cannot receive a final receipt whose upstream schema chain drifted or whose operator-owned metadata silently overwrote contradictory source fields.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, P0 recovery chain, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.