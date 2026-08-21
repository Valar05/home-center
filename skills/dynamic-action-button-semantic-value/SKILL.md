# Dynamic Action Button Semantic Value

## Purpose

Keep a native Button's accessibility label synchronized with the action it will perform now, especially when visual text changes among safety-relevant states.

Use this skill when a Button's visible label changes at runtime but source also installs a static or generic `contentDescription`, or when a compact visual label is intentionally too terse to carry the full action semantics.

## Law

1. Accessibility semantics must describe the action that will happen now, not a menu of possible actions.
2. A full-text Button such as `Enable control`, `Disable control`, `Confirm disable`, `Mute speech`, or `Unmute speech` may preserve its current visible text as the semantic label by keeping `contentDescription` null.
3. A compact visual Button may keep terse text such as `STOP`, `ENABLE`, or `CONFIRM`, but its accessibility description must carry the exact full current action.
4. Safety confirmation is a distinct state. `Confirm disable` must not collapse into a generic `Disable or enable` description.
5. Source evidence must include the direct owner refresh/update path where the action label changes, not just initialization.
6. Reuse the existing Java lexical/direct-owner evidence helpers for source-boundary regressions. Comments, literals, wrong methods, and neighboring owners are not wiring proof.
7. Do not create a neighboring accessibility controller. Compose the existing `OperatorOverlayService` owner.
8. Source regression, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
9. Phone/P0 firewall is binding. This skill does not authorize Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.

## Current PR #329 source truth

- Current authenticated owner blob: `44d4e273e79f8dc37227651ba11a31842169db18`.
- `muteButton`: visible text changes between `Mute speech` and `Unmute speech`, but owner still initializes a generic static `Mute or unmute Home Center status speech` description. **OWNER_WIRED NO / LEGACY**.
- `controlButton`: visible text changes among `Enable control`, `Disable control`, and `Confirm disable`, but owner still initializes a generic static `Disable or enable Home Center control` description. **OWNER_WIRED NO / LEGACY**.
- `compactControlButton`: visual text changes among `ENABLE`, `STOP`, and `CONFIRM`; owner still carries a generic static description rather than the exact full current action. **OWNER_WIRED NO / LEGACY**.
- Direct owner-boundary regression: **YES / RED / UNEXECUTED** at `tools/test_try_forever_dynamic_action_button_accessibility_owner_boundary.py`.
- Exact owner surgery: **YES / PROPOSED_NOT_APPLIED** at `patches/try-forever-dynamic-action-button-accessibility-owner.patch`, base-blob locked to `44d4e273e79f8dc37227651ba11a31842169db18`.
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- current visible action text is owned in `refreshUi`;
- full-text dynamic action buttons do not retain generic static content descriptions that can mask the current action;
- compact control semantics equal the exact `fullControlLabel` every refresh;
- `Confirm disable` remains distinct from ordinary disable;
- comments/literals/wrong-method counterfeits cannot earn source authority;
- source proof does not claim runtime TalkBack behavior.

## Evidence membrane

`requested → doctrine → RED owner regression → exact owner surgery → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current state: `requested YES → doctrine/regression/patch source YES → owner wiring NO → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.
