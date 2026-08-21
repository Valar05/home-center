# Nonsemantic Overlay Layer Accessibility

## Purpose

Keep technical full-screen interception layers out of the accessibility semantic tree while preserving operator-visible status on real UI surfaces.

Use this skill for transparent/technical overlay views whose job is pointer interception, hit blocking, drag capture, or layout plumbing rather than conveying state or accepting a meaningful accessibility action.

## Law

1. A technical interception layer is not operator content merely because it is a `View`.
2. Do not give a full-screen technical guard a semantic `contentDescription` such as "Remote input active". That creates a giant false accessibility target and can outlive the technical condition it describes.
3. Mark the technical layer `IMPORTANT_FOR_ACCESSIBILITY_NO` and keep its content description null.
4. Preserve the actual state on existing semantic owners such as status text, screen badges, collapsed-owner text, or real controls. Do not delete useful state to make the guard quiet.
5. Touchability/focusability flags and accessibility importance are separate contracts. `FLAG_NOT_TOUCHABLE` does not prove a view is absent from accessibility semantics.
6. Reuse the existing overlay owner. Do not create a second accessibility controller or alternate input guard.
7. Source policy, owner wiring, regression execution, Android runtime, TalkBack behavior, deployment, phone delivery, and acceptance remain separate states.
8. P0/phone firewall is binding. This skill owns no Phone Hands, recovery, Nightcore, Pocket TTS, Chromium, Context Organ, or physical-acceptance action.

## Current PR #329 source truth

- Supporting policy: **YES / SOURCE** at `TechnicalTouchGuardAccessibilityPolicy`.
- Policy regression: **YES / SOURCE / UNEXECUTED** at `TechnicalTouchGuardAccessibilityPolicyTest`.
- Existing-owner RED boundary: **YES / SOURCE / UNEXECUTED** at `tools/test_try_forever_touch_guard_accessibility_owner_boundary.py`.
- Exact owner patch provenance: **YES / PROPOSED_NOT_APPLIED** at `patches/try-forever-touch-guard-accessibility-owner.patch`.
- Current `OperatorOverlayService.createOverlay()` still assigns `touchGuard.setContentDescription("Remote input active")`: **YES / LEGACY OWNER**.
- Existing-owner policy consumption: **NO**.
- TESTED / runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Acceptance

Source-level promotion requires all of:

- the sole `OperatorOverlayService` owner calls `TechnicalTouchGuardAccessibilityPolicy.importantForAccessibility()`;
- the guard has no semantic content description;
- current operator state remains available on the existing semantic status surfaces;
- no neighboring overlay/input/accessibility owner is introduced;
- deterministic owner-boundary regression source is updated from RED only after authenticated owner readback.

Runtime promotion requires separate Android/TalkBack evidence. Source inspection is not runtime proof.
