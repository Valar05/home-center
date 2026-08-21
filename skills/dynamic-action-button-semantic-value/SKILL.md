# Dynamic Action Button Semantic Value

## Purpose

Keep a native Button's accessibility label synchronized with the action it will perform now, especially when visual text changes among safety-relevant states.

Use this skill when a Button's visible label changes at runtime but source also assigns a static or generic `contentDescription`, or when a compact visual label is intentionally too terse to carry the full action semantics.

## Law

1. Accessibility semantics must describe the action that will happen now, not a menu of possible actions.
2. A full-text Button such as `Enable control`, `Disable control`, `Confirm disable`, `Mute speech`, or `Unmute speech` may derive semantics from its visible text, but if the owner uses an explicit `contentDescription` it must be synchronized to the exact current action in the same direct refresh path.
3. A compact visual Button may keep terse text such as `STOP`, `ENABLE`, or `CONFIRM`, but its accessibility description must carry the exact full current action.
4. Safety confirmation is a distinct state. `Confirm disable` must not collapse into a generic `Disable or enable` description.
5. Source evidence must include the direct owner refresh/update path where the action label changes, not just initialization.
6. Reuse the existing Java lexical/direct-owner evidence helpers for source-boundary regressions. Comments, literals, wrong methods, and neighboring owners are not wiring proof.
7. Do not create a neighboring accessibility controller. Compose the existing `OperatorOverlayService` owner.
8. When multiple source-ready accessibility repairs target the same owner/base blob, converge them into one base-locked surgery before owner mutation. Independent patch application creates stale-base/partial-state risk.
9. Source regression, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
10. Phone/P0 firewall is binding. This skill does not authorize Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.

## Current PR #329 source truth

- Authenticated owner surgery commit: `a87d21b48eba28433688b40860f9befeb6347278`.
- Current source-wired owner blob from that surgery: `d8cad8c2931c688d0c6fad6f67626fae75e044d1`.
- `muteButton`: `refreshUi()` now synchronizes its `contentDescription` to the exact current `Mute speech` / `Unmute speech` action. **OWNER_WIRED YES / SOURCE**.
- `controlButton`: `refreshUi()` now synchronizes its semantic description to `fullControlLabel`, preserving distinct `Enable control`, `Disable control`, and `Confirm disable`. **OWNER_WIRED YES / SOURCE**.
- `compactControlButton`: visual text remains terse `ENABLE` / `STOP` / `CONFIRM`, while its semantic description now uses the exact full current action via `fullControlLabel`. **OWNER_WIRED YES / SOURCE**.
- Direct owner-boundary regression: **YES / REGRESSION_SOURCE / UNEXECUTED** at `tools/test_try_forever_dynamic_action_button_accessibility_owner_boundary.py`.
- Canonical combined owner surgery provenance: **APPLIED_SOURCE** at `patches/try-forever-operator-interaction-accessibility-owner-combined.patch`.
- Historical standalone dynamic-action patch remains **SUPERSEDED_DO_NOT_APPLY_INDEPENDENTLY**.
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- current visible action text is owned in `refreshUi`;
- `muteButton` semantic description equals its exact current Mute/Unmute action;
- `controlButton` semantic description equals `fullControlLabel` every refresh;
- compact control semantics equal the exact `fullControlLabel` every refresh even while visual text stays `STOP` / `ENABLE` / `CONFIRM`;
- `Confirm disable` remains distinct from ordinary disable;
- comments/literals/wrong-method counterfeits cannot earn source authority;
- source proof does not claim runtime TalkBack behavior.

## Evidence membrane

`requested → doctrine → owner regression source → combined exact owner surgery → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current state: `requested YES → doctrine/regression/combined-owner-source YES → owner wiring YES/SOURCE → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.
