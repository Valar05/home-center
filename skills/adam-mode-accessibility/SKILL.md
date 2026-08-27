# Adam Mode Accessibility

## Purpose

Keep the existing Operator Overlay Adam controls truthful for accessibility without creating another accessibility controller, changing Adam transport, or touching Phone/P0 execution.

## Trigger

Use when the overlay exposes multiple Adam modes, when selecting a mode moves focus into the input, when a successful send changes result state, when new editing can make a previous SENT state stale, when the Send action's consequence changes with the selected mode, when the Send button can be focused/activated despite having no admissible request to send, or when direct editable/request text can perform unbounded work before the smaller send semantics reject it.

## Law

1. TERM / CHAT / CONT / VLAD / RADIO are one persistent mutually-exclusive selection set. Activating the selected mode does not turn that mode off.
2. Selection state, keyboard focus, accessibility focus, editable input value, send-action consequence, send availability, and send-result state are distinct. Moving keyboard focus into the input does not make the chosen mode discoverable later.
3. Expose exactly one selected mode through native selected/checked semantics. Do not model the five choices as independent toggles, and do not duplicate the same selected state into generic custom state text merely for decoration.
4. One-of-many context also needs stable set identity. The canonical mode order is TERM / CHAT / CONT / VLAD / RADIO, with one-based positions 1..5 and set size 5. Native owner evidence is complete only when the owner exposes both the single-selection collection context and each mode's stable item position; `setSelected(...)` alone is `PARTIAL_UNSAFE`.
5. Collection/set-position semantics must reuse the same exact `AdamModeSelectionAccessibilityPolicy` decision that owns persistent selection. Do not infer positions from labels or focus, and do not claim selection owns keyboard or accessibility focus.
6. Adam mode wire identities are exact canonical values: `terminal`, `chat`, `continue`, `vlad`, `radio`. Whitespace/case drift fails closed instead of being normalized into authority at the accessibility policy boundary.
7. The editable Adam text remains the input's semantic value. Do not mask changing EditText text with a generic `contentDescription`; mode/result context belongs in state semantics.
8. READY/SENT is a lifecycle, not a sticker. Selecting a mode returns READY; a successful submit becomes SENT; the programmatic empty clear after submit preserves SENT; real new non-empty editing after SENT returns READY because there is now unsent text.
9. Empty polling or decorative refresh must never turn SENT into READY. The state transition must be caused by a material mode/send/edit event.
10. The compact Send button may remain visibly `Send`, but its semantic action must name the exact current mode (`Send request to Adam using Vlad mode`, etc.) and refresh when mode selection changes. The Send action does not own selection or focus.
11. A successful send may leave a persistent `Sent` state on the input surface, but that persistent state is not automatically a replacement for a repeatable identical send receipt.
12. `AccessibilityAnnouncementSemanticPolicy` currently keeps Adam send announcement migration blocked. Do not remove the legacy explicit send receipt merely because persistent result state source exists.
13. Reuse `OperatorOverlayService` as the sole native UI owner and `OperatorState` as the existing request persistence/routing owner. No neighboring Adam selector controller, accessibility controller, transport, queue, or phone path.
14. Reuse the repository Java lexical/source-evidence helpers when proving owner wiring. Comments, string literals, unrelated owner methods, a partial READY/SENT setter, a stale generic Send label, a selected-only mode implementation, or a patch artifact are not wiring proof.
15. Owner evidence for input state is complete only when mode selection, successful send, real edit-after-SENT recovery, null editable-value `contentDescription`, and state semantics converge on the same persistent state policy. Missing any of those is `PARTIAL_UNSAFE`, not SOURCE_WIRED.
16. Owner evidence for Send action is complete only when creation and subsequent mode changes both consume `AdamSendActionAccessibilityPolicy`; a one-time description is `PARTIAL_UNSAFE` because it can go stale after mode selection changes.
17. Source policy, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, callability, phone delivery, and acceptance are separate capability states.
18. The P0/phone firewall is binding. This skill cannot queue Phone Hands, execute on the primary phone, mutate recovery, or consume the physical acceptance chain.
19. An enabled focusable Send button must correspond to an actually admissible request. The current owner silently returns when trimmed input is empty; source availability mirrors that exact admitted trim boundary rather than silently widening request semantics.
20. Empty or ASCII-whitespace-only input should use native disabled-button semantics instead of a synthetic repeated announcement. Mode-specific action text remains available from `AdamSendActionAccessibilityPolicy`; disabling the button does not transfer selection/focus ownership to the Send action.
21. Small post-trim request semantics do not authorize unbounded pre-trim work. `AdamSendAvailabilityAccessibilityPolicy` now reuses `HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS` as the broad finite direct-source work ceiling before materializing/trimming an editable `CharSequence`. Over-ceiling input is unavailable; it is not truncated or normalized into a smaller request. This bounds work after one caller `length()` observation and does not claim callback-free admission for arbitrary custom `CharSequence` implementations.
22. The supporting availability throat does not green-paint the actual request owners. `OperatorOverlayService.submitAdamRequest()` and package/direct `OperatorState.submitAdamRequest(...)` still need the same finite work gate before their own trim/alias/UTF-8/Base64/SHA work. Until those existing owners consume the gate, request source-work custody is `PARTIAL / OWNER RED`.
23. Any future change to Adam request normalization must update request admission and `AdamSendAvailabilityAccessibilityPolicy` together. Do not let the semantic enabled state disagree with what `submitAdamRequest()` will actually accept.
24. Edit-driven Send availability evidence must prove that `refreshAdamSendAvailability()` is called from the actual `onTextChanged(...)` callback and that initial projection occurs independently outside that callback. A watcher token, an empty callback, and two nearby refresh calls are `PARTIAL_UNSAFE`, not edit ownership.
25. Availability and action wording are separate semantic owners inside the same native button. `refreshAdamSendAvailability()` owns native enabled/disabled consequence. `refreshAdamSendAction()` owns exact current-mode action wording. Do not require or create duplicate `contentDescription` writers merely to prove availability.
26. The canonical Adam accessibility owner surgery owns Adam Send availability because it already owns the persistent Send field, TextWatcher, mode-change lifecycle, editable-value state, and action semantics. The collapsed operational-contact patch must not also mutate those Adam organs.
27. A patch whose exact owner base has changed is not silently applicable. The historical Adam accessibility surgery is still useful design evidence, but its `c5de1411...` base predates later `OperatorOverlayService` owner mutations and must be rebased before any apply.
28. Finite source-work repair must not mutate deterministic terminal aliases, phone destinations, queue/relay behavior, recovery, or physical acceptance. Resource custody is not permission to cross the P0 firewall.

## Current PR #329 source truth — 2026-08-27 18:02 CT

- Selection policy: `AdamModeSelectionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**. It carries stable one-based position-in-set plus set-size metadata for the five canonical modes.
- Position/set metadata regression source: `AdamModeSelectionAccessibilityPolicyTest` — **YES / UNEXECUTED**.
- Input-result policy: `AdamInputResultAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**.
- Send-action policy: `AdamSendActionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**.
- Send-availability policy: `AdamSendAvailabilityAccessibilityPolicy` — **IMPLEMENTED SOURCE YES**. It now owns a broad finite pre-trim work throat using the existing 32,768 UTF-16-code-unit envelope ceiling while preserving the admitted `String.trim()` semantics.
- Send-availability hostile regression source: `AdamSendAvailabilityAccessibilityPolicyTest` — **YES / UNEXECUTED**. It pins exact-ceiling behavior and max+1 rejection before `toString()`/trim after one `length()` observation.
- Current authenticated native owner blob: `2935243f136359e3489a89108406e888b0ec2911`. Heartbeat collection/live-region work changed this owner after the historical Adam accessibility patch base. Adam mode/input/result/action/availability owner wiring described by that older patch therefore remains **NO / LEGACY OWNER FOR THESE SEAMS**.
- Current authenticated request-state owner blob: `94772cc4e9a3b42591832337420de4c416aa18e4`.
- Historical Adam accessibility surgery: `patches/try-forever-adam-mode-input-accessibility-owner.patch` — **STALE BASE / REBASE REQUIRED / NOT APPLIED**. Its old `c5de1411...` base must not be treated as current owner authority.
- Finite request-work surgery: `patches/try-forever-adam-request-source-work-throat.patch` — **CORRECTED_PROPOSED_NOT_APPLIED**, exact-base-locked to the current service/state blobs above. It stages only finite input work in the existing owners and explicitly leaves phone/P0 routing destinations untouched.
- Request-work owner boundary fixture: `tools/test_try_forever_adam_request_source_work.py` — **RED SOURCE / UNEXECUTED**. It requires the direct UI and package/state owners to gate before trim/alias/encoding while preserving the repeatable Adam send announcement.
- Deterministic Adam owner source probe: `tools/try_forever_adam_accessibility_owner_probe.py` — **SOURCE YES / NOT EXECUTED**.
- Operational-contact owner probe: `tools/try_forever_operational_contact_owner_probe.py` — **SOURCE YES / v3 / NOT EXECUTED**. v3 keeps availability separate from action wording and still requires real `onTextChanged(...)` callback ownership plus independent initial projection.
- Operational-contact hostile fixture: `tools/test_try_forever_operational_contact_owner_probe.py` — **SOURCE YES / UNEXECUTED**. It proves an empty `onTextChanged` counterfeit stays `PARTIAL_UNSAFE` and that valid availability wiring does not need a duplicate action-description write.
- Collapsed operational-contact owner surgery: `patches/try-forever-operational-contact-owner.patch` — **CORRECTED_PROPOSED_NOT_APPLIED / COLLAPSED-ONLY**. It does not own Adam Send organs.
- The proposal preserves the legacy Adam send announcement because announcement migration remains blocked by `ADAM_REPEAT_SEND_RESULT_UNRESOLVED` — **DO NOT REMOVE LEGACY RECEIPT**.
- TESTED / Android runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- exactly one canonical Adam mode is selected;
- canonical modes expose stable one-based set positions 1..5 with set size 5;
- selected-only owner wiring is `PARTIAL_UNSAFE` until the single-selection collection and per-mode collection-item position are both present;
- case/whitespace drift in mode identity fails closed at the accessibility policy boundary;
- selected mode state does not claim ownership of keyboard or accessibility focus;
- READY and SENT result states preserve editable text semantics;
- successful submit moves READY to SENT;
- programmatic empty clear after submit preserves SENT;
- real new non-empty editing after SENT returns READY;
- selecting another mode returns READY;
- the Send action names the exact selected mode and refreshes when the mode changes;
- null/empty/ASCII-whitespace-only input makes Send unavailable under the exact admitted trim contract;
- material input makes Send available without inventing a synthetic announcement;
- direct availability source exactly at the broad work ceiling reaches existing trim semantics;
- direct availability source at broad work ceiling + 1 stops before whole-source `toString()`/trim work;
- actual UI send owner and direct state owner independently consume the broad request work gate before trim/alias/encoding before request source-work custody can be called SOURCE_WIRED;
- the owner probe rejects an empty `onTextChanged` callback even when two availability-refresh calls sit elsewhere in `createOverlay`;
- valid availability wiring can remain `SOURCE_WIRED` without duplicating the independently owned action-description write;
- persistent SENT state does not claim announcement migration is ready;
- policy/source/patch presence cannot be reported as Android or TalkBack runtime proof.

## Evidence membrane

`requested → plan → supporting source → authenticated readback → regression source → owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`
