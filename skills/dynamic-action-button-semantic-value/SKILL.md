# Dynamic Action Button Semantic Value

## Purpose

Keep a native Button's accessibility label synchronized with the action it will perform now, especially when visual text changes among safety-relevant states.

Use this skill when a Button's visible label changes at runtime but source also installs a static or generic `contentDescription`, or when a compact visual label is intentionally too terse to carry the full action semantics.

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

- Current authenticated owner blob: `44d4e273e79f8dc37227651ba11a31842169db18`.
- `muteButton`: visible text changes between `Mute speech` and `Unmute speech`, but owner still initializes a generic static `Mute or unmute Home Center status speech` description and does not refresh that semantic description. **OWNER_WIRED NO / LEGACY**.
- `controlButton`: visible text changes among `Enable control`, `Disable control`, and `Confirm disable`, but owner still initializes a generic static `Disable or enable Home Center control` description and does not refresh it. **OWNER_WIRED NO / LEGACY**.
- `compactControlButton`: visual text changes among `ENABLE`, `STOP`, and `CONFIRM`; owner still carries a generic static description rather than the exact full current action. **OWNER_WIRED NO / LEGACY**.
- Selected repair: refresh `muteButton` description to the exact current Mute/Unmute text, refresh `controlButton` description to `fullControlLabel`, and refresh `compactControlButton` description to the same exact `fullControlLabel` while keeping its terse visual text.
- Direct owner-boundary regression: **YES / RED / UNEXECUTED** at `tools/test_try_forever_dynamic_action_button_accessibility_owner_boundary.py`.
- Canonical same-owner surgery: **YES / PROPOSED_NOT_APPLIED** at `patches/try-forever-operator-interaction-accessibility-owner-combined.patch`, base-blob locked to `44d4e273e79f8dc37227651ba11a31842169db18` and composed with latest-message interaction semantics.
- Historical standalone dynamic-action patch: **SUPERSEDED_DO_NOT_APPLY_INDEPENDENTLY**.
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

`requested → doctrine → RED owner regression → combined exact owner surgery → existing-owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`

Current state: `requested YES → doctrine/regression/combined-patch source YES → owner wiring NO → regression executed NO → tested/runtime/deployed/delivered/accepted NO`.
