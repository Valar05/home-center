# Operator Owner Surgery Temporal Content Binding

## Purpose
Bind descriptor-shadow content comparison to the **same artifact bytes that produced the canonical custody result**, without creating another promotion authority.

This skill exists because `canonicalResultSha256` fingerprints the canonical result payload, while descriptor-shadow v3 currently observes artifact bytes later. Later portable/descriptor agreement is useful staging evidence, but it does not by itself prove which bytes produced canonical v10.

## Core laws
`CANONICAL RESULT SHA != CANONICAL ARTIFACT CONTENT WITNESS`.

`LATER PORTABLE BYTES == LATER DESCRIPTOR BYTES` does **not** imply `THOSE BYTES PRODUCED CANONICAL RESULT`.

`TEMPORAL CONTENT BINDING REQUIRES SAME-OBSERVATION CANONICAL WITNESSES`.

`CANONICAL CONTENT WITNESS MISSING => TEMPORAL BINDING NO`.

`CANONICAL RESULT ID MISMATCH => TEMPORAL BINDING NO`.

`CANONICAL WITNESS != LATER PORTABLE != LATER DESCRIPTOR => TEMPORAL CONTENT DIVERGED`.

`TEMPORAL CONTENT BOUND != PROMOTION AUTHORITY != FILESYSTEM ATOMICITY != TESTED != RUNTIME`.

## Supporting source
`tools/try_forever_owner_surgery_shadow_temporal_binding.py` is supporting source only.

It:
- requires exact canonical owner-surgery custody v10 and descriptor-shadow v3;
- recomputes deterministic canonical-result SHA-256 and rejects a shadow receipt bound to a different canonical payload;
- requires a future canonical `artifactContentWitnesses` list containing unique exact path, byteCount, and lowercase SHA-256 evidence from the same bounded artifact observations that produced canonical surgery records;
- reports `CANONICAL_CONTENT_WITNESS_MISSING` for current v10 rather than treating later-read agreement as temporal proof;
- reports `TEMPORAL_CONTENT_BOUND` only when canonical witnesses, later portable staging, and later descriptor staging match exactly;
- never admits authority, owner mutation, TESTED, runtime, deployment, phone delivery, or acceptance.

## Regression source
`tools/test_try_forever_owner_surgery_shadow_temporal_binding.py` is **SOURCE / UNEXECUTED**. It pins missing witness, result-identity mismatch, future exact binding, later-content divergence, duplicate witness identity, and malformed witness evidence.

`tools/test_try_forever_owner_surgery_temporal_binding_owner_boundary.py` is intentionally **RED / UNEXECUTED**. It requires:
- canonical `Surgery` records to retain same-observation artifact byte count and SHA-256 evidence; and
- descriptor shadow owner flow to consume the temporal-binding contract.

Until that boundary is repaired, owner integration is **NO**.

## Existing-owner rule
Do not create a second custody owner or second descriptor audit controller. Future integration must compose:
1. the existing canonical v10 owner artifact read;
2. the existing descriptor-shadow audit; and
3. this temporal-binding policy.

The preferred repair is to carry exact content identity out of the **same canonical bounded artifact observation**, not to perform a third read and call it canonical evidence.

## Accessibility / touch
Operator-facing source art may distinguish canonical-result identity, missing canonical content witness, temporal bound, and temporal divergence. It must say SOURCE ONLY and must not imply runtime TalkBack or phone delivery.

## P0 / phone firewall
This skill consumes no Phone Hands, primary-phone command, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance. P0 evidence is read-only.

## Capability membrane
At this checkpoint:
- supporting policy: **YES / SOURCE**;
- supporting regression: **YES / UNEXECUTED**;
- RED owner boundary: **YES / UNEXECUTED**;
- canonical same-observation content witness: **NO**;
- descriptor-shadow temporal-policy consumption: **NO**;
- temporal binding proven: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.
