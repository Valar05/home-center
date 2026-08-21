# Dynamic TextView Semantic Value

## Purpose

Keep changing `TextView` content available as the accessibility semantic value instead of masking it with a stale or generic `contentDescription`.

Use this skill when a native Android `TextView` changes over time (status, message, playback state, receipt, etc.) and source also assigns a non-null `contentDescription` to that same view.

## Law

1. The visible changing text is semantic content, not decoration. Preserve it as the value accessibility services can announce.
2. Do not replace changing TextView content with a static/generic non-null `contentDescription`. Android accessibility guidance says TextView text is already announced; a content description can replace the description assistive technology would otherwise derive.
3. An explicit `setContentDescription(null)` is acceptable source evidence that the owner intentionally retains native text semantics. Absence of any override is also acceptable.
4. A clickable TextView does not gain permission to hide its changing text. Click/action semantics and the changing value are separate concerns.
5. Source evidence must include both initialization and the direct owner refresh/update path. A view that only looks dynamic at construction time does not satisfy the contract.
6. Comments, string literals, wrong methods, nested-class counterfeits, and helper existence do not prove owner wiring. Reuse the repository's lexical/direct-owner evidence organs.
7. Extend the existing deterministic owner probe rather than creating a parallel accessibility probe when the same lexical/class/method-scoping machinery already owns the evidence question.
8. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
9. Do not create a neighboring accessibility controller. Compose the existing `OperatorOverlayService` owner and existing evidence organs.
10. Phone/P0 firewall is binding: no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical-acceptance work belongs to this skill.

## Current PR #329 source truth

- Spotify dynamic status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Home Center connection/control status TextView: **YES / SOURCE_WIRED** — current changing text remains the semantic value.
- Latest Home Center/Adam message TextView: **YES / SOURCE_WIRED** — `OperatorOverlayService.createOverlay()` now leaves `latest` with native changing-text semantics via `setContentDescription(null)`, while `refreshUi()` continues to update the text.
- Existing-owner latest-message source commit: **YES** — `4a48e0e0dbd540291fbb75ca6c8800be58736dab`; authenticated owner blob after surgery: `44d4e273e79f8dc37227651ba11a31842169db18`.
- Existing deterministic accessibility owner probe: **YES / SUPPORTING_SOURCE** — its additive `latestMessageFocus` result uses the same v6 lexical/direct-owner-method evidence contract rather than introducing Probe II.
- Owner-probe latest seam regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `tools/test_try_forever_operator_accessibility_latest_probe.py`.
- Latest-message direct owner-boundary regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `tools/test_try_forever_latest_textview_semantics_owner_boundary.py`; it requires both initialization and refresh ownership plus native TextView semantics.
- Canonical combined existing-owner surgery: **YES / APPLIED_SOURCE** at `patches/try-forever-operator-accessibility-viewport-latest-combined.patch`; the authenticated commit diff matches the intended latest-message semantic change plus the viewport visibility gate.
- Existing-owner latest-message wiring: **YES / SOURCE_WIRED**.
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- current text is set in `createOverlay` and refreshed in `refreshUi`;
- a static/generic non-null description plus dynamic text is a legacy owner shape;
- dynamic text with no non-null description is source-wired at the TextView semantic-value layer;
- null-at-init plus later non-null override fails closed as partial/unsafe;
- missing refresh ownership fails closed as partial/unsafe;
- comment/literal/wrong-method/nested-class markers cannot earn wiring authority;
- source proof does not claim runtime TalkBack behavior.

## Evidence membrane

`requested → semantic policy source → deterministic source probe → regression source → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current state: `requested YES → policy/probe/regression source YES → existing-owner source wiring YES → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.

Never promote a state because a patch or helper exists; this skill was promoted only after authenticated owner mutation plus commit/readback evidence.