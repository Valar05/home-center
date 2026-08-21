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
7. **Spotify explicit command receipt** uses native command action + current status value. For an explicit command, the status may become a one-shot polite live region only when the status value actually changes. Startup/background status is not an explicit receipt.
8. **Explicit heartbeat detail selection** uses native selected-control state + the persistent full detail well. Re-selecting the same unchanged light does not create a new semantic fact and does not need a fake global announcement.
9. **Adam send confirmation** uses a mode-specific Send action plus the persistent cleared/sent input-result state. Same-mode resend may correctly stay quiet.
10. **Polite live regions are one-shot authority.** Reset live-region mode after the intended semantic mutation and on early-return/recovery paths so speech authority cannot leak into later bookkeeping.
11. **Legacy calls may be removed only after the existing native owner carries the exact replacement.** Policy/helper/fixture/patch existence alone is not owner wiring.
12. **No neighboring accessibility controller.** `OperatorOverlayService` remains the sole native owner.
13. **No phone/P0 side effects.** Repository/source accessibility work stays outside the canonical P0 physical chain.
14. Preserve capability states: `requested → policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

## Current consequence contract

`AccessibilityAnnouncementSemanticPolicy` now exposes semantic class and source-level migration readiness:

- **Heartbeat material transition** → `LIVE_REGION_VALUE_CHANGE` / `HEARTBEAT_SUMMARY_MATERIAL_TRANSITION` / source design ready.
- **Spotify explicit command receipt** → `LIVE_REGION_VALUE_CHANGE` / `SPOTIFY_ACTION_AND_STATUS_VALUE` / source design ready. POLITE requires explicit action + actual status change.
- **Heartbeat explicit detail selection** → `NATIVE_SELECTION_AND_DETAIL` / `HEARTBEAT_SELECTED_CONTROL_AND_DETAIL` / source design ready. No live region.
- **Adam send confirmation** → `NATIVE_ACTION_AND_RESULT_STATE` / `ADAM_MODED_SEND_AND_INPUT_RESULT` / source design ready. No live region.

`repeatableIdenticalValuePossible=true` does **not** itself require a synthetic repeat receipt. The policy now records `syntheticRepeatReceiptRequired=false`; the action/state semantics must pay rent instead.

## Regnet correction — sticky heartbeat live-region authority

The earlier narrow heartbeat owner patch set the summary live region to POLITE for a material transition but did not guarantee that the mode returned to NONE before an unchanged early-return path. That could leave stale speech authority attached to the summary.

The corrected patch now:

- starts the summary at `ACCESSIBILITY_LIVE_REGION_NONE`;
- clears live-region authority before WAITING/SKIP early returns;
- sets POLITE only immediately before the authorized material transition mutation;
- posts a reset back to NONE after that mutation;
- clears NONE before waiting-recovery text.

Patch state remains **CORRECTED_PROPOSED_NOT_APPLIED** until authenticated owner readback proves application.

## Current PR #329 source truth — 2026-08-21 0300

- durable pre-mutation plan gate: **YES**;
- She-Raw pre-execution consultation: **FAULT / account connection HTTP 400**, no substitute reviewer;
- policy source with all four exact semantic designs: **YES / IMPLEMENTED_SOURCE**;
- policy regression source: **YES / UNEXECUTED**;
- earlier broad announcement cannon: **REJECTED_UNSAFE__DO_NOT_APPLY**;
- corrected heartbeat-only owner surgery: `patches/try-forever-heartbeat-material-transition-live-region-owner.patch`, base blob `d8cad8c2931c688d0c6fad6f67626fae75e044d1`, **CORRECTED_PROPOSED_NOT_APPLIED**;
- Spotify/detail/Adam owner designs: **SOURCE_READY / OWNER_WIRED NO**;
- authenticated existing owner still contains all four legacy calls: **OWNER_WIRED NO**;
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Cross-skill composition

- `heartbeat-refresh-deduplication` owns the automatic material-transition/mute/visibility history gate. Announcement migration changes semantic delivery mechanism, not that identity.
- `dynamic-textview-semantic-value` keeps changing TextView text as the semantic value rather than replacing it with stale generic descriptions.
- `operator-repeatable-accessibility-event-semantics` owns the explicit-action/action+state contract and the no-fake-freshness law.
- `operator-accessibility-owner-boundary` supplies lexical/direct-owner source evidence; it is not Android control-flow or TalkBack runtime proof.
- `home-center-mutation-lane-truth` governs whether a non-phone owner body is actually callable; policy/patch existence is not execution.

## Review checklist

Before migrating one consequence:

- Is the consequence a semantic value change, a native action+state, or selection+detail?
- Can it repeat while the meaningful state stays identical, and if so is silence correct rather than a missing receipt?
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
