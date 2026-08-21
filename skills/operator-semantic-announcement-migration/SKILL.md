# Operator Semantic Announcement Migration

## Purpose

Migrate deprecated Android `announceForAccessibility(...)` usage by consequence, not by global search-and-replace. Preserve native semantic values, choose the narrowest semantic channel that represents the actual consequence, and keep owner/source/test/runtime evidence separate.

Use this skill when a native Android owner still emits explicit announcements, especially after Android 16 / API 36 where `View.announceForAccessibility(...)` and `TYPE_ANNOUNCEMENT` are deprecated.

## Law

1. **Deprecation is not permission for blanket replacement.** Classify the consequence first.
2. **Changing TextView text stays the semantic value.** Do not mask it with a generic `contentDescription` merely to obtain announcement behavior.
3. **A live region is a value lifecycle, not a new global announcer.** If one existing TextView receives both user/material updates and background refreshes, enable `POLITE` before the permitted update and explicitly set `NONE` before background/poll changes.
4. **Polite live regions are for meaningful changing status, not every poll.** Android warns that live regions can speak on every update. The existing heartbeat announcement-identity + mute + whole-overlay + heartbeat-surface gates remain authoritative for automatic transition speech.
5. **Explicit detail selection is not background speech.** The existing heartbeat detail value may be polite for an explicit, unmuted selection; any later evidence/background refresh must disable the live region before changing the detail value. The passive detail well is not claimed as a keyboard-focus owner.
6. **Action confirmation should be a persistent semantic status when that is the real consequence.** Adam send confirmation belongs on a dedicated status TextView rather than an announcement emitted from the editable input.
7. **Spotify explicit receipt and automatic status are different authority classes.** A user-triggered receipt may make the existing Spotify value polite; request-id-zero/background refresh must disable the live region before updating that same value.
8. **Mute preserves existing semantics rather than silently widening them.** Heartbeat transition/detail speech respects the global mute gate. Explicit Spotify and Adam confirmations keep their prior owner behavior and are not newly tied to mute by this migration.
9. **Waiting/recovery must clamp stale live-region state.** If heartbeat recovery writes `HEARTBEAT • waiting`, set its live region to `NONE` before changing the value so an earlier material transition cannot lend speech authority to recovery bookkeeping.
10. **Legacy calls may be removed only after the existing native owner carries the replacement semantics.** Policy/helper/fixture/patch existence alone is not owner wiring.
11. **No neighboring accessibility controller.** `OperatorOverlayService` remains the sole native owner for these surfaces.
12. **No duplicate offline-worker churn.** A currently offline Computer Hands worker plus occupied TRY FOREVER lanes is an execution boundary, not permission to create another request with the same owner target.
13. **No phone/P0 side effects.** This skill owns repository/source accessibility work only unless the canonical P0 owners explicitly reopen a non-overlapping execution surface.
14. Preserve capability states: `requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

## Exact consequence contract

`AccessibilityAnnouncementSemanticPolicy` now names both channel and existing-owner mechanism:

- **Spotify explicit command receipt** → existing `spotifyStatus` TextView, native text value preserved; `POLITE` only when `requestId > 0`; background/request-id-zero refresh must set `NONE` before changing text.
- **Heartbeat material transition** → existing `heartbeatSummary` TextView; `POLITE` only when the existing `HeartbeatOverlayRefreshPlan.shouldAnnounce(...)` presentation gate allows the transition. Evidence-only, muted, hidden, and collapsed-surface updates must remain silent while announcement identity still advances according to the existing refresh-deduplication law.
- **Heartbeat explicit detail selection** → existing `heartbeatDetail` TextView; `POLITE` only for explicit unmuted selection. Background/evidence refresh sets `NONE` before changing the same detail value. Full exact detail remains inspectable; this does not invent focus ownership.
- **Adam send confirmation** → dedicated `adamStatus` TextView in the existing overlay owner, with native text as the semantic value. It updates only after a real send. The editable `adamInput` keeps its input/value semantics and is no longer the announcement source after owner migration.

The pure policy also exposes the live-region mode gate so owner code does not have to re-invent the four consequence rules.

## Current PR #329 source truth — 2026-08-21 0200

- semantic mechanism policy: **YES / IMPLEMENTED_SOURCE**;
- policy regression source: **YES / UNEXECUTED**;
- RED owner-boundary regression: **YES / UNEXECUTED**;
- exact existing-owner surgery: `patches/try-forever-operator-semantic-announcement-owner.patch`, base blob `d8cad8c2931c688d0c6fad6f67626fae75e044d1`, **YES / PROPOSED_NOT_APPLIED**;
- authenticated existing owner still contains all four `announceForAccessibility(...)` calls: **OWNER_WIRED NO**;
- Computer Hands `windows-hands-01`: **offline** with existing TRY FOREVER lanes active; **no duplicate request created**;
- external Venice worker: **offline**; no worker verdict may be fabricated;
- She-Raw pre-execution consultation: **FAULT / account connection HTTP 400**, no substitute reviewer;
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Cross-skill composition

This migration composes existing organs rather than superseding them:

- `heartbeat-refresh-deduplication` owns the automatic material-transition/mute/visibility history gate. Announcement migration may change the semantic delivery mechanism, not that gate.
- `dynamic-textview-semantic-value` keeps changing TextView text as the semantic value rather than replacing it with stale generic descriptions.
- `operator-accessibility-owner-boundary` supplies lexical/direct-owner source evidence; it is not Android control-flow or TalkBack runtime proof.
- `home-center-mutation-lane-truth` governs whether a non-phone owner body is actually callable. Offline/occupied aggregate lanes are not execution receipts.
- `heartbeat-hard-returned-text-budgets` remains responsible for bounded visible/spoken projections; announcement migration must not reintroduce UTF-16 or unbounded speech cuts.

## Review checklist

Before owner mutation, verify each call site independently:

- exact consequence and trigger source;
- exact existing value/status owner;
- live-region mode is set **before** changing the value;
- background/poll updates explicitly disable live-region state before changing a shared value;
- automatic heartbeat updates reuse the existing material-transition/mute/visibility gate and do not create a second history identity;
- explicit detail selection does not turn background evidence refresh into speech or claim focus ownership;
- Adam confirmation uses a dedicated status value without replacing editable input semantics;
- recovery/waiting paths clear stale live-region state before changing heartbeat summary;
- the proposed change removes all four legacy calls without inventing a second owner;
- source patch is base-blob locked and remains proposal until authenticated owner readback proves application.

If any item is unresolved, preserve **OWNER_WIRED=NO** and advance source/regression evidence instead of performing speculative runtime surgery.

## Capability membrane

Keep these states distinct:

`requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI observed → TalkBack exercised → deployed → callable → executed → delivered → accepted`

GitHub source/readback proves durable source only. A RED fixture is not a passed test. A patch is not owner wiring. Owner source wiring is not runtime accessibility proof. Runtime proof is not phone delivery. P0 remains separately owned.
