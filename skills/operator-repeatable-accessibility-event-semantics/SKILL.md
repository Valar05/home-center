# Operator Repeatable Accessibility Event Semantics

## Purpose

Prevent deprecated announcement migration from replacing useful semantics with a fake event cannon. Repeated explicit actions must remain understandable, but **not every repeated press requires a repeated synthetic spoken confirmation**.

This skill is repository/source accessibility doctrine only. It owns no Android View, controller, renderer, phone execution, P0 recovery, deployment, delivery, or acceptance lane.

## Core distinction

A live region is a semantic **value-change** surface. A native control already exposes an **action**. A persistent selected/result surface exposes the **resulting state**.

If an explicit action repeats while the steady-state value is identical, do not manufacture freshness with counters, timestamps, punctuation, zero-width text, opaque IDs, focus theft, or global announcement events merely to prove that the user pressed the button.

The exact replacement question is instead:

`Is the action self-describing, and is any meaningful changed result persistently inspectable?`

When yes, a same-value repeat may correctly stay quiet.

## Current TRY FOREVER semantic designs

1. **Spotify explicit command receipt — design ready / owner unwired.**
   - The Spotify command button already names the action.
   - `spotifyStatus` is the native changing result value.
   - For an explicit command, a polite live region is allowed only when the result value actually changes.
   - Repeating Status against the same playback state stays quiet by design; no fake receipt sequence is created.
   - Startup/background status refresh must not inherit the explicit-action live-region gate.

2. **Heartbeat explicit detail selection — design ready / owner unwired.**
   - The heartbeat light Button owns the selection action and semantic identity.
   - The selected state plus the persistent full Why/Consequence/Evidence/Source detail is the receipt.
   - Selecting the same light twice may correctly remain quiet; the second press does not create a new semantic fact.
   - The passive detail well remains passive. No programmatic focus transfer is introduced merely to obtain speech.

3. **Adam send confirmation — design ready / owner unwired.**
   - The Send button action must identify the currently selected Adam mode.
   - The input/result surface already clears the submitted text and exposes the `sent` result in its persistent hint/state.
   - A second send in the same mode may correctly remain quiet; no synthetic event counter is required.
   - If a future asynchronous failure/result surface exists, that changed result gets its own semantic contract rather than reviving a global announcement event.

The automatic heartbeat **material transition** remains a separate value-change case: its existing transition/announcement identity already represents a material semantic change and may drive a one-shot polite live-region update.

## Laws

1. **Repeated action does not automatically imply repeated announcement.** Prefer native action + persistent semantic result.
2. **Same value is not fresh evidence.** Never mutate text solely to trigger accessibility output.
3. **Changed async result may use a live region.** Gate it to the explicit action and actual semantic value change; startup/poll changes remain silent unless independently authorized.
4. **Selection is state.** For repeated detail selection, expose selected control semantics and durable detail instead of replaying a global announcement.
5. **Action labels track action.** Adam send semantics must include the selected mode; Mute/Enable/Confirm-style labels remain exact-current-action precedent.
6. **No fake freshness.** No decorative timestamps, counters, punctuation, zero-width markers, or opaque request IDs.
7. **Do not steal focus.** Programmatic focus movement needs its own interaction contract and runtime proof.
8. **Do not blanket-live-region a frequently refreshed value.** A live region that speaks polls is a regression, not accessibility.
9. **One owner.** Compose `OperatorOverlayService`; do not create a neighboring accessibility-event controller.
10. **Capability membrane:** `policy source → regression source → owner patch → owner source wired → regression executed → tested → runtime TalkBack → deployed → delivered → accepted`.
11. **P0 firewall:** no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.

## Owner acceptance questions

Before removing one legacy `announceForAccessibility(...)` call:

- Is the control/action itself accurately named?
- Is the resulting semantic state/value persistently inspectable?
- For live-region use, did the semantic value actually change?
- Can background/poll work mutate the same surface, and if so is that path gated silent?
- Does the design preserve mute, selection, focus, viewport-contact, and contact-preservation laws?
- Does the existing native owner carry the design?
- Is any one-shot live-region authority reset after the intended mutation?
- Does regression source distinguish source design from owner wiring and runtime proof?

If owner wiring is missing, keep the legacy call and mark **OWNER_WIRED=NO** even when the source-level design is ready.

## Current PR #329 source truth — 2026-08-21 0300

- doctrine: **YES / IMPLEMENTED_SOURCE**;
- `AccessibilityAnnouncementSemanticPolicy` has exact source designs for all four consequences: **YES**;
- Spotify changed-status design: **SOURCE_READY / OWNER_WIRED NO**;
- repeated detail selection+detail design: **SOURCE_READY / OWNER_WIRED NO**;
- Adam mode-specific action+persistent result design: **SOURCE_READY / OWNER_WIRED NO**;
- heartbeat material-transition design: **SOURCE_READY / OWNER_WIRED NO**;
- earlier heartbeat-only patch had a sticky live-region authority defect: **FOUND / CORRECTED IN PATCH SOURCE**;
- corrected heartbeat patch: `CORRECTED_PROPOSED_NOT_APPLIED`;
- regression source: **YES / UNEXECUTED**;
- authenticated existing owner still contains all four legacy calls: **YES / OWNER_WIRED NO**;
- She-Raw pre-execution consultation: **FAULT / account connection HTTP 400**, no substitute reviewer;
- TESTED / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.
