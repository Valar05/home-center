# Operator Accessibility Owner Boundary

## Purpose

Keep accessibility source policy, the existing Android owner, and runtime proof separate. Use this when an accessibility helper/policy exists but `OperatorOverlayService` may still contain an older presentation or speech path.

## Trigger

Use when repository source shows one of these shapes:

- a pure accessibility policy/helper exists but the sole native owner does not consume it;
- the owner mixes legacy and new markers, creating a partial unsafe surgery;
- a returned speech/text budget uses UTF-16 substring/counting while an existing grapheme-safe budget organ already exists;
- a visible/touchable detail surface destructively ellipsizes or line-caps semantic evidence that policy says must remain inspectable;
- a source-capability probe can be fooled by comments, literals, correct-looking markers placed in the wrong owner method, or identically named methods inside a nested class;
- a dynamic non-interactive `TextView` carries a static or otherwise non-null `contentDescription` that replaces the current visible text as its accessibility semantic value.

## Law

1. `OperatorOverlayService` remains the sole native owner. Do not create a neighboring accessibility controller, renderer, state store, overlay, or phone path.
2. Classify owner source deterministically as `LEGACY_OWNER`, `SOURCE_WIRED`, or `PARTIAL_UNSAFE`; do not infer wiring from helper existence or raw substring presence. Positive evidence must first survive Java lexical filtering, then be scoped to the named `OperatorOverlayService` class, then occur inside a direct native member method that owns the consequence. A marker in comments/literals, an unrelated method, or an identically named nested-class method earns no wiring authority.
3. Direct-owner-method lexical source custody is still source-structure evidence only. It does **not** prove Java control flow, Android execution, focus retention, runtime accessibility behavior, deployment, or phone delivery.
4. Reuse existing organs before inventing helpers. Deep detail composes `HeartbeatDetailSurfacePolicy`; plain returned accessibility speech reuses `HeartbeatPlainTextBudget` when its grapheme-safe/plain-text semantics match the surface.
5. Full explicit Why / Consequence / Evidence / Source detail must stay semantically inspectable. A five-line spatial target is not permission to amputate the TextView layout with `setMaxLines(5)` plus `END` ellipsis.
6. Deep-detail owner wiring is complete only when the existing owner method scopes compose policy text projection, pixel-height viewport, vertical scrollability, passive focus/click ownership after movement-method installation, generation-bound post-layout scroll restoration, explicit-selection top reset, and explicit-detail announcement. Helper calls in another method or nested class are counterfeit evidence.
7. Accessibility announcement budgets describe the returned projection, not UTF-16 code units. Do not use `substring(0, N)` as a Unicode safety contract. The Spotify budget marker must live in `handleSpotifyReceipt`, not merely somewhere in the file.
8. For non-interactive dynamic `TextView` status surfaces, prefer the framework's native text semantics. Android accessibility guidance explicitly says not to provide descriptions for `TextView` elements because accessibility services announce the text itself. A non-null `contentDescription` that replaces changing Spotify or Home Center status text is source-level stale/duplicated semantics, even when the description is dynamically rebuilt. Explicit event announcements remain a separate surface and may use the existing grapheme-safe plain-text budget.
9. Spotify focused-status source wiring requires current text at initialization and receipt update plus no non-null `contentDescription` override. An explicit `setContentDescription(null)` is acceptable source evidence of intentional native TextView semantics but is not required if no override exists.
10. Home Center connection/control status source wiring requires current status text at initialization and `refreshUi` plus no non-null `contentDescription` override. Generic text such as `"Home Center connection and control state"` must not replace the actual current status value.
11. A patch artifact is proposed source, not owner wiring. A deterministic source probe is evidence about source shape, not TESTED/runtime proof.
12. When multiple independent accessibility wounds overlap the same owner file, prefer one base-blob-locked composed surgery over racing multiple patches. Patch composition still does not equal application.
13. Retired or unavailable worker machinery is not a reason to create duplicate queue sludge or route through the phone. Use an authorized existing non-phone mutation lane when it can preserve exact owner identity; otherwise stop at the exact boundary.
14. Source wiring, regression-source existence, regression execution, Android runtime UI, TalkBack behavior, deployment, phone delivery, and acceptance are distinct capability states.
15. The P0/phone firewall is binding. No Phone Hands, primary-phone execution, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance may be consumed by this skill.

## Current PR #329 source truth

Authenticated owner readback at this checkpoint is blob `c266e66a8004623efadab1933de4e429e677c6a5` and still contains four independent legacy source shapes:

- deep detail in `createOverlay`: `heartbeatDetail.setMaxLines(5)` plus `heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END)`;
- Spotify explicit receipt announcement in `handleSpotifyReceipt`: `summary.substring(0, 160)`;
- Spotify status in `createOverlay`: changing visible summary text is paired with static `spotifyStatus.setContentDescription("Current Spotify playback status")`;
- Home Center status in `createOverlay`: changing `status` text is paired with static `status.setContentDescription("Home Center connection and control state")` while `refreshUi` later updates only the visible text.

Supporting source now exists at:

- `tools/try_forever_operator_accessibility_owner_probe.py` — v6 deterministic direct-owner-method source classification. It blanks Java comments and string/char/text-block literals, isolates the named public `OperatorOverlayService` class, only accepts markers inside direct private-void owner members, and separately classifies dynamic TextView semantics by requiring current text ownership with no non-null content-description override;
- `tools/test_try_forever_operator_accessibility_owner_probe.py` — regression source for legacy/wired/partial states, inert-text counterfeits, wrong-method counterfeits, nested-class method counterfeits, missing owner class, mixed null/non-null description state, Spotify native TextView focus semantics, and Home Center status semantics;
- `docs/try-forever/operator-overlay-heartbeat-detail-scroll-wiring.patch` — deep-detail sole-owner surgery provenance;
- `docs/try-forever/operator-overlay-spotify-announcement-budget.patch` — Spotify existing-organ announcement surgery provenance;
- `docs/try-forever/operator-overlay-accessibility-owner-combined.patch` — exact composed four-wound surgery whose declared base owner blob still matches authenticated current owner source. The corrected patch uses native TextView text semantics for dynamic Spotify/Home Center status instead of duplicating text into `contentDescription`.

Fresh Android platform guidance supporting the correction:

- Android Developers, “Make apps more accessible (Views)”: do not provide descriptions for `TextView` elements; accessibility services automatically announce the text itself.
- This guidance changes the earlier proposed Spotify repair: dynamically rebuilding a duplicate `contentDescription` is not required merely to keep focused status current.

Current capability membrane:

- deterministic source probe: **YES / SUPPORTING_SOURCE**;
- lexical literal/comment exclusion: **YES / SUPPORTING_SOURCE**;
- named owner-class source gate: **YES / SUPPORTING_SOURCE**;
- direct owner-method source evidence gate: **YES / SUPPORTING_SOURCE**;
- nested-class counterfeit exclusion: **YES / SUPPORTING_SOURCE**;
- dynamic TextView native-semantics source gate: **YES / SUPPORTING_SOURCE**;
- regression source: **YES / UNEXECUTED**;
- deep-detail policy source: **YES**;
- grapheme-safe plain-text budget source: **YES**;
- corrected combined four-wound owner surgery: **YES / PROPOSED_NOT_APPLIED**;
- combined surgery base matches authenticated owner blob: **YES / SOURCE READBACK**;
- deep-detail owner wiring: **NO**;
- Spotify speech-budget owner wiring: **NO**;
- Spotify native TextView focused-status owner wiring: **NO**;
- Home Center native TextView dynamic-status owner wiring: **NO**;
- Java control-flow proof: **NO**;
- TESTED: **NO**;
- runtime UI / TalkBack: **NO**;
- deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

The source-capability probe should prove:

- complete legacy markers inside their direct owning Java methods classify `LEGACY_OWNER`;
- complete expected existing-organ markers inside every required direct owner method, with no owner-method legacy markers, classify `SOURCE_WIRED`;
- helper-only or mixed/incomplete surgery classifies `PARTIAL_UNSAFE`;
- Spotify old substring plus new budget marker together inside `handleSpotifyReceipt` classify `PARTIAL_UNSAFE`;
- Spotify changing text plus a non-null content-description override remains a separate legacy seam even when the explicit announcement budget is repaired;
- Spotify current text with no non-null content-description override classifies native TextView semantics as `SOURCE_WIRED` at source level;
- a null Spotify description plus a later dynamic non-null override fails closed as `PARTIAL_UNSAFE`;
- Home Center changing status text plus a generic static content description classifies `LEGACY_OWNER`;
- Home Center status with current text and no non-null description override classifies `SOURCE_WIRED` at source level;
- comments, block comments, string literals, char literals, and text blocks containing expected markers cannot earn `SOURCE_WIRED`;
- complete expected markers placed in an unrelated method cannot earn `SOURCE_WIRED`;
- complete expected markers placed inside identically named methods of a nested class cannot earn `SOURCE_WIRED`;
- legacy markers placed only in an unrelated method do not poison otherwise complete direct owner-method wiring;
- a missing named `OperatorOverlayService` class fails closed;
- the probe itself reports direct-owner-method source custody and native TextView semantics source inspection but no control-flow, TESTED, runtime, or phone capability.

Owner repair review should additionally prove:

- deep-detail setup no longer uses destructive line-count/END truncation and consumes the existing detail policy completely;
- background detail refresh preserves only a still-valid scroll position while explicit selection resets to top;
- movement-method installation does not steal direct keyboard/click ownership from the passive detail well;
- Spotify accessibility announcement uses the grapheme-safe existing plain-text budget rather than UTF-16 substring;
- Spotify and Home Center non-interactive status TextViews expose their changing text directly without non-null content-description overrides;
- no second owner/controller is introduced;
- exact remote owner readback is required before changing any owner-wiring state to YES.
