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
6. For the current `OperatorOverlayService` contract, the semantic writes are direct `refreshUi()` statements after action labels are computed. Regression evidence must not accept equivalent marker text buried in nested/unreachable branches as proof of that direct refresh contract.
7. Reuse the existing Java lexical/direct-owner evidence helpers. Comments, literals, wrong methods, neighboring owners, and nested counterfeit branches are not wiring proof.
8. Source structure is not Java execution proof. Even a direct-method green fixture remains `REGRESSION_SOURCE`; it does not prove Android execution, runtime TalkBack behavior, deployment, or phone delivery.
9. Do not create a neighboring accessibility controller. Compose the existing `OperatorOverlayService` owner.
10. Source regression, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
11. Phone/P0 firewall is binding. This skill does not authorize Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.

## Current PR #329 source truth — authenticated 2026-08-21

Authenticated owner blob on current PR head at review time: `c5de1411a6b68087ae17aff83c032af754587150`.

The owner source already contains the three exact dynamic-action semantic writes in direct `refreshUi()` statements:

- `muteButton`: visible and semantic action both track `Mute speech` / `Unmute speech`.
- `controlButton`: semantic action tracks `fullControlLabel`, preserving `Enable control`, `Disable control`, and the separate safety state `Confirm disable`.
- `compactControlButton`: visual text remains terse `ENABLE` / `STOP` / `CONFIRM`, while semantic description uses the exact full `fullControlLabel` action.

`createOverlay()` ends by calling `refreshUi()` synchronously, so the generic construction-time descriptions are not a separately established first-frame accessibility defect. Do not manufacture that wound merely because the initialization strings are generic.

Historical commit/blob identifiers from other source slices are provenance, not current-owner authority. Current capability is derived from authenticated current-head owner readback plus the bounded regression source.

Direct owner-boundary regression: `tools/test_try_forever_dynamic_action_button_accessibility_owner_boundary.py` is **REGRESSION_SOURCE / UNEXECUTED**. It now checks the direct method-body surface and includes a nested impossible-branch counterfeit so marker presence alone cannot satisfy the current direct-refresh contract.

## Regression doctrine

At minimum prove:

- current visible action text is owned in `refreshUi`;
- `muteButton` semantic description equals its exact current Mute/Unmute action;
- `controlButton` semantic description equals `fullControlLabel` every refresh;
- compact control semantics equal the exact `fullControlLabel` every refresh even while visual text stays `STOP` / `ENABLE` / `CONFIRM`;
- the owner still has a distinct `Confirm disable` branch;
- comments/literals/wrong-method/nested counterfeit writes cannot earn source authority;
- source proof does not claim Android control flow, runtime TalkBack behavior, or deployment.

## Evidence membrane

`requested → doctrine → owner regression source → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current state: `requested YES → doctrine/regression YES → owner wiring YES/SOURCE → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.
