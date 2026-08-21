# Operator Accessibility Owner Boundary

## Purpose

Keep accessibility source policy, the existing Android owner, and runtime proof separate. Use this when an accessibility helper/policy exists, when `OperatorOverlayService` may still contain an older presentation or speech path, or when source wiring has landed but regression/runtime evidence has not.

## Trigger

Use when repository source shows one of these shapes:

- a pure accessibility policy/helper exists but the sole native owner does not consume it;
- the owner mixes legacy and new markers, creating a partial unsafe surgery;
- a returned speech/text budget uses UTF-16 substring/counting while an existing grapheme-safe budget organ already exists;
- a visible/touchable detail surface destructively ellipsizes or line-caps semantic evidence that policy says must remain inspectable;
- a source-capability probe can be fooled by comments, literals, correct-looking markers placed in the wrong owner method, or identically named methods inside a nested class;
- a dynamic non-interactive `TextView` carries a static or otherwise non-null `contentDescription` that replaces the current visible text as its accessibility semantic value;
- a changing interactive TextView preserves value semantics but lacks explicit action/state semantics;
- a dynamic Button changes the action it will perform while its accessibility label remains static/generic;
- source wiring exists but TESTED/runtime/TalkBack/deployment evidence is still absent.

## Law

1. `OperatorOverlayService` remains the sole native owner. Do not create a neighboring accessibility controller, renderer, state store, overlay, or phone path.
2. Classify owner source deterministically as `LEGACY_OWNER`, `SOURCE_WIRED`, or `PARTIAL_UNSAFE`; do not infer wiring from helper existence or raw substring presence. Positive evidence must first survive Java lexical filtering, then be scoped to the named `OperatorOverlayService` class, then occur inside a direct native member method that owns the consequence. A marker in comments/literals, an unrelated method, or an identically named nested-class method earns no wiring authority.
3. Direct-owner-method lexical source custody is still source-structure evidence only. It does **not** prove Java control flow, Android execution, focus retention, runtime accessibility behavior, deployment, or phone delivery.
4. Reuse existing organs before inventing helpers. Deep detail composes `HeartbeatDetailSurfacePolicy`; plain returned accessibility speech reuses `HeartbeatPlainTextBudget` when its grapheme-safe/plain-text semantics match the surface.
5. Full explicit Why / Consequence / Evidence / Source detail must stay semantically inspectable. A five-line spatial target is not permission to amputate the TextView layout with `setMaxLines(5)` plus `END` ellipsis.
6. Deep-detail owner wiring is complete only when the existing owner method scopes compose policy text projection, pixel-height viewport, vertical scrollability, passive focus/click ownership after movement-method installation, generation-bound post-layout scroll restoration, explicit-selection top reset, and explicit-detail semantics. Helper calls in another method or nested class are counterfeit evidence.
7. Accessibility text budgets describe the returned projection, not UTF-16 code units. Do not use `substring(0, N)` as a Unicode safety contract. A speech-budget marker must live in the direct method that owns the speech consequence, not merely somewhere in the file.
8. For non-interactive dynamic `TextView` status surfaces, prefer the framework's native text semantics. Android accessibility guidance says TextView text is already announced; a non-null `contentDescription` that replaces changing Spotify or Home Center status text is stale/duplicated semantics.
9. A changing interactive TextView keeps the changing text as semantic value while exposing action/state separately. Label the standard click action; on API 30+ use semantic `stateDescription`. Do not reintroduce `announceForAccessibility` merely to confirm a simple expand/collapse action; Android 16 / API 36 deprecates announcement APIs in favor of semantic UI state.
10. A dynamic Button's semantic label must describe the action that will happen now. Safety-critical states such as `Confirm disable` cannot remain behind a generic `Disable or enable` description. Compact visual text may stay terse only when the accessibility label carries the exact full action.
11. A patch artifact is proposed source until authenticated owner mutation/readback proves application. After that point, mark it `APPLIED_SOURCE`; neither state is TESTED/runtime proof.
12. When multiple independent accessibility wounds overlap the same owner file/base blob, prefer one base-blob-locked composed surgery over racing multiple patches.
13. Retired or unavailable worker machinery is not a reason to create duplicate queue sludge or route through the phone. Use an authorized existing non-phone mutation lane when it can preserve exact owner identity; otherwise stop at the exact boundary.
14. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are distinct capability states.
15. The P0/phone firewall is binding. No Phone Hands, primary-phone execution, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance may be consumed by this skill.

## Current PR #329 source truth

Authenticated **current branch** readback now reports `OperatorOverlayService` blob `44d4e273e79f8dc37227651ba11a31842169db18`. Historical owner commit `aafece5e8e1d8d2631ade85ba9c1bec3e4e6089f` / blob `5dc7f2f52db7e2b7cff867ee6b82cc1492e1b835` remains valid provenance for an earlier four-wound surgery, but it is **not** the current owner blob and must not be presented as current-head custody.

Current owner source still contains those four completed repairs:

- deep detail composes `HeartbeatDetailSurfacePolicy`, a bounded pixel-height viewport, vertical scrolling, passive focus/click ownership, generation-bound post-layout scroll restoration, explicit-selection top reset, and current detail semantics;
- Spotify receipt speech uses `HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160)` instead of UTF-16 substring;
- Spotify dynamic status keeps its changing TextView text as semantic value with `contentDescription=null`;
- Home Center dynamic status likewise keeps current TextView text as semantic value with `contentDescription=null`.

Two additional owner seams remain deliberately unwired at current blob `44d4e273...`:

- **latest-message interaction semantics — OWNER_WIRED NO / LEGACY:** changing message text is correctly native semantic value, but the clickable TextView still lacks a labeled standard click action and expanded/collapsed state description;
- **dynamic action-button semantics — OWNER_WIRED NO / LEGACY:** `muteButton`, `controlButton`, and `compactControlButton` change their real current actions in `refreshUi()` while static generic content descriptions remain.

Current supporting source for those two seams:

- `LatestMessageAccessibilityPolicy` now owns labeled click action + expanded/collapsed state only; it explicitly avoids deprecated simple-action confirmation announcements;
- latest policy + direct-owner RED regression: **YES / UNEXECUTED**;
- dynamic action direct-owner RED regression: **YES / UNEXECUTED**;
- `patches/try-forever-operator-interaction-accessibility-owner-combined.patch`: **YES / PROPOSED_NOT_APPLIED**, base-blob locked to `44d4e273...`, composing both seams in one surgery;
- the former standalone latest-message and dynamic-action patches are **SUPERSEDED_DO_NOT_APPLY_INDEPENDENTLY** because they target the same owner/base and could create stale-base partial state.

Current capability membrane:

- deterministic source probe: **YES / SUPPORTING_SOURCE**;
- lexical literal/comment exclusion: **YES / SUPPORTING_SOURCE**;
- named owner-class + direct owner-method evidence gates: **YES / SUPPORTING_SOURCE**;
- regression source for historical/current accessibility seams: **YES / UNEXECUTED**;
- deep-detail owner wiring: **YES / SOURCE_WIRED**;
- Spotify speech-budget owner wiring: **YES / SOURCE_WIRED**;
- Spotify native TextView focused-status owner wiring: **YES / SOURCE_WIRED**;
- Home Center native TextView dynamic-status owner wiring: **YES / SOURCE_WIRED**;
- latest-message value semantics: **YES / SOURCE_WIRED**;
- latest-message interaction action/state: **NO / OWNER_UNWIRED**;
- dynamic action-button exact current action semantics: **NO / OWNER_UNWIRED**;
- combined exact owner surgery: **YES / PROPOSED_NOT_APPLIED**;
- Java control-flow proof: **NO**;
- TESTED: **NO**;
- runtime UI / TalkBack: **NO**;
- deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

Source-capability evidence should prove:

- complete legacy markers inside their direct owning Java methods classify `LEGACY_OWNER`;
- complete expected existing-organ markers inside every required direct owner method, with no owner-method legacy markers, classify `SOURCE_WIRED`;
- helper-only or mixed/incomplete surgery classifies `PARTIAL_UNSAFE`;
- comments, block comments, string literals, char literals, text blocks, unrelated methods, and identically named nested-class methods cannot earn wiring authority;
- a missing named `OperatorOverlayService` class fails closed;
- the probe itself reports source custody but no control-flow, TESTED, runtime, or phone capability.

Owner repair review should additionally prove:

- deep detail stays full and inspectable through the existing policy rather than destructive line-count/END truncation;
- background detail refresh preserves only a still-valid scroll position while explicit selection resets to top;
- movement-method installation does not steal direct keyboard/click ownership from the passive detail well;
- Spotify receipt speech remains grapheme-safe through the existing plain-text budget;
- Spotify and Home Center non-interactive status TextViews expose changing text without non-null semantic overrides;
- latest-message TextView keeps changing text as value, labels ACTION_CLICK, exposes API-30+ stateDescription, and does not use deprecated explicit confirmation announcement;
- mute/full/compact control semantics track the exact current action on every refresh, with `Confirm disable` distinct;
- no second owner/controller is introduced;
- exact remote owner readback is required before changing either remaining owner-wiring state to YES;
- passing source checks still does not prove Android runtime rendering or TalkBack behavior.

## Evidence membrane

`requested → policy/doctrine → RED owner regression → exact combined owner surgery → authenticated existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`
