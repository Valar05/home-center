# Operator Accessibility Owner Boundary

## Purpose

Keep accessibility source policy, the existing Android owner, and runtime proof separate. Use this when an accessibility helper/policy exists but `OperatorOverlayService` may still contain an older presentation or speech path.

## Trigger

Use when repository source shows one of these shapes:

- a pure accessibility policy/helper exists but the sole native owner does not consume it;
- the owner mixes legacy and new markers, creating a partial unsafe surgery;
- a returned speech/text budget uses UTF-16 substring/counting while an existing grapheme-safe budget organ already exists;
- a visible/touchable detail surface destructively ellipsizes or line-caps semantic evidence that policy says must remain inspectable.

## Law

1. `OperatorOverlayService` remains the sole native owner. Do not create a neighboring accessibility controller, renderer, state store, overlay, or phone path.
2. Classify owner source deterministically as `LEGACY_OWNER`, `SOURCE_WIRED`, or `PARTIAL_UNSAFE`; do not infer wiring from helper existence.
3. Reuse existing organs before inventing helpers. For this branch, deep detail composes `HeartbeatDetailSurfacePolicy`; plain returned accessibility speech may reuse `HeartbeatPlainTextBudget` when its grapheme-safe/plain-text semantics match the surface.
4. Full explicit Why / Consequence / Evidence / Source detail must stay semantically inspectable. A five-line spatial target is not permission to amputate the TextView layout with `setMaxLines(5)` plus `END` ellipsis.
5. Accessibility announcement budgets describe the returned projection, not UTF-16 code units. Do not use `substring(0, N)` as a Unicode safety contract.
6. A patch artifact is proposed source, not owner wiring. A deterministic source probe is evidence about source shape, not TESTED/runtime proof.
7. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are distinct capability states.
8. The P0/phone firewall is binding. No Phone Hands, primary-phone execution, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance may be consumed by this skill.

## Current PR #329 source truth

Authenticated owner readback at the 1200 checkpoint still contains both independent legacy shapes:

- deep detail: `heartbeatDetail.setMaxLines(5)` plus `heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END)`;
- Spotify explicit receipt announcement: `summary.substring(0, 160)`.

Supporting source now exists at:

- `tools/try_forever_operator_accessibility_owner_probe.py` — deterministic owner-source classification;
- `tools/test_try_forever_operator_accessibility_owner_probe.py` — pure regression source for legacy/wired/partial states;
- `docs/try-forever/operator-overlay-heartbeat-detail-scroll-wiring.patch` — existing deep-detail owner surgery provenance;
- `docs/try-forever/operator-overlay-spotify-announcement-budget.patch` — existing-organ Spotify announcement surgery provenance.

Current capability membrane:

- deterministic source probe: **YES / SUPPORTING_SOURCE**;
- regression source: **YES / UNEXECUTED**;
- deep-detail policy source: **YES**;
- grapheme-safe plain-text budget source: **YES**;
- deep-detail owner wiring: **NO**;
- Spotify speech-budget owner wiring: **NO**;
- TESTED: **NO**;
- runtime UI / TalkBack: **NO**;
- deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

A pure source-capability probe should prove:

- complete legacy markers classify `LEGACY_OWNER`;
- complete expected existing-organ markers with no legacy markers classify `SOURCE_WIRED`;
- mixed or incomplete surgery classifies `PARTIAL_UNSAFE`;
- the probe itself reports no TESTED/runtime/phone capability.

Owner repair review should additionally prove:

- deep-detail setup no longer uses destructive line-count/END truncation and consumes the existing detail policy completely;
- Spotify accessibility announcement uses the grapheme-safe existing plain-text budget rather than UTF-16 substring;
- no second owner/controller is introduced;
- exact remote owner readback is required before changing either owner-wiring state to YES.
