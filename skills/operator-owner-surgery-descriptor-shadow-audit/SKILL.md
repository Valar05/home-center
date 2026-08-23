# Operator Owner Surgery Descriptor Shadow Audit

## Purpose
Stage the existing POSIX held-directory custody organ beside canonical portable v10 owner-surgery custody **without creating a second authority producer**.

This skill owns one evidence-staging distinction. It does not own patch promotion, a second custody owner, a backend controller, Android runtime, phone execution, P0 recovery, deployment, delivery, or acceptance.

## Core laws
`CANONICAL PORTABLE AUTHORITY + DESCRIPTOR SHADOW != TWO AUTHORITIES`.

`CANONICAL SCHEMA != V10 => NO SHADOW STAGING`.

`CANONICAL EVIDENCE WOUND != SHADOW MATCH`.

`SHADOW RECEIPT BINDS TO EXACT CANONICAL RESULT SHA256`.

`REJECTED CANONICAL SCHEMA STILL GETS A RESULT FINGERPRINT; FINGERPRINTING != SCHEMA ADMISSION`.

`CANONICAL RESULT FINGERPRINT != CANONICAL ARTIFACT IDENTITY != ATOMIC FILESYSTEM BINDING`.

`SHADOW MATCH = PATH SET + WORK METRICS + EXACT COMPARED CONTENT IDENTITY`.

`SHADOW MATCH != CANONICAL OWNER DESCRIPTOR INTEGRATION`.

`SHADOW DIVERGENCE != PERMISSION TO PICK THE RESULT WE LIKE BETTER`.

`UNKNOWN CAPABILITY TEXT != DESCRIPTOR UNAVAILABLE`.

`SHADOW DESCRIPTOR WOUND != SELECTED-DESCRIPTOR FAILURE + PORTABLE FALLBACK` because the descriptor shadow never held promotion authority in the first place.

`DESCRIPTOR SUPPORTING SOURCE != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Source organ
`tools/try_forever_owner_surgery_descriptor_shadow_audit.py` is supporting source only, schema `try-forever-owner-surgery-descriptor-shadow.v3`.

It:
- asks canonical portable v10 `classify(...)` for the authority result first;
- deterministically serializes that returned canonical result and carries its SHA-256 as `canonicalResultSha256` so every bounded shadow or schema-wound receipt identifies the exact canonical payload it accompanied;
- requires the canonical result schema to be exactly `try-forever-owner-surgery-custody.v10` before any descriptor capability or artifact staging;
- returns `CANONICAL_SCHEMA_WOUND` on schema drift rather than reinterpreting a future or malformed authority payload under v10 assumptions, while retaining the rejected payload fingerprint for diagnostic identity;
- treats that result fingerprint as evidence association only: it is not schema admission, canonical artifact-content identity, or proof of atomic filesystem binding;
- requires canonical `evidenceComplete` to be an actual boolean rather than truthiness-normalizing malformed evidence;
- if canonical evidence is incomplete, returns `CANONICAL_WOUND` **before descriptor capability or artifact staging** so wounded authority cannot be decorated as a shadow match;
- checks current descriptor capability without changing the canonical backend only after canonical schema/evidence admission;
- treats only exact `PORTABLE_ATOMIC_BINDING_UNAVAILABLE` as ordinary descriptor unavailability;
- treats unknown/corrupt capability text as `CAPABILITY_WOUND` rather than repairing it into a harmless platform state;
- reuses the existing finite ordinary-file observer to collect portable-path staging `byteCount` + SHA-256 for the canonical artifact path set;
- reports `PORTABLE_SHADOW_WOUND` if that staging observation cannot be obtained exactly;
- when descriptor primitives are supported, reuses `HeldDirectoryCustody` and its existing entry/candidate/read budgets;
- carries enumeration-time candidate identity into descriptor-relative observation;
- independently records descriptor artifact byte count and SHA-256 evidence;
- compares descriptor candidate paths, inventory metrics, and exact per-path byte-count/SHA identity against portable staging evidence;
- returns `SHADOW_MATCH`, `SHADOW_DIVERGED`, `CANONICAL_SCHEMA_WOUND`, `CANONICAL_WOUND`, `PORTABLE_SHADOW_WOUND`, `DESCRIPTOR_UNAVAILABLE`, `CAPABILITY_WOUND`, or `DESCRIPTOR_WOUND`;
- never emits collision/stale/unverified promotion groups;
- never emits `ownerEvidenceAdmitted=true`;
- always reports `descriptorAuthorityAdmitted=false` and `ownerMutation=false`.

The portable exact-content staging observation is deliberately **not** a reinterpretation of canonical v10 authority. It exists only so `SHADOW_MATCH` cannot mean “same filenames, maybe different bytes.” Canonical semantic authority remains what canonical v10 produced.

A shadow match means the pathname staging observer and held-directory staging observer agree on the compared artifact set, work metrics, and exact content identity for the canonical-result fingerprint carried by that receipt. It is **staging evidence**, not permission to wire or promote the descriptor backend.

A shadow divergence is useful precisely because canonical authority remains unchanged. Stop, explain the disagreement, and repair evidence semantics before owner composition.

## Regression source
`tools/test_try_forever_owner_surgery_descriptor_shadow_audit.py` is **REGRESSION SOURCE / UNEXECUTED**.

It pins:
- shadow v3 match with exact v10 canonical schema;
- deterministic canonical-result fingerprinting independent of mapping insertion order;
- fingerprint sensitivity to material canonical evidence changes;
- wrong/future canonical schema becoming `CANONICAL_SCHEMA_WOUND` before artifact staging while retaining the exact rejected-result fingerprint;
- matching path set, inventory metrics, and exact byte/SHA identity;
- independent path-set divergence;
- independent metric divergence;
- independent exact-content divergence;
- portable finite-artifact staging wound;
- exact descriptor-unavailable behavior without a fake downgrade story;
- unknown/corrupt capability text failing as `CAPABILITY_WOUND`;
- typed descriptor wound with zero authority;
- canonical `evidenceComplete=false` becoming `CANONICAL_WOUND` before artifact staging;
- malformed non-boolean canonical `evidenceComplete` being rejected rather than normalized;
- no promotion-authority fields leaking out of the shadow result.

Do not call these tests passed until an authorized execution lane produces a receipt.

## Relationship to backend selection
`tools/try_forever_owner_surgery_backend_policy.py` remains the future composition gate. Its no-downgrade law applies **after the canonical owner actually selects the stronger descriptor backend for an authority classification attempt**.

The shadow audit deliberately happens earlier. Therefore:
- canonical schema drift → `CANONICAL_SCHEMA_WOUND`; receipt identity survives, descriptor staging does not begin;
- canonical evidence incomplete → `CANONICAL_WOUND`; descriptor staging does not begin;
- exact descriptor unavailable → canonical portable owner remains the independent authority path;
- unknown capability state → shadow capability wound; do not normalize it;
- portable staging observation wound → shadow comparison stops; canonical authority is unchanged;
- descriptor shadow wound → shadow evidence fails, canonical portable result is unaffected;
- future descriptor-selected owner wound → fail closed; no weaker retry in the same classification attempt.

Those states must not be collapsed.

## Current owner truth
Canonical owner: `tools/try_forever_owner_surgery_custody_probe.py` schema v10.

At this checkpoint:
- zero-partial-authority canonical owner repair: **SOURCE_WIRED**;
- canonical portable owner: **SOURCE_WIRED**;
- descriptor custody organ: **SUPPORTING SOURCE**;
- descriptor shadow audit v3: **SUPPORTING SOURCE**;
- canonical schema gate: **SUPPORTING SOURCE**;
- canonical-result receipt fingerprint: **SUPPORTING SOURCE**;
- exact content parity inside the shadow: **SUPPORTING SOURCE**;
- descriptor shadow regression: **SOURCE / UNEXECUTED**;
- canonical backend-selection consumption: **NO**;
- canonical descriptor owner integration: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Duplicate-architecture law
Do not create a descriptor promotion owner beside canonical v10. The shadow may inspect and compare evidence but may not classify promotion authority. Future integration must compose the existing canonical owner, backend policy, and descriptor custody organ.

## Accessibility / touch
A source specimen may make canonical-vs-shadow state visible and touch-inspectable, but source art must say SOURCE ONLY and must not imply Android runtime, TalkBack runtime, phone delivery, or acceptance.

Dynamic detail is an interaction result, not the persistent description of the entire radio group. Keep group instructions stable and let one atomic polite status surface announce the selected state; do not make every radio focus inherit the current detail paragraph.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting source → authenticated source readback → regression source → regression executed → canonical owner composition → authenticated owner readback → TESTED → runtime → deployed → callable → executed → delivered → accepted`.
