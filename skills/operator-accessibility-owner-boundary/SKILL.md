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
8. For non-interactive dynamic `TextView` status surfaces, prefer the framework's native text semantics. A non-null `contentDescription` that replaces changing Spotify or Home Center status text is stale/duplicated semantics.
9. A changing interactive TextView keeps the changing text as semantic value while exposing action/state separately. Label the standard click action; on API 30+ use semantic `stateDescription`. Do not reintroduce `announceForAccessibility` merely to confirm a simple expand/collapse action.
10. A dynamic Button's semantic label must describe the action that will happen now. Safety-critical states such as `Confirm disable` cannot remain behind a generic `Disable or enable` description. Compact visual text may stay terse only when the accessibility label carries the exact full action.
11. A patch artifact is proposed source until authenticated owner mutation/readback proves application. After that point, mark it `APPLIED_SOURCE`; neither state is TESTED/runtime proof.
12. When multiple independent accessibility wounds overlap the same owner file/base blob, prefer one base-blob-locked composed surgery over racing multiple patches.
13. Retired or unavailable worker machinery is not a reason to create duplicate queue sludge or route through the phone. Use an authorized existing non-phone mutation lane when it can preserve exact owner identity; otherwise stop at the exact boundary.
14. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are distinct capability states.
15. The P0/phone firewall is binding. No Phone Hands, primary-phone execution, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance may be consumed by this skill.
16. Supporting-policy safety must never green-paint its consumer. If a helper is bounded but the native method performs whole-source work before calling it, the owner seam remains `LEGACY_OWNER` or `PARTIAL_UNSAFE` until direct-owner ordering proves otherwise.
17. Deterministic evidence must prove ordering when ordering is the capability. Correct helper names in comments/literals, or a helper call placed after the unsafe operation, are not owner wiring.

## Current PR #329 source truth — 2026-08-27 22:58 CT

Authenticated current branch readback reports `OperatorOverlayService` blob `2935243f136359e3489a89108406e888b0ec2911`. The former `44d4e273...` current-owner claim was stale doctrine and is retired as current-head evidence.

Current owner source retains the previously applied generic accessibility repairs:

- deep detail composes `HeartbeatDetailSurfacePolicy`, a bounded pixel-height viewport, vertical scrolling, passive focus/click ownership, generation-bound post-layout scroll restoration, explicit-selection top reset, and current detail semantics;
- Spotify receipt speech uses `HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160)` instead of UTF-16 substring;
- Spotify dynamic status keeps changing TextView text as semantic value with `contentDescription=null`;
- Home Center dynamic status likewise keeps current TextView text as semantic value with `contentDescription=null`;
- latest-message interaction semantics are **SOURCE_WIRED**: the changing message text remains value, ACTION_CLICK has a policy label, and API-30+ `stateDescription` tracks expanded/collapsed state;
- dynamic mute/full/compact control semantics are **SOURCE_WIRED**: `refreshUi()` synchronizes content descriptions to the exact current action, including `Confirm disable`.

`patches/try-forever-operator-interaction-accessibility-owner-combined.patch` is **APPLIED_SOURCE / DO_NOT_APPLY** provenance. It records base blob `44d4e273...`, applied commit `a87d21b48eba28433688b40860f9befeb6347278`, and result blob `d8cad8c2931c688d0c6fad6f67626fae75e044d1`; later owner evolution does not turn that applied provenance back into a pending patch.

The currently open Adam owner seams are governed by `adam-mode-accessibility`, not by creating another generic accessibility owner:

- Adam state request owner: **SOURCE_WIRED**;
- Adam UI request admission: **NO / PROPOSED_NOT_APPLIED** on current owner blob `2935243f...`;
- Adam native mode/input/result/action accessibility owner: **REBASED_PROPOSED_NOT_APPLIED** on current owner blob `2935243f...`;
- `tools/try_forever_adam_accessibility_owner_probe.py` schema v6 now has an independent `requestAdmission` evidence seam; source exists, execution remains **NO**.

Current capability membrane:

- deterministic source probes: **YES / SUPPORTING_SOURCE**;
- lexical literal/comment exclusion and direct-owner-method evidence gates: **YES / SUPPORTING_SOURCE**;
- generic deep-detail/status/latest-message/dynamic-action repairs: **YES / SOURCE_WIRED**;
- Adam UI request owner: **NO / PROPOSED_NOT_APPLIED**;
- Adam native accessibility owner: **NO / REBASED_PROPOSED_NOT_APPLIED**;
- regression source: **YES / UNEXECUTED**;
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
- an ordering-sensitive seam remains unsafe when the policy appears only after the unsafe whole-source operation;
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
- exact remote owner readback is required before changing any remaining owner-wiring state to YES;
- passing source checks still does not prove Android runtime rendering or TalkBack behavior.

## Evidence membrane

`requested → policy/doctrine → RED owner regression → exact existing-owner surgery → authenticated owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`
