# Operator Semantic Announcement Migration

## Purpose

Migrate deprecated Android `announceForAccessibility(...)` usage by consequence, not by global search-and-replace. Preserve native semantic values, distinguish **value changes** from **repeatable action events**, and keep owner/source/test/runtime evidence separate.

Use this skill when a native Android owner still emits explicit announcements, especially after Android 16 / API 36 where `View.announceForAccessibility(...)` and `TYPE_ANNOUNCEMENT` are deprecated.

## Law

1. **Deprecation is not permission for blanket replacement.** Classify the consequence first.
2. **A live region is a changing semantic value, not a generic event bus.** Android describes live regions as views whose changes should notify the user. If the same action can complete twice with the same value, `POLITE + setText(sameValue)` is not an exact replacement contract.
3. **Changing TextView text stays the semantic value.** Do not mask it with a generic `contentDescription` merely to obtain speech.
4. **Automatic heartbeat material transition is currently the only migration-ready consequence.** Its existing announcement identity changes only for material transition/interruption semantics, so the existing summary value can inherit that exact gate.
5. **Spotify explicit receipt is a repeatable action event.** The current playback summary can remain identical across two completed commands. Do not remove the legacy receipt consequence until an explicit event/status value is designed that changes meaningfully for each completed receipt.
6. **Explicit heartbeat detail selection is a repeatable action event.** The same light can be selected twice with identical detail. Do not replace the legacy detail read with a live region on an unchanged passive detail value.
7. **Adam send confirmation is a repeatable action event.** Two sends in the same mode can produce the same simple `sent` label. A dedicated status is not sufficient unless its semantic value represents each completed send distinctly.
8. **Polite live regions are for meaningful changing status, not every poll.** Android warns that live regions can speak on every update. The existing heartbeat announcement-identity + mute + whole-overlay + heartbeat-surface gates remain authoritative.
9. **Heartbeat recovery clamps stale live-region state.** If the summary later writes `HEARTBEAT • waiting`, set live region `NONE` before changing the value so previous transition authority cannot leak into recovery bookkeeping.
10. **Legacy calls may be removed only after the existing native owner carries an exact replacement.** Policy/helper/fixture/patch existence alone is not owner wiring.
11. **Rejected patch provenance is not an invitation.** `patches/try-forever-operator-semantic-announcement-owner.patch` is `REJECTED_UNSAFE__DO_NOT_APPLY`; Git history preserves the failed design.
12. **No neighboring accessibility controller.** `OperatorOverlayService` remains the sole native owner.
13. **No duplicate offline-worker churn.** An offline Computer Hands worker plus occupied TRY FOREVER lanes is an execution boundary, not permission to create another request with the same owner target.
14. **No phone/P0 side effects.** Repository/source accessibility work stays outside the canonical P0 physical chain.
15. Preserve capability states: `requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

## Current consequence contract

`AccessibilityAnnouncementSemanticPolicy` now exposes both semantic class and migration readiness:

- **Heartbeat material transition** → `LIVE_REGION_VALUE_CHANGE` / `HEARTBEAT_SUMMARY_MATERIAL_TRANSITION` / `ownerMigrationReady=true`. The live-region gate returns POLITE only for a material, unmuted transition; otherwise NONE.
- **Spotify explicit command receipt** → `REPEATABLE_ACTION_EVENT_UNRESOLVED` / owner migration not ready.
- **Heartbeat explicit detail selection** → `REPEATABLE_ACTION_EVENT_UNRESOLVED` / owner migration not ready.
- **Adam send confirmation** → `REPEATABLE_ACTION_EVENT_UNRESOLVED` / owner migration not ready.

The three unresolved consequences deliberately return `ACCESSIBILITY_LIVE_REGION_NONE` from the pure policy even when called as explicit actions. That makes speculative owner migration fail closed instead of silently losing repeated same-value events.

## Current PR #329 source truth — 2026-08-21 0200 corrective review

- pre-mutation plan: **YES**;
- corrective replan after Regnet review: **YES**;
- policy source: **YES / IMPLEMENTED_SOURCE**;
- policy regression source: **YES / UNEXECUTED**;
- owner-boundary regression: **YES / UNEXECUTED**, RED only for heartbeat material-transition migration while requiring the three unresolved legacy calls to remain;
- first four-consequence owner surgery: **REJECTED_UNSAFE__DO_NOT_APPLY**;
- narrow heartbeat-only owner surgery: `patches/try-forever-heartbeat-material-transition-live-region-owner.patch`, base blob `d8cad8c2931c688d0c6fad6f67626fae75e044d1`, **YES / PROPOSED_NOT_APPLIED**;
- authenticated existing owner still contains all four `announceForAccessibility(...)` calls: **OWNER_WIRED NO**;
- Computer Hands `windows-hands-01`: **offline**, queue depth 4, existing TRY FOREVER lanes active; **no duplicate request created**;
- external Venice worker: **offline**; no worker verdict may be fabricated;
- She-Raw pre-execution consultation: **FAULT / account connection HTTP 400**, no substitute reviewer;
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Cross-skill composition

- `heartbeat-refresh-deduplication` owns the automatic material-transition/mute/visibility history gate. Announcement migration may change semantic delivery mechanism, not that gate.
- `dynamic-textview-semantic-value` keeps changing TextView text as the semantic value rather than replacing it with stale generic descriptions.
- `operator-repeatable-accessibility-event-semantics` owns the newly discovered same-value-event scar for explicit consequences.
- `operator-accessibility-owner-boundary` supplies lexical/direct-owner source evidence; it is not Android control-flow or TalkBack runtime proof.
- `home-center-mutation-lane-truth` governs whether a non-phone owner body is actually callable. Offline/occupied aggregate lanes are not execution receipts.

## Review checklist

Before migrating one consequence:

- Is this a **value change** or a **repeatable action event**?
- Can the consequence repeat while the proposed semantic value remains identical?
- Does the exact existing value/status owner change before an accessibility service is expected to react?
- For automatic heartbeat speech, is the existing material-transition/mute/visibility gate reused without a second history identity?
- Are background/poll changes silent?
- Does recovery/waiting clear stale live-region authority before changing summary text?
- Does the proposed owner change remove only the consequence whose replacement is exact?
- Is the source patch base-blob locked and still merely proposal until authenticated owner readback proves application?

If repeatable identical value remains possible and no fresh semantic event/status value is defined, keep the legacy consequence and mark **OWNER_WIRED=NO**.

## Capability membrane

`requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI observed → TalkBack exercised → deployed → callable → executed → delivered → accepted`

GitHub source/readback proves durable source only. A RED fixture is not a passed test. A patch is not owner wiring. Owner source wiring is not runtime accessibility proof. Runtime proof is not phone delivery. P0 remains separately owned.
