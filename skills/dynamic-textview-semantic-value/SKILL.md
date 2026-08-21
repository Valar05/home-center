# Dynamic TextView Semantic Value

## Purpose

Keep changing `TextView` content available as the accessibility semantic value instead of masking it with a stale or generic `contentDescription`.

Use this skill when a native Android `TextView` changes over time (status, message, playback state, receipt, etc.) and source also assigns a non-null `contentDescription` to that same view, or when a changing `TextView` is also interactive and its action/state semantics need to remain distinct from its changing value.

## Law

1. The visible changing text is semantic content, not decoration. Preserve it as the value accessibility services can announce.
2. Do not replace changing TextView content with a static/generic non-null `contentDescription`. Android accessibility guidance says TextView text is already announced; a content description can replace the description assistive technology would otherwise derive.
3. An explicit `setContentDescription(null)` is acceptable source evidence that the owner intentionally retains native text semantics. Absence of any override is also acceptable.
4. A clickable TextView does not gain permission to hide its changing text. Click/action semantics and the changing value are separate concerns.
5. When an interactive changing TextView has a binary visual state such as expanded/collapsed, expose the standard `ACTION_CLICK` consequence with an explicit action label. Do not encode the action by replacing the TextView's changing semantic value.
6. On API 30+, use the view's semantic `stateDescription` for current expanded/collapsed state. On older supported Android versions, the labeled standard click action must still describe the next consequence without inventing a parallel control.
7. Do not use `announceForAccessibility` / `TYPE_ANNOUNCEMENT` as confirmation for a simple expand/collapse action. Android 16 / API 36 deprecates announcement APIs and recommends semantic UI state; `View.setStateDescription(...)` supplies a semantic state-change event on supported versions.
8. Source evidence must include both initialization and the direct owner refresh/update path. A view that only looks dynamic at construction time does not satisfy the contract.
9. Comments, string literals, wrong methods, nested-class counterfeits, and helper existence do not prove owner wiring. Reuse the repository's lexical/direct-owner evidence organs.
10. Extend the existing deterministic owner probe or reuse its lexical/direct-owner helpers rather than creating a parallel accessibility parser when the same evidence machinery already exists.
11. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
12. Do not create a neighboring accessibility controller. Compose the existing `OperatorOverlayService` owner and existing evidence organs.
13. Multiple source-ready repairs against the same owner/base must be composed before owner mutation. Applying one standalone repair may stale another's base-lock and create partial accessibility state.
14. Phone/P0 firewall is binding: no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical-acceptance work belongs to this skill.

## Current PR #329 source truth

- Spotify dynamic status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Home Center connection/control status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Latest Home Center/Adam message TextView value: **YES / SOURCE_WIRED** — current owner leaves `latest` with native changing-text semantics via `setContentDescription(null)` while `refreshUi()` updates the text.
- Latest-message expand/collapse interaction semantics: **NO / OWNER_UNWIRED** — current authenticated owner blob `44d4e273e79f8dc37227651ba11a31842169db18` does not yet expose the labeled click action/state description.
- Latest-message interaction policy: **YES / SUPPORTING_SOURCE** — `LatestMessageAccessibilityPolicy` owns click-action and state strings without replacing the changing TextView value or generating a deprecated confirmation announcement.
- Latest-message interaction policy regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `android/operator-overlay/app/src/test/java/com/homecenter/operatoroverlay/LatestMessageAccessibilityPolicyTest.java`.
- Latest-message interaction owner-boundary regression: **YES / RED / UNEXECUTED** at `tools/test_try_forever_latest_message_interaction_accessibility_owner_boundary.py`; it requires semantic state/action and forbids `latest.announceForAccessibility`.
- Canonical owner surgery: **YES / PROPOSED_NOT_APPLIED** at `patches/try-forever-operator-interaction-accessibility-owner-combined.patch`, base-blob locked to `44d4e273e79f8dc37227651ba11a31842169db18` and composed with the dynamic action-button repair.
- Historical standalone latest-message patch: **SUPERSEDED_DO_NOT_APPLY_INDEPENDENTLY**.
- Existing-owner latest-message interaction wiring: **NO**.
- Existing-owner latest-message semantic-value wiring: **YES / SOURCE_WIRED**.
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- current text is set in `createOverlay` and refreshed in `refreshUi`;
- a static/generic non-null description plus dynamic text is a legacy owner shape;
- dynamic text with no non-null description is source-wired at the TextView semantic-value layer;
- null-at-init plus later non-null override fails closed as partial/unsafe;
- missing refresh ownership fails closed as partial/unsafe;
- interactive latest-message text exposes a labeled standard click action without reintroducing a non-null content description;
- API-30 state description is guarded and does not redefine the source text;
- simple expand/collapse does not reintroduce deprecated explicit announcements;
- comment/literal/wrong-method/nested-class markers cannot earn wiring authority;
- source proof does not claim runtime TalkBack behavior.

## Evidence membrane

`requested → semantic policy source → deterministic source probe/regression → combined existing-owner surgery → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current state: `requested YES → semantic-value owner source wiring YES → interaction policy/regression/combined-patch source YES → interaction owner wiring NO → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.

Never promote a state because a patch or helper exists. Owner mutation requires authenticated owner readback; runtime/TalkBack/phone acceptance requires its own evidence lane.
