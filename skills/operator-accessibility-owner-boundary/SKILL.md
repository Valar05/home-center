# Operator Accessibility Owner Boundary

## Purpose

Keep accessibility source policy, the existing Android owner, and runtime proof separate. Use this when an accessibility helper/policy exists but `OperatorOverlayService` may still contain an older presentation or speech path.

## Trigger

Use when repository source shows one of these shapes:

- a pure accessibility policy/helper exists but the sole native owner does not consume it;
- the owner mixes legacy and new markers, creating a partial unsafe surgery;
- a returned speech/text budget uses UTF-16 substring/counting while an existing grapheme-safe budget organ already exists;
- a visible/touchable detail surface destructively ellipsizes or line-caps semantic evidence that policy says must remain inspectable;
- a source-capability probe can be fooled by comments, literals, or correct-looking markers placed in the wrong owner method.

## Law

1. `OperatorOverlayService` remains the sole native owner. Do not create a neighboring accessibility controller, renderer, state store, overlay, or phone path.
2. Classify owner source deterministically as `LEGACY_OWNER`, `SOURCE_WIRED`, or `PARTIAL_UNSAFE`; do not infer wiring from helper existence or raw substring presence. Positive evidence must first survive Java lexical filtering and then occur inside the native method that owns the consequence. A marker in comments/literals or in an unrelated method earns no wiring authority.
3. Method-scoped lexical source custody is still source-structure evidence only. It does **not** prove Java control flow, Android execution, focus retention, runtime accessibility behavior, deployment, or phone delivery.
4. Reuse existing organs before inventing helpers. Deep detail composes `HeartbeatDetailSurfacePolicy`; plain returned accessibility speech reuses `HeartbeatPlainTextBudget` when its grapheme-safe/plain-text semantics match the surface.
5. Full explicit Why / Consequence / Evidence / Source detail must stay semantically inspectable. A five-line spatial target is not permission to amputate the TextView layout with `setMaxLines(5)` plus `END` ellipsis.
6. Deep-detail owner wiring is complete only when the existing owner method scopes compose policy text projection, pixel-height viewport, vertical scrollability, passive focus/click ownership after movement-method installation, generation-bound post-layout scroll restoration, explicit-selection top reset, and explicit-detail announcement. Helper calls in another method are counterfeit evidence.
7. Accessibility announcement budgets describe the returned projection, not UTF-16 code units. Do not use `substring(0, N)` as a Unicode safety contract. The Spotify budget marker must live in `handleSpotifyReceipt`, not merely somewhere in the file.
8. A patch artifact is proposed source, not owner wiring. A deterministic source probe is evidence about source shape, not TESTED/runtime proof.
9. When multiple independent accessibility wounds overlap the same owner file, prefer one base-blob-locked composed surgery over racing multiple patches. Patch composition still does not equal application.
10. Retired or unavailable worker machinery is not a reason to create duplicate queue sludge or route through the phone. Use an authorized existing non-phone mutation lane when it can preserve exact owner identity; otherwise stop at the exact boundary.
11. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are distinct capability states.
12. The P0/phone firewall is binding. No Phone Hands, primary-phone execution, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance may be consumed by this skill.

## Current PR #329 source truth

Authenticated owner readback at the current accessibility checkpoint is blob `c266e66a8004623efadab1933de4e429e677c6a5` and still contains both independent legacy owner-method shapes:

- deep detail in `createOverlay`: `heartbeatDetail.setMaxLines(5)` plus `heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END)`;
- Spotify explicit receipt announcement in `handleSpotifyReceipt`: `summary.substring(0, 160)`.

Supporting source now exists at:

- `tools/try_forever_operator_accessibility_owner_probe.py` — v4 deterministic method-scoped owner-source classification. It first blanks Java comments and string/char/text-block literals, then requires each positive marker inside its owning native method;
- `tools/test_try_forever_operator_accessibility_owner_probe.py` — regression source for legacy/wired/partial states, inert-text counterfeits, and the wrong-method counterfeit case where every expected marker exists but cannot earn `SOURCE_WIRED` outside its owner method;
- `docs/try-forever/operator-overlay-heartbeat-detail-scroll-wiring.patch` — deep-detail sole-owner surgery provenance;
- `docs/try-forever/operator-overlay-spotify-announcement-budget.patch` — Spotify existing-organ surgery provenance;
- `docs/try-forever/operator-overlay-accessibility-owner-combined.patch` — exact composed surgery whose declared base owner blob still matches the authenticated current owner blob.

The historical Command Center Codex worker/job/session/worker surface reports itself permanently retired. Do not retry it, manufacture queue state, or substitute the gated phone path. The audited Home Center GitHub-admin lane remains a distinct non-phone repository mutation surface; repository mutation through that lane is still source work, not runtime delivery.

Current capability membrane:

- deterministic source probe: **YES / SUPPORTING_SOURCE**;
- lexical literal/comment exclusion: **YES / SUPPORTING_SOURCE**;
- method-scoped source evidence gate: **YES / SUPPORTING_SOURCE**;
- regression source: **YES / UNEXECUTED**;
- deep-detail policy source: **YES**;
- grapheme-safe plain-text budget source: **YES**;
- exact combined owner surgery: **YES / PROPOSED_NOT_APPLIED**;
- combined surgery base matches authenticated owner blob: **YES / SOURCE READBACK**;
- deep-detail owner wiring: **NO**;
- Spotify speech-budget owner wiring: **NO**;
- Java control-flow proof: **NO**;
- TESTED: **NO**;
- runtime UI / TalkBack: **NO**;
- deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

The source-capability probe should prove:

- complete legacy markers inside their owning Java methods classify `LEGACY_OWNER`;
- complete expected existing-organ markers inside every required owner method, with no owner-method legacy markers, classify `SOURCE_WIRED`;
- helper-only or mixed/incomplete surgery classifies `PARTIAL_UNSAFE`;
- Spotify old substring plus new budget marker together inside `handleSpotifyReceipt` classify `PARTIAL_UNSAFE`;
- comments, block comments, string literals, char literals, and text blocks containing expected markers cannot earn `SOURCE_WIRED`;
- complete expected markers placed in an unrelated method cannot earn `SOURCE_WIRED`;
- legacy markers placed only in an unrelated method do not poison otherwise complete owner-method wiring;
- the probe itself reports method-scoped source custody but no control-flow, TESTED, runtime, or phone capability.

Owner repair review should additionally prove:

- deep-detail setup no longer uses destructive line-count/END truncation and consumes the existing detail policy completely;
- background detail refresh preserves only a still-valid scroll position while explicit selection resets to top;
- movement-method installation does not steal direct keyboard/click ownership from the passive detail well;
- Spotify accessibility announcement uses the grapheme-safe existing plain-text budget rather than UTF-16 substring;
- no second owner/controller is introduced;
- exact remote owner readback is required before changing either owner-wiring state to YES.
