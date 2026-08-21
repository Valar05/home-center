# Operator Repeatable Accessibility Event Semantics

## Purpose

Prevent a deprecated announcement migration from silently deleting **repeatable action consequences** when the proposed replacement is only a live region on a value that may not change.

This skill is repository/source accessibility doctrine only. It owns no Android View, controller, renderer, phone execution, P0 recovery, deployment, delivery, or acceptance lane.

## Core distinction

A live region is a semantic **value-change** surface. A repeatable action is an **event consequence**.

If action A can complete twice while the proposed TextView text/contentDescription remains identical, then:

`POLITE + setText(sameValue)`

is not an exact replacement for:

`announce each completed action`.

Do not remove the legacy consequence until the existing owner has a semantic event/status design whose user-facing value changes meaningfully for each completed action, or another platform-supported semantic pattern that preserves the consequence without a global announcement event.

## Current TRY FOREVER examples

Three current `OperatorOverlayService` consequences are repeatable and remain owner-unready:

1. **Spotify explicit command receipt** — a status/refresh command can complete while the playback summary is identical to the previous value.
2. **Heartbeat explicit detail selection** — the same semantic light can be selected again while its full Why/Consequence/Evidence/Source detail is unchanged.
3. **Adam send confirmation** — another send in the same mode can complete while a simple `Adam • <mode> • sent` label would be unchanged.

The automatic heartbeat **material transition** is different: the existing transition/announcement identity represents a semantic state/consequence change and therefore can compose with the existing summary value as a live-region value-change candidate.

## Laws

1. **Same value is not a fresh event receipt.** Never assume assigning identical text generates equivalent accessibility feedback.
2. **No fake freshness.** Do not append random punctuation, zero-width text, decorative timestamps, or opaque IDs merely to force an announcement.
3. **Fresh semantic value must pay rent.** If a status gains a sequence, timestamp, action label, or result identity, that information must be genuinely useful and visible/inspectable, not an accessibility side-channel costume.
4. **Do not steal focus by default.** Replacing an announcement with programmatic keyboard/accessibility-focus movement requires its own user-interaction contract and runtime proof.
5. **Do not convert passive detail into a focus owner accidentally.** Explicit detail-selection migration must preserve existing contact/focus/viewport laws unless a new owner contract is deliberately approved.
6. **Do not blanket-live-region a frequently refreshed value.** Automatic/background refresh must stay silent unless the existing semantic gate explicitly authorizes the change.
7. **One owner.** Compose `OperatorOverlayService`; do not create a neighboring accessibility-event controller.
8. **Capability membrane:** `policy source → owner design → regression source → owner source wired → regression executed → tested → runtime TalkBack → deployed → delivered → accepted`.
9. **P0 firewall:** no Phone Hands, primary-phone execution, recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.

## Acceptance questions for a repeatable consequence

Before removing a legacy announcement, answer all of these with source evidence:

- Can the action complete twice with the same current semantic value?
- What semantic value or platform behavior represents **this completion**, not merely the resulting steady state?
- Will that value remain meaningful if shown visually and inspected later?
- Can background/poll updates mutate the same value and accidentally generate noise?
- Does mute apply to this consequence under the existing contract?
- Does the design change focus, selection, viewport contact, or input semantics?
- Is the replacement owned by the existing native owner?
- Does a regression distinguish repeated identical steady-state actions from one genuine value change?

If any answer is unresolved, keep the legacy owner consequence and mark migration **OWNER_WIRED=NO**.

## Current PR #329 source truth — 2026-08-21 0200

- doctrine harvested: **YES / IMPLEMENTED_SOURCE**;
- pure announcement policy identifies all three repeatable consequences as `REPEATABLE_ACTION_EVENT_UNRESOLVED`: **YES**;
- regression source asserts those consequences are not migration-ready: **YES / UNEXECUTED**;
- prior four-consequence owner patch: **REJECTED_UNSAFE__DO_NOT_APPLY**;
- exact replacement designs for Spotify receipt / repeated detail / Adam send: **NO**;
- existing-owner migration for those three consequences: **NO**;
- TESTED / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.
