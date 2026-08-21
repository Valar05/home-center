# Adam Mode Accessibility

## Purpose

Keep the existing Operator Overlay Adam controls truthful for accessibility without creating another accessibility controller, changing Adam transport, or touching Phone/P0 execution.

## Trigger

Use when the overlay exposes multiple Adam modes, when selecting a mode moves focus into the input, or when a successful send changes visible hint/result state.

## Law

1. TERM / CHAT / CONT / VLAD / RADIO are one persistent mutually-exclusive selection set. Activating the selected mode does not turn it off.
2. Selection state, keyboard focus, accessibility focus, editable input value, and send-result state are distinct. Moving keyboard focus into the input does not make the chosen mode discoverable later.
3. Expose exactly one selected mode through native selected/checked semantics. Do not model the five choices as independent toggles, and do not duplicate the same selected state into generic custom state text merely for decoration.
4. Adam mode wire identities are exact canonical values: `terminal`, `chat`, `continue`, `vlad`, `radio`. Whitespace/case drift fails closed instead of being normalized into authority.
5. The editable Adam text remains the input value. Mode/result context belongs in state semantics; do not mask the editable value with a generic content description.
6. A successful send may leave a persistent `Sent` state on the input surface, but that persistent state is not automatically a replacement for a repeatable identical send receipt.
7. `AccessibilityAnnouncementSemanticPolicy` currently keeps Adam send announcement migration blocked. Do not remove the legacy explicit send receipt merely because persistent result state source exists.
8. Reuse `OperatorOverlayService` as the sole native owner. No neighboring Adam selector controller, accessibility controller, transport, queue, or phone path.
9. Reuse the repository Java lexical/source-evidence helpers when proving owner wiring. Comments, string literals, and unrelated owner methods are not wiring proof.
10. Source policy, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, callability, phone delivery, and acceptance are separate capability states.
11. The P0/phone firewall is binding. This skill cannot queue Phone Hands, execute on the primary phone, mutate recovery, or consume the physical acceptance chain.

## Current PR #329 source truth

- Supporting selection policy: `AdamModeSelectionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**.
- Supporting input-result policy: `AdamInputResultAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**.
- Pure JUnit regression source for both policies: **YES / UNEXECUTED**.
- Deterministic owner source probe: `tools/try_forever_adam_accessibility_owner_probe.py` — **SOURCE YES / NOT EXECUTED**. Probe v2 binds evidence to direct Adam owner methods rather than the whole giant owner class.
- Authenticated owner at the 2026-08-21 0959 plan still changes `adamMode`, updates the input hint/description, moves keyboard focus to the input, and does not expose persistent selected/checked mode state — **MODE OWNER WIRING NO / LEGACY_OWNER**.
- Authenticated owner still puts `sent` in the empty-field hint and uses the legacy explicit announcement while the field lacks persistent mode/result state semantics — **INPUT RESULT OWNER WIRING NO / LEGACY_OWNER**.
- Adam announcement migration remains blocked by `ADAM_REPEAT_SEND_RESULT_UNRESOLVED` — **DO NOT REMOVE LEGACY RECEIPT**.
- TESTED / Android runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- exactly one canonical Adam mode is selected;
- case/whitespace drift in mode identity fails closed;
- selected mode state does not claim ownership of keyboard or accessibility focus;
- comments/literals and unrelated owner methods cannot counterfeit owner policy usage;
- READY and SENT result states preserve editable value semantics;
- persistent SENT state does not claim announcement migration is ready;
- policy/source presence cannot be reported as Android or TalkBack runtime proof.

## Evidence membrane

`requested → plan → supporting source → authenticated readback → regression source → owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`
