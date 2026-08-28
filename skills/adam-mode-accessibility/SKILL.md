# Adam Mode Accessibility

## Purpose

Keep the existing Operator Overlay Adam controls truthful for accessibility without creating another accessibility controller, changing Adam transport, or touching Phone/P0 execution.

## Trigger

Use when the overlay exposes multiple Adam modes, when selecting a mode moves focus into the input, when a successful send changes result state, when new editing can make a previous SENT state stale, when the Send action's consequence changes with the selected mode, when the Send button can be focused/activated despite having no admissible request to send, or when direct mode/editable/request text can perform unbounded work before smaller send semantics reject it.

## Law

1. TERM / CHAT / CONT / VLAD / RADIO are one persistent mutually-exclusive selection set. Activating the selected mode does not turn that mode off.
2. Selection state, keyboard focus, accessibility focus, editable input value, send-action consequence, send availability, send-result state, and request persistence are distinct.
3. Expose exactly one selected mode through native selected/checked semantics. Do not model the five choices as independent toggles, and do not duplicate the same selected state into generic custom state text merely for decoration.
4. One-of-many context also needs stable set identity. The canonical mode order is TERM / CHAT / CONT / VLAD / RADIO, with one-based positions 1..5 and set size 5. Native owner evidence is complete only when the owner exposes both the single-selection collection context and each mode's stable item position; `setSelected(...)` alone is `PARTIAL_UNSAFE`.
5. Collection/set-position semantics must reuse the same exact `AdamModeSelectionAccessibilityPolicy` decision that owns persistent selection. Do not infer positions from labels or focus, and do not claim selection owns keyboard or accessibility focus.
6. Adam mode wire identities are exact canonical values: `terminal`, `chat`, `continue`, `vlad`, `radio`. Whitespace/case drift fails closed. Direct policy callers cross a 64 UTF-16-code-unit work throat before repeated equality/rejection work, and invalid raw mode text is not echoed into diagnostic prose.
7. `OperatorState.submitAdamRequest(...)` must consume the same exact mode-admission policy instead of separately trimming/lowercasing mode identity. Null may retain the historical `terminal` default, but non-null mode authority must not be normalized into another canonical value.
8. The editable Adam text remains the input's semantic value. Do not mask changing EditText text with a generic `contentDescription`; mode/result context belongs in state semantics.
9. READY/SENT is a lifecycle, not a sticker. Selecting a mode returns READY; a successful submit becomes SENT; the programmatic empty clear after submit preserves SENT; any newer unsent source returns READY. `OVER_BUDGET` is unavailable for Send but still proves newer unsent contact and therefore must not preserve stale SENT.
10. Empty polling or decorative refresh must never turn SENT into READY. The transition must come from a material mode/send/edit event or bounded evidence that newer unsent source exists.
11. The compact Send button may remain visibly `Send`, but its semantic action must name the exact current mode and refresh when mode selection changes. The Send action does not own selection or focus.
12. A successful send may leave a persistent `Sent` state on the input surface, but that persistent state is not automatically a replacement for a repeatable identical send receipt.
13. `AccessibilityAnnouncementSemanticPolicy` currently keeps Adam send announcement migration blocked. Do not remove the legacy explicit send receipt merely because persistent result-state source exists.
14. Reuse `OperatorOverlayService` as the sole native UI owner and `OperatorState` as the existing request persistence/routing owner. No neighboring Adam selector controller, accessibility controller, transport, queue, or phone path.
15. Reuse repository lexical/source-evidence helpers when proving owner wiring. Comments, string literals, unrelated owner methods, a partial READY/SENT setter, a stale generic Send label, a selected-only mode implementation, or a patch artifact are not wiring proof.
16. Owner evidence for input state is complete only when mode selection, successful send, edit-after-SENT recovery including rejected-over-budget contact, null editable-value `contentDescription`, and state semantics converge on the same persistent state policy. Missing any of those is `PARTIAL_UNSAFE`.
17. Owner evidence for Send action is complete only when creation and subsequent mode changes both consume `AdamSendActionAccessibilityPolicy`; a one-time description can go stale.
18. Source policy, owner source wiring, regression execution, Android runtime UI, TalkBack behavior, deployment, callability, phone delivery, and acceptance are separate capability states.
19. The P0/phone firewall is binding. This skill cannot queue Phone Hands, execute on the primary phone, mutate recovery, or consume the physical acceptance chain.
20. An enabled focusable Send button must correspond to an actually admissible request. Empty or ASCII-whitespace-only input should use native disabled-button semantics instead of a synthetic repeated announcement once the native accessibility owner consumes availability policy.
21. Small post-trim request semantics do not authorize unbounded pre-trim work. `AdamSendAvailabilityAccessibilityPolicy` reuses `HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS` (32,768 UTF-16 code units), observes source length once, and scans admitted source in-place with the exact historical `String.trim()` emptiness predicate (`char <= U+0020`) without whole-source `toString()` materialization. It distinguishes `EMPTY_OR_WHITESPACE`, `MATERIAL`, and `OVER_BUDGET`; over-ceiling input is unavailable and is never truncated or normalized.
22. Request source-work custody is split by owner and must stay split in receipts. Direct/package `OperatorState.submitAdamRequest(...)` is SOURCE_WIRED: request text is bounded before trim/terminal alias/UTF-8/Base64/SHA, and mode identity delegates to exact `AdamModeSelectionAccessibilityPolicy`. `OperatorOverlayService.submitAdamRequest()` still materializes/trims the editable value before consuming the supporting throat and therefore remains OWNER RED / PROPOSED_NOT_APPLIED.
23. Any future change to Adam request normalization must update request admission and `AdamSendAvailabilityAccessibilityPolicy` together. Do not let native enabled state disagree with what `submitAdamRequest()` accepts.
24. Edit-driven Send availability and READY/SENT truth should consume one bounded request classification per edit callback. `OVER_BUDGET` disables Send while `hasUnsentText=true`; supporting-policy rejection is not evidence that the field contains no newer unsent user input.
25. Availability and action wording are separate semantic owners inside the same native button. Availability owns native enabled/disabled consequence; `refreshAdamSendAction()` owns exact current-mode action wording. Do not create duplicate `contentDescription` writers merely to prove availability.
26. The canonical Adam accessibility owner surgery owns Adam Send availability because it already owns the persistent Send field, TextWatcher, mode-change lifecycle, editable-value state, and action semantics. The collapsed operational-contact patch must not also mutate those Adam organs.
27. Exact owner base is a hard custody boundary. The Adam accessibility surgery remains rebased onto authenticated `OperatorOverlayService` blob `2935243f...`; it is `PROPOSED_NOT_APPLIED` and must not be fuzzily carried onto a later owner blob.
28. Finite source-work repair must not mutate deterministic terminal aliases, phone destinations, queue/relay behavior, recovery, or physical acceptance. Resource custody is not permission to cross the P0 firewall.
29. Supporting capability must not green-paint consumer capability. A safe availability policy, mode policy, result-state policy, or rebased patch does not make the native UI owner SOURCE_WIRED until authenticated owner source consumes it.
30. A finite output does not prove finite source work. If a supporting accessibility decision can be computed without whole-source materialization, native owner surgery should consume that decision before materializing request text or deriving state.
31. Sendability and unsent-contact truth are distinct. `enabled=false` may mean empty input or rejected over-budget source; only the bounded classifier's `hasUnsentText` decides whether persistent SENT contact is stale.
32. Existing-owner surgery must preserve unrelated source exactly enough for review. A broad whole-file rewrite that changes unrelated comments/formatting is a failed surgery even when intended semantics are present; revert it before treating owner capability as changed.
33. Rendered-axis geometry is authority-bearing accessibility context. The existing Adam mode row is horizontal, so canonical source geometry is `rowCount=1`, `columnCount=5`, every item has `rowIndex=0`, and `columnIndex=positionInSet-1`; row/column spans are one. Do not transpose a horizontal set into five rows by one column, and do not hand-copy this geometry into the native owner when `AdamModeSelectionAccessibilityPolicy` can own it once for both regression and owner surgery.

## Current PR #329 source truth — 2026-08-27 22:02 CT

- Selection policy: `AdamModeSelectionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES** at blob `0ab827c07cca64ce29879c0d7a51d229835a9aeb`. It owns exact five-mode identity, stable one-based positions, horizontal one-row/five-column collection geometry, a 64-code-unit direct source throat, and bounded invalid-mode diagnostics.
- Selection regression source: `AdamModeSelectionAccessibilityPolicyTest` — **YES / UNEXECUTED** at blob `8fad334e627a9bc13c6fb417e48f7e99b884706c`; it now pins `1 row × 5 columns`, row zero, zero-based columns, one-cell spans, and the independent one-based set positions.
- Input-result policy: `AdamInputResultAccessibilityPolicy` — **IMPLEMENTED SOURCE YES** at blob `cc09a2533fa487569ec0b3708f9dd00ace2a95da`; doctrine and parameter semantics explicitly treat rejected OVER_BUDGET source as unsent contact rather than sendability.
- Input-result regression source: `AdamInputResultAccessibilityPolicyTest` — **YES / UNEXECUTED** at blob `6034131edf868504efee5885d7b4f0ba17fa7294`; it cross-pins OVER_BUDGET availability contact into READY/SENT lifecycle truth.
- Send-action policy: `AdamSendActionAccessibilityPolicy` — **IMPLEMENTED SOURCE YES** at blob `1c1f6a3b5f27c66e95fc44fe5e747da93c70d386`.
- Send-availability policy: `AdamSendAvailabilityAccessibilityPolicy` — **IMPLEMENTED SOURCE YES** at blob `2e15869dcab81995fbac849c98596a6cf2cd50c5`. It owns the 32,768-code-unit source throat, bounded in-place ASCII-trim-equivalent scan, explicit `EMPTY_OR_WHITESPACE / MATERIAL / OVER_BUDGET` state, and separate `hasUnsentText` contact truth.
- Send-availability hostile regression source: `AdamSendAvailabilityAccessibilityPolicyTest` — **YES / UNEXECUTED** at blob `2f7727f1b0c00c4785ea7d00fe36e50c41371d02`.
- Current authenticated native UI owner blob remains `2935243f136359e3489a89108406e888b0ec2911`. It still lacks the finite pre-materialization service gate and rebased Adam mode/input/result/action/availability wiring.
- A broad attempted owner rewrite at commit `82fd5003...` was rejected by self-review because its 224-line diff included unrelated comment/format churn. Commit `69511efc...` restored the exact pre-attempt tree before further source work. **No native owner capability is claimed from the rejected attempt.**
- Current authenticated request-state owner blob: `3870272863878cd7eaef69d24b31a6c8de1bbef9` — **REQUEST SOURCE-WORK SOURCE_WIRED**.
- Adam accessibility surgery: `patches/try-forever-adam-mode-input-accessibility-owner.patch` — **REBASED_PROPOSED_NOT_APPLIED** at blob `3937d4b6c699076c314dd475c7154f14d5baa4f9`, exact-base locked to UI owner blob `2935243f...`, and now consumes policy-owned horizontal collection geometry instead of duplicating row/column constants.
- Finite request-work surgery: `patches/try-forever-adam-request-source-work-throat.patch` — **PARTIAL_APPLIED_SOURCE__SERVICE_PROPOSED_NOT_APPLIED**; the service seam remains exact-base-locked to blob `2935243f...`.
- Deterministic Adam owner source probe: `tools/try_forever_adam_accessibility_owner_probe.py` — **SOURCE YES / NOT EXECUTED**.
- Legacy repeatable Adam send announcement remains present because `ADAM_REPEAT_SEND_RESULT_UNRESOLVED` is not resolved by this source work.
- TESTED / Android runtime UI / runtime TalkBack / deployed / callable / executed / delivered / accepted: **NO**.

## Regression doctrine

At minimum prove:

- exactly one canonical Adam mode is selected;
- canonical modes expose stable one-based positions 1..5 with set size 5;
- the horizontal native mode row exposes one row by five columns, every item at row zero with its zero-based canonical column, and the owner proposal consumes policy geometry rather than independently transposing/copying it;
- mode input exactly at the 64-code-unit policy throat still reaches exact identity comparison; max+1 stops before repeated identity/diagnostic work;
- case/whitespace drift fails closed and `OperatorState` does not independently normalize it into authority;
- selected-only owner wiring is `PARTIAL_UNSAFE` until collection and per-mode position semantics are both present;
- selected mode state does not claim ownership of keyboard or accessibility focus;
- READY/SENT state preserves editable text semantics and transition ordering;
- rejected OVER_BUDGET editable source disables Send but still invalidates stale SENT contact;
- the Send action names the exact selected mode and refreshes when mode changes;
- null/empty/ASCII-whitespace-only input makes Send unavailable under the admitted trim contract;
- direct availability source exactly at the broad work ceiling reaches the historical ASCII trim predicate without `toString()`; max+1 stops after the length observation with zero element reads and is classified OVER_BUDGET;
- direct state request source max+1 stops before trim/alias/UTF-8/Base64/SHA;
- native UI submit max+1 stops before editable `toString()`/trim before service request-work custody can be called SOURCE_WIRED;
- valid availability wiring can remain SOURCE_WIRED without duplicating action-description ownership;
- persistent SENT state does not claim announcement migration is ready;
- proposed owner patches and rejected owner attempts cannot be reported as Android or TalkBack runtime proof.

## Evidence membrane

`requested → plan → supporting source → authenticated readback → regression source → owner source wiring → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`
