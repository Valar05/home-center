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
5. Deep-detail owner wiring is complete only when policy text projection, pixel-height viewport, vertical scrollability, passive focus/click ownership after movement-method installation, generation-bound post-layout scroll restoration, explicit-selection top reset, and explicit-detail announcement all compose in the existing owner. Helper calls alone are insufficient.
6. Accessibility announcement budgets describe the returned projection, not UTF-16 code units. Do not use `substring(0, N)` as a Unicode safety contract.
7. A patch artifact is proposed source, not owner wiring. A deterministic source probe is evidence about source shape, not TESTED/runtime proof.
8. When multiple independent accessibility wounds overlap the same owner file, prefer one base-blob-locked composed surgery over racing multiple patches. Patch composition still does not equal application.
9. An active Computer Hands lane is not an exact request identity. If the worker is offline, the lane is occupied, and a historical request lookup is missing, do not enqueue duplicate surgery merely to create activity.
10. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are distinct capability states.
11. The P0/phone firewall is binding. No Phone Hands, primary-phone execution, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance may be consumed by this skill.

## Current PR #329 source truth

Authenticated owner readback at the current accessibility checkpoint still contains both independent legacy shapes on owner blob `c266e66a8004623efadab1933de4e429e677c6a5`:

- deep detail: `heartbeatDetail.setMaxLines(5)` plus `heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END)`;
- Spotify explicit receipt announcement: `summary.substring(0, 160)`.

Supporting source now exists at:

- `tools/try_forever_operator_accessibility_owner_probe.py` — v2 deterministic owner-source classification; deep-detail SOURCE_WIRED requires the complete native scroll/focus/announcement lifecycle rather than only helper names;
- `tools/test_try_forever_operator_accessibility_owner_probe.py` — regression source for legacy/wired/partial states, including incomplete deep-detail native lifecycle and mixed Spotify legacy/new budget markers;
- `docs/try-forever/operator-overlay-heartbeat-detail-scroll-wiring.patch` — deep-detail sole-owner surgery provenance;
- `docs/try-forever/operator-overlay-spotify-announcement-budget.patch` — Spotify existing-organ surgery provenance;
- `docs/try-forever/operator-overlay-accessibility-owner-combined.patch` — exact base-blob-locked composed surgery for both independent owner wounds.

Fresh mutation-lane truth in the current heartbeat: `windows-hands-01` is offline; `lane-try-forever-heartbeat-detail` is active; historical request `hands-try-forever-20260818-0100-detail` is not found. Treat that as **OCCUPIED_OR_UNRESOLVED**, not as execution and not as permission to enqueue a duplicate request.

Current capability membrane:

- deterministic source probe: **YES / SUPPORTING_SOURCE**;
- regression source: **YES / UNEXECUTED**;
- deep-detail policy source: **YES**;
- grapheme-safe plain-text budget source: **YES**;
- exact combined owner surgery: **YES / PROPOSED_NOT_APPLIED**;
- deep-detail owner wiring: **NO**;
- Spotify speech-budget owner wiring: **NO**;
- TESTED: **NO**;
- runtime UI / TalkBack: **NO**;
- deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

A pure source-capability probe should prove:

- complete legacy markers classify `LEGACY_OWNER`;
- complete expected existing-organ markers with no legacy markers classify `SOURCE_WIRED`;
- helper-only or mixed/incomplete surgery classifies `PARTIAL_UNSAFE`;
- Spotify old substring plus new budget marker together classifies `PARTIAL_UNSAFE`;
- the probe itself reports no TESTED/runtime/phone capability.

Owner repair review should additionally prove:

- deep-detail setup no longer uses destructive line-count/END truncation and consumes the existing detail policy completely;
- background detail refresh preserves only a still-valid scroll position while explicit selection resets to top;
- movement-method installation does not steal direct keyboard/click ownership from the passive detail well;
- Spotify accessibility announcement uses the grapheme-safe existing plain-text budget rather than UTF-16 substring;
- no second owner/controller is introduced;
- exact remote owner readback is required before changing either owner-wiring state to YES.
