# Dynamic TextView Semantic Value

## Purpose

Keep changing `TextView` content available as the accessibility semantic value instead of masking it with a stale or generic `contentDescription`.

Use this skill when a native Android `TextView` changes over time and source also assigns a non-null `contentDescription`, or when a changing `TextView` is interactive and its action/state semantics must remain distinct from its changing value.

## Law

1. Visible changing text is semantic content, not decoration. Preserve it as the value accessibility services can announce.
2. Do not replace changing TextView content with a static/generic non-null `contentDescription`.
3. An explicit `setContentDescription(null)` is acceptable source evidence that the owner intentionally retains native text semantics. Absence of any override is also acceptable.
4. A clickable TextView does not gain permission to hide its changing text. Click/action semantics and changing value are separate concerns.
5. For a binary visual state such as expanded/collapsed, expose the standard `ACTION_CLICK` consequence with an explicit action label without replacing the changing text value.
6. On API 30+, use semantic `stateDescription` for current expanded/collapsed state. Keep that state synchronized from the shared presentation-state owner so direct clicks and programmatic resets follow the same path.
7. Do not use `announceForAccessibility` / `TYPE_ANNOUNCEMENT` as confirmation for simple expand/collapse.
8. Source evidence must include initialization and the direct owner refresh/update path. A view that only looks dynamic at construction time does not satisfy the contract.
9. Comments, string literals, wrong methods, nested-class counterfeits, and helper existence do not prove owner wiring. Reuse the repository lexical/direct-owner evidence organs.
10. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
11. Do not create a neighboring accessibility controller. Compose the existing `OperatorOverlayService` owner.
12. Multiple source-ready repairs against the same owner/base must be composed before owner mutation.
13. Phone/P0 firewall is binding: no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance belongs to this skill.
14. **Spatial bound is not semantic amputation.** An expanded inspectable TextView may use a bounded-height scrolling viewport, but must not impose a finite line ceiling that makes later source text unreachable. Collapse may intentionally use a short line+ellipsis preview; expansion must preserve the full layout.

## Current PR #329 source truth

- Spotify dynamic status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Home Center connection/control status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Latest Home Center/Adam message TextView value: **YES / SOURCE_WIRED** — owner leaves `latest` with native changing-text semantics via `setContentDescription(null)` while `refreshUi()` updates the text.
- Latest-message interaction policy: **YES / SUPPORTING_SOURCE** at `LatestMessageAccessibilityPolicy`.
- Latest-message ACTION_CLICK label: **YES / SOURCE_WIRED** through the existing `OperatorOverlayService` accessibility delegate.
- Latest-message expanded/collapsed state: **YES / SOURCE_WIRED**. API 30+ `stateDescription` is synchronized in `applyExpandedTextState()`.
- Latest-message expanded full-layout policy: **YES / SOURCE_WIRED** — `OperatorOverlayService.applyExpandedTextState()` now consumes `LatestMessageAccessibilityPolicy.maxLines(...)` and the existing 520dp height throat. Owner commit `5ad44ee456a8b1666b740ae7f44e019e3ef43142`, owner blob `c5de1411a6b68087ae17aff83c032af754587150`.
- Latest-message expanded full-layout owner-boundary regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `tools/test_try_forever_latest_message_surface_owner_boundary.py`.
- Latest-message full-layout owner patch provenance: **YES / APPLIED_SOURCE** at `patches/try-forever-latest-message-full-layout-owner.patch`.
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- current text is set in `createOverlay` and refreshed in `refreshUi`;
- dynamic text has no non-null description override;
- interactive latest-message text exposes a labeled standard click action without reintroducing a non-null content description;
- API-30 state description is guarded and uses the shared presentation-state owner;
- programmatic panel collapse resets latest-message expanded state through that same semantic owner;
- simple expand/collapse does not reintroduce deprecated explicit announcements;
- expanded inspection uses full layout plus bounded-height scrolling, not a finite expanded line ceiling;
- comment/literal/wrong-method/nested-class markers cannot earn wiring authority;
- source proof does not claim runtime TalkBack behavior.

## Evidence membrane

`requested → semantic policy source → deterministic source regression → existing-owner surgery → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current new-slice state: `requested YES → expanded full-layout policy/regression YES → owner wiring YES / SOURCE_WIRED → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.

Never promote a state because a patch or helper exists. Owner source wiring requires authenticated owner readback; runtime/TalkBack/phone acceptance requires its own evidence lane.
