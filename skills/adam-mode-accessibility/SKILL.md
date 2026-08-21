# Adam Mode Accessibility

## Purpose

Keep the existing Operator Overlay Adam controls truthful for accessibility without creating another accessibility controller, changing Adam transport, or touching Phone/P0 execution.

## Trigger

Use when the overlay exposes multiple Adam modes, when selecting a mode moves focus into the input, when a successful send changes result state, or when new editing can make a previous SENT state stale.

## Law

1. TERM / CHAT / CONT / VLAD / RADIO are one persistent mutually-exclusive selection set. Activating the selected mode does not turn that mode off.
2. Selection state, keyboard focus, accessibility focus, editable input value, and send-result state are distinct. Moving keyboard focus into the input does not make the chosen mode discoverable later.
3. Expose exactly one selected mode through native selected/checked semantics. Do not model the five choices as independent toggles, and do not duplicate the same selected state into generic custom state text merely for decoration.
4. Adam mode wire identities are exact canonical values: `terminal`, `chat`, `continue`, `vlad`, `radio`. Whitespace/case drift fails closed instead of being normalized into authority.
5. The editable Adam text remains the input value. Mode/result context belongs in state semantics; do not mask the editable value with a generic content description.
6. READY/SENT is a lifecycle, not a sticker. Selecting a mode returns READY; a successful submit becomes SENT; the programmatic empty clear after submit preserves SENT; real new non-empty editing after SENT returns READY because there is now unsent text.
7. Empty polling or decorative refresh must never turn SENT into READY. The state transition must be caused by a material mode/send/edit event.
8. A successful send may leave a persistent `Sent` state on the input surface, but that persistent state is not automatically a replacement for a repeatable identical send receipt.
9. `AccessibilityAnnouncementSemanticPolicy` currently keeps Adam send announcement migration blocked. Do not remove the legacy explicit send receipt merely because persistent result state source exists.
10. Reuse `OperatorOverlayService` as the sole native owner. No neighboring Adam selector controller, accessibility controller, transport, queue, or phone path.
11. Reuse the repository Java lexical/source-evidence helpers when proving owner wiring. Comments, string literals, unrelated owner methods, a partial READY/SENT setter, or a patch artifact are not wiring proof.
12. Owner evidence for input state is complete only when mode selection, successful send, and real edit-after-SENT recovery all converge on the same persistent state policy. Missing edit recovery is `PARTIAL_UNSAFE`, not SOURCE_WIRED.
13. Source policy, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, callability, phone delivery, and acceptance are separate capability states.
14. The P0/phone firewall is binding. This skill cannot queue Phone Hands, execute on the primary phone, mutate recovery, or consume the physical acceptance chain.

## Current PR #329 source truth — 2026-08-21 1059

- Supporting selection policy: `AdamModeSelectionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**.
- Supporting input-result policy: `AdamInputResultAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**, now including explicit `MODE_SELECTED`, `SUBMIT_SUCCEEDED`, and `EDITED` lifecycle transitions.
- Pure JUnit regression source for policy lifecycle: **YES / UNEXECUTED**.
- Deterministic owner source probe: `tools/try_forever_adam_accessibility_owner_probe.py` — **SOURCE YES / NOT EXECUTED**. Probe v3 requires direct mode initialization/refresh plus READY/SENT/edit-recovery lifecycle; comments/literals and partial setters cannot counterfeit SOURCE_WIRED.
- Authenticated owner blob at this plan remains `c5de1411a6b68087ae17aff83c032af754587150`: mode selection and input-result lifecycle are still **OWNER WIRING NO / LEGACY_OWNER**.
- Exact owner surgery provenance: `patches/try-forever-adam-mode-input-accessibility-owner.patch` — **PROPOSED_NOT_APPLIED**, base locked to owner blob `c5de1411a6b68087ae17aff83c032af754587150`.
- The proposal preserves the legacy Adam send announcement because announcement migration remains blocked by `ADAM_REPEAT_SEND_RESULT_UNRESOLVED` — **DO NOT REMOVE LEGACY RECEIPT**.
- TESTED / Android runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- exactly one canonical Adam mode is selected;
- case/whitespace drift in mode identity fails closed;
- selected mode state does not claim ownership of keyboard or accessibility focus;
- comments/literals and unrelated owner methods cannot counterfeit owner policy usage;
- READY and SENT result states preserve editable value semantics;
- successful submit moves READY to SENT;
- programmatic empty clear after submit preserves SENT;
- real new non-empty editing after SENT returns READY;
- selecting another mode returns READY;
- a source owner with READY/SENT setters but no edit recovery is `PARTIAL_UNSAFE`;
- persistent SENT state does not claim announcement migration is ready;
- policy/source/patch presence cannot be reported as Android or TalkBack runtime proof.

## Evidence membrane

`requested → plan → supporting source → authenticated readback → regression source → owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`
