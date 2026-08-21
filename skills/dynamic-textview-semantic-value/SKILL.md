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
6. On API 30+, `stateDescription` may expose the current interaction state. On older supported Android versions, the labeled standard click action must remain sufficient to describe the next consequence without inventing a parallel control.
7. Explicit post-action accessibility confirmation is a separate speech consequence and must honor the owner's existing mute contract.
8. Source evidence must include both initialization and the direct owner refresh/update path. A view that only looks dynamic at construction time does not satisfy the contract.
9. Comments, string literals, wrong methods, nested-class counterfeits, and helper existence do not prove owner wiring. Reuse the repository's lexical/direct-owner evidence organs.
10. Extend the existing deterministic owner probe or reuse its lexical/direct-owner helpers rather than creating a parallel accessibility parser when the same evidence machinery already exists.
11. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
12. Do not create a neighboring accessibility controller. Compose the existing `OperatorOverlayService` owner and existing evidence organs.
13. Phone/P0 firewall is binding: no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical-acceptance work belongs to this skill.

## Current PR #329 source truth

- Spotify dynamic status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Home Center connection/control status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Latest Home Center/Adam message TextView value: **YES / SOURCE_WIRED** — `OperatorOverlayService.createOverlay()` leaves `latest` with native changing-text semantics via `setContentDescription(null)`, while `refreshUi()` continues to update the text.
- Latest-message expand/collapse interaction semantics: **NO / OWNER_UNWIRED** — the existing clickable TextView toggles `expandedText`, but current authenticated owner blob `44d4e273e79f8dc37227651ba11a31842169db18` does not yet expose a labeled standard click action or state description for that visual interaction.
- Latest-message interaction policy: **YES / SUPPORTING_SOURCE** — `LatestMessageAccessibilityPolicy` owns bounded click-action, state, and confirmation strings without replacing the changing TextView value.
- Latest-message interaction policy regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `android/operator-overlay/app/src/test/java/com/homecenter/operatoroverlay/LatestMessageAccessibilityPolicyTest.java`.
- Latest-message interaction owner-boundary regression: **YES / RED / UNEXECUTED** at `tools/test_try_forever_latest_message_interaction_accessibility_owner_boundary.py`; it reuses the existing lexical/direct-owner evidence helpers.
- Exact existing-owner surgery: **YES / PROPOSED_NOT_APPLIED** at `patches/try-forever-latest-message-interaction-accessibility-owner.patch`, base-blob locked to `44d4e273e79f8dc37227651ba11a31842169db18`.
- Existing-owner latest-message interaction wiring: **NO**.
- Existing-owner latest-message semantic-value source commit: **YES** — `4a48e0e0dbd540291fbb75ca6c8800be58736dab`; authenticated owner blob after surgery: `44d4e273e79f8dc37227651ba11a31842169db18`.
- Existing deterministic accessibility owner probe: **YES / SUPPORTING_SOURCE** — its additive `latestMessageFocus` result uses the same v6 lexical/direct-owner-method evidence contract rather than introducing Probe II.
- Owner-probe latest seam regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `tools/test_try_forever_operator_accessibility_latest_probe.py`.
- Latest-message direct semantic-value owner-boundary regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `tools/test_try_forever_latest_textview_semantics_owner_boundary.py`.
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
- explicit expand/collapse confirmation honors the existing mute contract;
- comment/literal/wrong-method/nested-class markers cannot earn wiring authority;
- source proof does not claim runtime TalkBack behavior.

## Evidence membrane

`requested → semantic policy source → deterministic source probe/regression → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current state: `requested YES → semantic-value owner source wiring YES → interaction policy/regression/patch source YES → interaction owner wiring NO → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.

Never promote a state because a patch or helper exists; the dynamic-value seam was promoted only after authenticated owner mutation plus commit/readback evidence, and the interaction seam must meet the same standard.
