# Operator Semantic Announcement Migration

## Purpose

Migrate deprecated Android `announceForAccessibility(...)` usage by consequence, not by global search-and-replace. Preserve native semantic values, distinguish **meaningful value changes** from **native actions/state**, and keep owner/source/test/runtime evidence separate.

Use this skill when a native Android owner still emits explicit announcements, especially after Android 16 / API 36 where `View.announceForAccessibility(...)` and `TYPE_ANNOUNCEMENT` are deprecated.

## Law

1. **Deprecation is not permission for blanket replacement.** Classify the consequence first.
2. **A live region is a changing semantic value, not a generic event bus.** Gate it to the exact semantic value change that matters.
3. **A simple repeated action does not require a synthetic repeated confirmation by default.** If the native control names the action and the meaningful result is persistently inspectable, an identical repeat may correctly stay quiet—but removal of an existing receipt still needs a complete owner contract.
4. **Changing TextView text stays the semantic value.** Do not mask it with a generic `contentDescription` merely to obtain speech.
5. **No fake freshness.** Do not append timestamps, counters, punctuation, zero-width text, or opaque request IDs solely to force accessibility output.
6. **Heartbeat automatic material transition** uses the existing material-transition/announcement identity. It may drive a one-shot polite live-region update only when the existing mute/visibility/surface gate authorizes it.
7. **Repeatable explicit-event designs are not automatically owner-migration-ready.** Spotify receipt, repeated detail selection, and Adam send may have useful source designs while their legacy receipt remains the safer existing-owner behavior.
8. **Migration-unready must be typed, not vibes.** Every designed consequence carries an explicit `MigrationBlocker`; `ownerMigrationReady=true` is valid only with blocker `NONE`.
9. **Legacy calls may be removed only after the exact consequence contract is reviewed and the existing native owner carries the replacement.** Policy/helper/fixture/patch existence alone is not owner wiring.
10. **Polite live regions are one-shot authority.** Reset live-region mode after the intended semantic mutation and on early-return/recovery paths so speech authority cannot leak into later bookkeeping.
11. **Review-ready surgery must be locked to current owner custody.** A patch intended for promotion must name the authenticated current owner blob; rejected historical archaeology must stay rejected and need not be continuously rebased to look apply-ready.
12. **No neighboring accessibility controller.** `OperatorOverlayService` remains the sole native owner.
13. **No phone/P0 side effects.** Repository/source accessibility work stays outside the canonical P0 physical chain.
14. Preserve capability states: `requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

## Current consequence contract — 2026-08-21 0811

`AccessibilityAnnouncementSemanticPolicy` exposes semantic class, **owner migration readiness**, and a typed source-review blocker:

- **Heartbeat material transition** → `LIVE_REGION_VALUE_CHANGE` / `HEARTBEAT_SUMMARY_MATERIAL_TRANSITION` / `OWNER_MIGRATION_READY=true` / blocker `NONE`.
- **Spotify explicit command receipt** → `LIVE_REGION_VALUE_CHANGE` / `SPOTIFY_ACTION_AND_STATUS_VALUE` / `OWNER_MIGRATION_READY=false` / blocker `SPOTIFY_REPEATABLE_RECEIPT_UNRESOLVED`.
- **Heartbeat explicit detail selection** → `NATIVE_SELECTION_AND_DETAIL` / `HEARTBEAT_SELECTED_CONTROL_AND_DETAIL` / `OWNER_MIGRATION_READY=false` / blocker `DETAIL_REPEAT_SELECTION_RECEIPT_UNRESOLVED`.
- **Adam send confirmation** → `NATIVE_ACTION_AND_RESULT_STATE` / `ADAM_MODED_SEND_AND_INPUT_RESULT` / `OWNER_MIGRATION_READY=false` / blocker `ADAM_REPEAT_SEND_RESULT_UNRESOLVED`.

The three repeatable explicit-event consequences fail closed until their owner event semantics are reviewed as complete contracts. A typed blocker is a durable review reason, not runtime evidence and not permission to invent a replacement event channel.

## Canonical owner-surgery state

- Authenticated current owner blob observed at plan time: `c5de1411a6b68087ae17aff83c032af754587150`.
- `patches/try-forever-heartbeat-material-transition-live-region-owner.patch` remains the only currently review-ready announcement migration surgery. It is **CORRECTED_PROPOSED_NOT_APPLIED** and was re-locked at 0811 to that current owner blob after unrelated owner accessibility surgery changed custody.
- `patches/try-forever-semantic-announcement-owner-v2.patch` is **REJECTED_SUPERSEDED__DO_NOT_APPLY** historical provenance. Rejected archaeology must remain unmistakably rejected; it is not required to chase the current owner blob.
- `tools/test_try_forever_semantic_announcement_owner_boundary.py` is the RED owner-boundary source: heartbeat migration expected; Spotify/detail/Adam legacy calls retained.
- `tools/test_try_forever_semantic_announcement_inventory.py` is the source inventory guard: exactly four known legacy consequence calls, no fifth silent consequence, current narrow patch removes only heartbeat, rejected broad patch stays historical, and every unready consequence has a named blocker.
- `AccessibilityAnnouncementSemanticPolicyTest` pins the readiness/blocker relation. Regression source is not executed test evidence.

## Current PR #329 source truth — 2026-08-21 0811

- durable pre-mutation plan gate: **YES** (`receipts/heartbeat-skill-lights/2026-08-21-0811-plan.json`);
- She-Raw pre-execution consultation: **FAULT / account connection HTTP 400**, no substitute reviewer;
- policy source with typed migration blockers: **YES / IMPLEMENTED_SOURCE**;
- policy regression source: **YES / UNEXECUTED**;
- owner-inventory regression source: **YES / UNEXECUTED**, corrected so rejected archaeology is not falsely required to track current owner custody;
- broad four-consequence owner surgery: **REJECTED_SUPERSEDED__DO_NOT_APPLY**;
- corrected heartbeat-only owner surgery: **CORRECTED_PROPOSED_NOT_APPLIED / CURRENT_OWNER_BLOB_LOCKED**;
- authenticated existing owner at plan time still contains all four legacy calls: **OWNER_WIRED NO**;
- Command Center Codex agents/jobs/sessions/workers: **PERMANENTLY RETIRED** in current Home Center capability surface; no worker queue is a valid substitute lane;
- large owner mutation was not reconstructed through an adjacent mechanism merely to manufacture a receipt: **BOUNDARY PRESERVED**;
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO unless fresh exact-head evidence proves otherwise**.

## Cross-skill composition

- `heartbeat-refresh-deduplication` owns the automatic material-transition/mute/visibility history gate. Announcement migration changes semantic delivery mechanism, not that identity.
- `dynamic-textview-semantic-value` keeps changing TextView text as the semantic value rather than replacing it with stale generic descriptions.
- `operator-repeatable-accessibility-event-semantics` owns the unresolved repeatable explicit-event contracts, the typed blocker consequences, and the no-fake-freshness law.
- `operator-accessibility-owner-boundary` supplies lexical/direct-owner source evidence; it is not Android control-flow or TalkBack runtime proof.
- `home-center-mutation-lane-truth` governs whether a non-phone owner body is actually callable; policy/patch existence is not execution.

## Review checklist

Before migrating one consequence:

- What exact semantic channel owns the consequence?
- Is its `MigrationBlocker` `NONE`, and if so, what reviewed evidence removed the former blocker?
- Can the consequence repeat while the meaningful state stays identical?
- Is silence on an identical repeat correct, or would that remove a meaningful receipt?
- Is the action itself self-describing?
- Is the meaningful changed result persistently inspectable?
- For live-region use, is the update gated to an actual semantic change and cleared afterward?
- Are startup/background/poll paths silent unless independently authorized?
- Does the change preserve mute, focus, selection, viewport contact, and recovery laws?
- Does the existing native owner carry the replacement?
- If a patch is review-ready, is its base blob the authenticated current owner blob?
- Is rejected patch archaeology still clearly historical rather than continuously rebased into an apply-shaped artifact?
- Does the owner inventory still account for every legacy call with no unexpected fifth consequence?
- Is regression execution separate from regression-source existence?

## Capability membrane

`requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI observed → TalkBack exercised → deployed → callable → executed → delivered → accepted`

GitHub source/readback proves durable source only. A RED fixture is not a passed test. A patch is not owner wiring. Owner source wiring is not runtime accessibility proof. Runtime proof is not phone delivery. P0 remains separately owned.
