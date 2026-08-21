# Adam Mode Accessibility

## Purpose

Keep the existing Operator Overlay Adam controls truthful for accessibility without creating another accessibility controller, changing Adam transport, or touching Phone/P0 execution.

## Trigger

Use when the overlay exposes multiple Adam modes, when selecting a mode moves focus into the input, when a successful send changes result state, when new editing can make a previous SENT state stale, or when the Send action's consequence changes with the selected mode.

## Law

1. TERM / CHAT / CONT / VLAD / RADIO are one persistent mutually-exclusive selection set. Activating the selected mode does not turn that mode off.
2. Selection state, keyboard focus, accessibility focus, editable input value, send-action consequence, and send-result state are distinct. Moving keyboard focus into the input does not make the chosen mode discoverable later.
3. Expose exactly one selected mode through native selected/checked semantics. Do not model the five choices as independent toggles, and do not duplicate the same selected state into generic custom state text merely for decoration.
4. One-of-many context also needs stable set identity. The canonical mode order is TERM / CHAT / CONT / VLAD / RADIO, with one-based positions 1..5 and set size 5. Native owner evidence is complete only when the owner exposes both the single-selection collection context and each mode's stable item position; `setSelected(...)` alone is `PARTIAL_UNSAFE`.
5. Collection/set-position semantics must reuse the same exact `AdamModeSelectionAccessibilityPolicy` decision that owns persistent selection. Do not infer positions from labels or focus, and do not claim selection owns keyboard or accessibility focus.
6. Adam mode wire identities are exact canonical values: `terminal`, `chat`, `continue`, `vlad`, `radio`. Whitespace/case drift fails closed instead of being normalized into authority.
7. The editable Adam text remains the input's semantic value. Do not mask changing EditText text with a generic `contentDescription`; mode/result context belongs in state semantics. A generic description plus hidden hint is not a substitute for the actual editable value.
8. READY/SENT is a lifecycle, not a sticker. Selecting a mode returns READY; a successful submit becomes SENT; the programmatic empty clear after submit preserves SENT; real new non-empty editing after SENT returns READY because there is now unsent text.
9. Empty polling or decorative refresh must never turn SENT into READY. The state transition must be caused by a material mode/send/edit event.
10. The compact Send button may remain visibly `Send`, but its semantic action must name the exact current mode (`Send request to Adam using Vlad mode`, etc.) and refresh when mode selection changes. The Send action does not own selection or focus.
11. A successful send may leave a persistent `Sent` state on the input surface, but that persistent state is not automatically a replacement for a repeatable identical send receipt.
12. `AccessibilityAnnouncementSemanticPolicy` currently keeps Adam send announcement migration blocked. Do not remove the legacy explicit send receipt merely because persistent result state source exists.
13. Reuse `OperatorOverlayService` as the sole native owner. No neighboring Adam selector controller, accessibility controller, transport, queue, or phone path.
14. Reuse the repository Java lexical/source-evidence helpers when proving owner wiring. Comments, string literals, unrelated owner methods, a partial READY/SENT setter, a stale generic Send label, a selected-only mode implementation, or a patch artifact are not wiring proof.
15. Owner evidence for input state is complete only when mode selection, successful send, real edit-after-SENT recovery, null editable-value `contentDescription`, and state semantics converge on the same persistent state policy. Missing any of those is `PARTIAL_UNSAFE`, not SOURCE_WIRED.
16. Owner evidence for Send action is complete only when creation and subsequent mode changes both consume `AdamSendActionAccessibilityPolicy`; a one-time description is `PARTIAL_UNSAFE` because it can go stale after mode selection changes.
17. Source policy, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, callability, phone delivery, and acceptance are separate capability states.
18. The P0/phone firewall is binding. This skill cannot queue Phone Hands, execute on the primary phone, mutate recovery, or consume the physical acceptance chain.

## Current PR #329 source truth — 2026-08-21 1358

- Selection policy: `AdamModeSelectionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**. It carries stable one-based position-in-set plus set-size metadata for the five canonical modes.
- Position/set metadata regression source: `AdamModeSelectionAccessibilityPolicyTest` — **YES / UNEXECUTED**.
- Deterministic owner source probe: `tools/try_forever_adam_accessibility_owner_probe.py` — **SOURCE YES / NOT EXECUTED**. Probe v4 is now stricter: persistent native `setSelected(...)` without single-selection collection context and per-mode collection-item position is `PARTIAL_UNSAFE`, not SOURCE_WIRED.
- Probe hostile fixture: `tools/test_try_forever_adam_accessibility_owner_probe.py` — **SOURCE YES / UNEXECUTED**. It distinguishes selected-only partial wiring from full set-position source wiring and rejects comment/wrong-method counterfeits.
- Native owner consumption of position/set context: **NO**. The authenticated owner does not expose collection/set-position semantics today.
- Input-result policy: `AdamInputResultAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**. Changing EditText value must not be replaced by generic `contentDescription`; READY/SENT context belongs in state semantics.
- Send-action policy: `AdamSendActionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**. Exact selected mode determines the semantic action while the compact visible label remains `Send`.
- Authenticated owner blob remains `c5de1411a6b68087ae17aff83c032af754587150`: selection, input lifecycle/value preservation, dynamic Send semantics, and set-position context are **OWNER WIRING NO / LEGACY_OWNER**.
- Exact combined owner surgery provenance: `patches/try-forever-adam-mode-input-accessibility-owner.patch` — **CORRECTED_PROPOSED_NOT_APPLIED**, base locked to owner blob `c5de1411a6b68087ae17aff83c032af754587150`. The surgery now includes compileSdk-safe native collection/set-position semantics using the existing `AccessibilityNodeInfo` surface, plus persistent selection, READY/SENT edit recovery, and dynamic Send semantics.
- Owner mutation remains **NO** in this slice. The current Command Center Codex worker/job/session surface is retired, and audited GitHub upsert is a whole-file replacement rather than a patch interpreter. No duplicate worker/controller or phone-shaped substitute was created.
- The proposal preserves the legacy Adam send announcement because announcement migration remains blocked by `ADAM_REPEAT_SEND_RESULT_UNRESOLVED` — **DO NOT REMOVE LEGACY RECEIPT**.
- TESTED / Android runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- exactly one canonical Adam mode is selected;
- canonical modes expose stable one-based set positions 1..5 with set size 5;
- selected-only owner wiring is `PARTIAL_UNSAFE` until the single-selection collection and per-mode collection-item position are both present;
- source position metadata is not reported as native collection/TalkBack runtime semantics before owner consumption;
- case/whitespace drift in mode identity fails closed;
- selected mode state does not claim ownership of keyboard or accessibility focus;
- comments/literals and unrelated owner methods cannot counterfeit owner policy usage or collection/set-position wiring;
- READY and SENT result states preserve editable text semantics;
- generic Adam input `contentDescription` cannot coexist with SOURCE_WIRED editable-value semantics;
- successful submit moves READY to SENT;
- programmatic empty clear after submit preserves SENT;
- real new non-empty editing after SENT returns READY;
- selecting another mode returns READY;
- a source owner with READY/SENT setters but no edit recovery is `PARTIAL_UNSAFE`;
- the Send action names the exact selected mode and refreshes when the mode changes;
- a one-time or generic Send description is `LEGACY_OWNER`/`PARTIAL_UNSAFE`, not SOURCE_WIRED;
- persistent SENT state does not claim announcement migration is ready;
- policy/source/patch presence cannot be reported as Android or TalkBack runtime proof.

## Evidence membrane

`requested → plan → supporting source → authenticated readback → regression source → owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`
