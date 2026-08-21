# Operator Semantic Announcement Migration

## Purpose

Migrate deprecated Android `announceForAccessibility(...)` usage by consequence, not by global search-and-replace. Preserve native semantic values, distinguish **meaningful value changes** from **native actions/state**, and keep owner/source/test/runtime evidence separate.

Use this skill when a native Android owner still emits explicit announcements, especially after Android 16 / API 36 where `View.announceForAccessibility(...)` and `TYPE_ANNOUNCEMENT` are deprecated.

## Law

1. **Deprecation is not permission for blanket replacement.** Classify the consequence first.
2. **A live region is a changing semantic value, not a generic event bus.** Gate it to the exact semantic value change that matters.
3. **A simple repeated action does not require a synthetic repeated confirmation.** If the native control names the action and the meaningful result is persistently inspectable, an identical repeat may correctly stay quiet.
4. **Changing TextView text stays the semantic value.** Do not mask it with a generic `contentDescription` merely to obtain speech.
5. **No fake freshness.** Do not append timestamps, counters, punctuation, zero-width text, or opaque request IDs solely to force accessibility output.
6. **Heartbeat automatic material transition** uses the existing material-transition/announcement identity. It may drive a one-shot polite live-region update only when the existing mute/visibility/surface gate authorizes it.
7. **Repeatable explicit-event designs are not automatically owner-migration-ready.** Spotify receipt, repeated detail selection, and Adam send may have useful source designs while their legacy receipt remains the safer existing-owner behavior.
8. **Legacy calls may be removed only after the exact consequence contract is reviewed and the existing native owner carries the replacement.** Policy/helper/fixture/patch existence alone is not owner wiring.
9. **Polite live regions are one-shot authority.** Reset live-region mode after the intended semantic mutation and on early-return/recovery paths so speech authority cannot leak into later bookkeeping.
10. **No neighboring accessibility controller.** `OperatorOverlayService` remains the sole native owner.
11. **No phone/P0 side effects.** Repository/source accessibility work stays outside the canonical P0 physical chain.
12. Preserve capability states: `requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

## Current consequence contract — 2026-08-21 0400 reconciliation

`AccessibilityAnnouncementSemanticPolicy` exposes semantic class separately from **owner migration readiness**:

- **Heartbeat material transition** → `LIVE_REGION_VALUE_CHANGE` / `HEARTBEAT_SUMMARY_MATERIAL_TRANSITION` / **OWNER_MIGRATION_READY=true**.
- **Spotify explicit command receipt** → `LIVE_REGION_VALUE_CHANGE` / `SPOTIFY_ACTION_AND_STATUS_VALUE` / source design exists, **OWNER_MIGRATION_READY=false**.
- **Heartbeat explicit detail selection** → `NATIVE_SELECTION_AND_DETAIL` / `HEARTBEAT_SELECTED_CONTROL_AND_DETAIL` / source design exists, **OWNER_MIGRATION_READY=false**.
- **Adam send confirmation** → `NATIVE_ACTION_AND_RESULT_STATE` / `ADAM_MODED_SEND_AND_INPUT_RESULT` / source design exists, **OWNER_MIGRATION_READY=false**.

The three repeatable explicit-event consequences fail closed until their owner event semantics are reviewed as complete contracts. Supporting design is not permission to remove a working legacy receipt.

## Canonical owner-surgery state

- `patches/try-forever-heartbeat-material-transition-live-region-owner.patch` remains the only currently review-ready announcement migration surgery. It is **CORRECTED_PROPOSED_NOT_APPLIED** against owner blob `d8cad8c2931c688d0c6fad6f67626fae75e044d1`.
- `patches/try-forever-semantic-announcement-owner-v2.patch` is **REJECTED_SUPERSEDED__DO_NOT_APPLY**. It attempted to migrate all four consequences and conflicts with the fail-closed repeatable-event owner boundary.
- `tools/test_try_forever_semantic_announcement_owner_boundary.py` is the current RED owner-boundary source: heartbeat migration expected; Spotify/detail/Adam legacy calls retained.
- `AccessibilityAnnouncementSemanticPolicyTest` now pins the same readiness split.

## Current PR #329 source truth — 2026-08-21 0400

- durable pre-mutation plan gate: **YES**;
- She-Raw pre-execution consultation: **FAULT / account connection HTTP 400**, no substitute reviewer;
- policy source reconciled with owner-boundary regression: **YES / IMPLEMENTED_SOURCE**;
- policy regression source: **YES / UNEXECUTED**;
- broad four-consequence owner surgery: **REJECTED_SUPERSEDED__DO_NOT_APPLY**;
- corrected heartbeat-only owner surgery: **CORRECTED_PROPOSED_NOT_APPLIED**;
- authenticated existing owner still contains all four legacy calls: **OWNER_WIRED NO**;
- Computer Hands worker `windows-hands-01`: **offline**, existing TRY FOREVER lanes present; no duplicate owner request;
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Cross-skill composition

- `heartbeat-refresh-deduplication` owns the automatic material-transition/mute/visibility history gate. Announcement migration changes semantic delivery mechanism, not that identity.
- `dynamic-textview-semantic-value` keeps changing TextView text as the semantic value rather than replacing it with stale generic descriptions.
- `operator-repeatable-accessibility-event-semantics` owns the unresolved repeatable explicit-event contract and the no-fake-freshness law.
- `operator-accessibility-owner-boundary` supplies lexical/direct-owner source evidence; it is not Android control-flow or TalkBack runtime proof.
- `home-center-mutation-lane-truth` governs whether a non-phone owner body is actually callable; policy/patch existence is not execution.

## Review checklist

Before migrating one consequence:

- Is the consequence a semantic value change, a native action+state, or selection+detail?
- Can it repeat while the meaningful state stays identical?
- Is silence on an identical repeat actually correct, or would that remove a meaningful receipt?
- Is the action itself self-describing?
- Is the meaningful changed result persistently inspectable?
- For live-region use, is the update gated to an actual semantic change and cleared afterward?
- Are startup/background/poll paths silent unless independently authorized?
- Does the change preserve mute, focus, selection, viewport contact, and recovery laws?
- Does the existing native owner carry the replacement?
- Is regression execution separate from regression-source existence?

## Capability membrane

`requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI observed → TalkBack exercised → deployed → callable → executed → delivered → accepted`

GitHub source/readback proves durable source only. A RED fixture is not a passed test. A patch is not owner wiring. Owner source wiring is not runtime accessibility proof. Runtime proof is not phone delivery. P0 remains separately owned.
