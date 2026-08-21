# Operator Semantic Announcement Migration

## Purpose

Migrate deprecated Android `announceForAccessibility(...)` usage by consequence, not by global search-and-replace. Preserve native semantic values, choose the narrowest semantic channel that represents the actual consequence, and keep owner/source/test/runtime evidence separate.

Use this skill when a native Android owner still emits explicit announcements, especially after Android 16 / API 36 where `View.announceForAccessibility(...)` and `TYPE_ANNOUNCEMENT` are deprecated.

## Law

1. **Deprecation is not permission for blanket replacement.** Classify the consequence first.
2. **Changing TextView text stays the semantic value.** Do not mask it with a generic `contentDescription` merely to obtain announcement behavior.
3. **Polite live regions are for meaningful changing status, not every poll.** Automatic heartbeat updates may surface only when the existing material-transition gate says the semantic consequence changed.
4. **Explicit detail selection is not an automatic broadcast.** Prefer the selected/focused detail semantic value; do not turn background evidence refresh into unsolicited speech.
5. **Action confirmation should be modeled as state/status when that is the real consequence.** Do not preserve a deprecated global announcer merely because it is convenient.
6. **User-triggered and automatic consequences are different authority classes.** A semantic channel that is acceptable for an explicit Spotify command receipt may be noisy or wrong for periodic status refresh.
7. **Legacy calls may be removed only after the existing native owner carries the replacement semantics.** Policy/helper/fixture existence alone is not owner wiring.
8. **No neighboring accessibility controller.** `OperatorOverlayService` remains the sole native owner for these surfaces.
9. **No phone/P0 side effects.** This skill owns repository/source accessibility work only unless the canonical P0 owners explicitly reopen a non-overlapping execution surface.
10. Preserve capability states: `requested → policy source → regression source → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

## Current PR #329 source truth

`AccessibilityAnnouncementSemanticPolicy` classifies four current legacy consequences:

- Spotify explicit command receipt → `POLITE_LIVE_REGION_VALUE`, user-triggered only.
- Heartbeat material transition → `POLITE_LIVE_REGION_VALUE`, automatic only behind the existing material-transition gate.
- Heartbeat explicit detail selection → `FOCUSED_DETAIL_VALUE`, user-triggered; background refresh must not become speech.
- Adam send confirmation → `STATUS_OR_STATE_DESCRIPTION`, user-triggered.

Current `OperatorOverlayService` still contains four `announceForAccessibility(...)` call sites for those consequences. Therefore:

- semantic migration policy: **YES / SUPPORTING_SOURCE**;
- policy regression source: **YES / UNEXECUTED**;
- existing-owner semantic migration wiring: **NO**;
- existing legacy announcements removed: **NO**;
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Review checklist

Before owner mutation, verify each call site independently:

- exact consequence and trigger source;
- whether the existing view already owns the changing semantic value;
- whether automatic updates are already deduplicated/material-gated;
- whether a live-region choice would cause periodic or evidence-only over-announcement;
- whether explicit selection has a real focused/selected semantic surface;
- whether action confirmation can be represented as status/state without replacing editable/value text;
- whether the proposed change removes one legacy call without inventing a second owner.

If any item is unresolved, preserve the legacy owner boundary as **OWNER_WIRED NO** and advance supporting policy/regression evidence instead of performing a speculative runtime surgery.
