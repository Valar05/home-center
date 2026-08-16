# Heartbeat Viewport Contact

## Purpose

Preserve *visible contact* for the existing Operator Overlay heartbeat controls when semantic heartbeat content changes width or the ordered child structure changes while a surviving semantic control remains relevant.

Stable object identity is not sufficient: a surviving Button can slide horizontally out of the user's viewport when preceding content changes width. Rebuilds add a second hazard: the old native object may disappear even though the same semantic light still exists in the accepted next model. Delayed after-layout work adds a third: an older restore callback must not move the viewport after a later mutation, explicit selection, or direct keyboard-focus move has superseded it. A fourth hazard is explicit: **semantic selection is not proof of visible contact**. A durable selected light may be completely offscreen after the user scrolls elsewhere. A fifth hazard follows from rebuilds: **mutation-caused loss of native keyboard focus is not proof that the user superseded the captured anchor**. A sixth hazard is now explicit: **empty heartbeat-child focus is not proof of mutation-caused focus loss** because direct focus may have moved to a non-heartbeat overlay control. A seventh scar is interaction ownership: **persistent selection is not permanent navigation ownership**; newer direct keyboard navigation may supersede a selection-anchored pending restore.

## Ownership

- `OperatorOverlayService` remains the only Android UI owner.
- `HeartbeatOverlayRefreshPlan` owns accepted semantic-anchor selection and bounded scroll math.
- `HeartbeatViewportRestorePolicy` owns pure restore-ticket identity, stale-work rejection, visible-contact geometry, and captured interaction-owner revalidation; it owns no Android views, callbacks, renderer, controller, service, state store, transport, phone path, or P0 owner.
- The existing owner consumes the restore-ticket policy for stable in-place refreshes, structural rebuilds, and drift-triggered fallback rebuilds. This is **source wiring only**, not Android execution or runtime viewport proof.
- The existing owner consumes the geometry-aware visible-contact gate before capture. This is durable source wiring, not runtime viewport or TalkBack evidence.
- The existing owner now consumes the explicit focus-scope overload with actual mutation class plus overlay-wide direct-focus presence. This is durable source wiring, not runtime viewport, keyboard-focus, or TalkBack evidence.

## Source contract

1. Consider viewport preservation only when the existing owner is about to perform a material heartbeat content mutation or structural rebuild.
2. Semantic candidacy remains selected-first / keyboard-focus-fallback against the **accepted next model**, but a candidate must also have real horizontal viewport intersection before it may be called visible contact.
3. `HeartbeatViewportRestorePolicy.hasVisibleViewportContact(...)` defines that geometry boundary: partial intersection is enough; fully offscreen, zero-width control, and zero-width viewport fail closed; long arithmetic prevents overflow from manufacturing contact.
4. The existing owner measures the live selected and direct-keyboard-focused native controls against the current `HorizontalScrollView` before mutation and feeds those booleans to `visibleViewportAnchorId(...)` / `captureVisible(...)`.
5. `visibleViewportAnchorId(...)` composes the existing semantic policy with geometry truth: a visible accepted selection wins; an offscreen selection cannot suppress a visible accepted keyboard-focused fallback; stale ids cannot be resurrected by a true geometry flag.
6. Do **not** inspect or claim TalkBack accessibility focus. Native accessibility-focus preservation requires runtime evidence and remains a separate capability state.
7. Before mutation, capture the chosen anchor's semantic id and horizontal viewport offset from the existing `HorizontalScrollView`, together with the accepted selected/focused interaction ids that explain why that anchor owned contact.
8. Advance a restore-generation token whenever a later content/structure mutation, presentation-state mutation, hide, or explicit semantic selection supersedes older pending after-layout work.
9. After layout, restore only when the pending ticket's generation still equals the current generation, the semantic anchor still exists in the accepted current model/live children, and the captured interaction owner has not been superseded.
10. Do **not** re-run capture-time visibility against post-mutation geometry to decide whether the ticket is still owned; the mutation itself is allowed to move the anchor and is exactly why restoration exists. Revalidate interaction ownership, not mutation-caused geometry.
11. A different non-empty heartbeat keyboard focus observed after capture is newer navigation and supersedes the pending captured-owner ticket, including a ticket whose visible anchor came from persistent selection.
12. Empty heartbeat-child focus may receive rebuild amnesty only when the mutation that actually occurred could destroy native focus **and** there is no direct focus elsewhere under the existing overlay root.
13. Stable in-place refresh must not use rebuild amnesty. If heartbeat-child focus disappears during an in-place refresh, the restore is stale unless the ticket was touch-selected with no keyboard owner and explicit overlay scope proves no competing direct focus.
14. Direct focus on a non-heartbeat overlay control is a competing interaction owner and cancels stale captured-owner restoration. This is direct-focus truth only; do not infer TalkBack focus.
15. Use `HeartbeatViewportRestorePolicy.targetScrollX(...)` / `HeartbeatOverlayRefreshPlan.anchoredScrollX(...)` for the bounded target. Do not manufacture negative/out-of-range scroll motion.
16. If the anchor disappeared, capture-time geometry is unavailable, the pending ticket is stale, the accepted selection changed, or a competing direct focus is observed, do not claim visible contact.
17. Viewport anchoring must not alter semantic selection, evidence identity, announcement identity, or Christmas-motion eligibility.

## Accessibility rules

- Native heartbeat Buttons remain the semantic/touch destinations; the horizontal container is not an accessibility destination.
- Touch targets remain at least the model's 48dp contract on both axes.
- Selection, heartbeat-child keyboard focus, non-heartbeat direct overlay focus, visible viewport contact, and TalkBack accessibility focus are separate states. Never report one as another.
- A selected control that is completely outside the current horizontal viewport does **not** possess visible contact merely because its semantic id is durable.
- A visible keyboard-focused heartbeat control may be the source-policy fallback when a durable selection is offscreen; this is still not TalkBack accessibility-focus evidence.
- A structural rebuild may preserve the *semantic viewport target* when the id survives even if the rebuild itself clears native keyboard focus. That is viewport-source behavior, not proof that keyboard focus survived.
- A newer surviving direct keyboard focus observed after capture is a competing interaction owner and cancels the older captured-owner ticket even when persistent selection did not change.
- A non-heartbeat overlay control owning direct focus is also a competing owner; an empty heartbeat-child scan alone must not hide that fact.
- Do not announce scroll restoration, restore-generation churn, or geometry-only visibility decisions as semantic heartbeat transitions.
- Stable Button identity plus viewport restoration is an accessibility opportunity, not proof that TalkBack retained accessibility focus.

## Idempotence / delayed-callback law

`HeartbeatViewportRestorePolicy` defines one bounded ticket with generation, chosen semantic id, viewport offset, and the accepted selected/focused ids observed at capture.

- Generation is an ordering token, not wall-clock evidence.
- A later mutation/selection advances generation and invalidates earlier pending tickets.
- Same generation is still insufficient when the captured interaction owner has changed.
- For geometry-aware captured-owner tickets, a changed direct heartbeat keyboard focus is newer navigation and supersedes the ticket, including a selection-derived ticket.
- When current heartbeat-child focus is empty, the source policy may distinguish mutation-caused absence from stale work using two explicit inputs: whether this mutation may destroy keyboard focus and whether any direct keyboard focus is known elsewhere in the overlay.
- Empty focus is therefore **ambiguous evidence**, not automatic permission.
- A selection-derived ticket captured with no keyboard owner may remain valid when the accepted selection is unchanged and explicit overlay scope proves no competing direct focus.
- The older semantic-only `shouldRestore(...)` helper intentionally retains selected-first semantics; do not confuse that compatibility helper with the stronger geometry-aware captured-owner contract now consumed by the service.
- A current generation is still insufficient if the semantic id disappeared from the accepted model.
- Capture-time visibility is source evidence for *which* live control owned contact before mutation. Post-mutation geometry is not user-intent evidence and must not invalidate a ticket merely because the mutation moved the anchor.
- Exact generation equality plus surviving captured ownership permits geometry calculation; it does not prove Android executed the callback.

## Existing-owner source wiring

`OperatorOverlayService` currently:

1. advances restore generation before each material heartbeat view mutation;
2. reads direct keyboard focus from existing heartbeat Buttons for semantic identity;
3. resolves current selected/focused live children and measures each against the current horizontal viewport;
4. chooses visible accepted selection first, visible accepted keyboard focus second, otherwise no anchor;
5. captures the chosen anchor's pre-mutation viewport offset plus the accepted selected/focused ownership state;
6. applies the same ticket path to stable in-place refresh, structural rebuild, and structure-drift fallback rebuild;
7. records whether the mutation that actually occurred may destroy native keyboard focus: structural rebuild and fallback rebuild = true, successful in-place refresh = false;
8. schedules one-shot pre-draw restoration on the existing `heartbeatLights` owner;
9. after layout, reads overlay-wide direct-focus presence from `root.findFocus() != null`, separately from heartbeat-child semantic focus;
10. calls the explicit seven-argument captured-owner revalidation with generation, accepted model, selected id, heartbeat keyboard-focused id, actual mutation class, and overlay-wide direct-focus presence;
11. re-finds the semantic anchor and applies bounded scroll geometry only after ownership revalidation passes;
12. invalidates pending restore work on presentation-state changes, hide, and explicit heartbeat selection.

This does **not** prove Android performed the restore, preserved keyboard focus through rebuild, retained TalkBack accessibility focus, or produced a delivered phone interface. `root.findFocus()` is direct keyboard-focus presence only.

## Evidence membrane

Track these independently:

`requested → semantic viewport policy source → visible-contact geometry policy source → focus-scope revalidation policy source → regression source → existing-owner stable-refresh wiring → existing-owner rebuild/generation wiring → existing-owner visibility-gate wiring → existing-owner focus-scope wiring → tested → runtime viewport observed → runtime keyboard focus observed → runtime TalkBack observed → deployed → callable → executed → delivered → accepted`

Current source truth:

- semantic viewport policy source: **YES**
- visible-contact geometry + geometry-aware anchor chooser source: **YES**
- focus-scope revalidation policy source: **YES**
- regression source: **YES**
- existing-owner stable-refresh viewport wiring: **YES**
- existing-owner structural-rebuild viewport wiring: **YES**
- existing-owner restore-generation/idempotence wiring: **YES**
- captured interaction-owner revalidation source: **YES**
- existing-owner visible-contact gate consumption: **YES**
- existing-owner mutation-class/focus-scope revalidation wiring: **YES**
- exact GitHub readback of the owner wiring: **YES**
- tested: **NO / BLOCKED_ACTIONS_BUDGET**
- runtime viewport/runtime keyboard focus/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO** until their own authorized evidence exists.

A source helper, service mutation, or test fixture never proves Android layout timing or accessibility-focus retention.

## Regression source

At minimum cover:

- selected semantic id surviving a changed ordered structure;
- keyboard-focused fallback when selection does not survive;
- stale/missing ids producing no anchor;
- a later mutation invalidating an older pending restore ticket;
- a removed semantic id refusing restore even when generation is current;
- a same-generation keyboard-focus move invalidating an older semantic-only ticket;
- explicit selection superseding an older keyboard-derived ticket;
- whole and partial horizontal viewport intersection;
- fully offscreen and exact-edge non-intersection;
- zero-width control/viewport failure;
- overflow-adjacent geometry using long arithmetic;
- offscreen durable selection yielding to a visible keyboard-focused fallback;
- visible capture recording the selected/focused ownership state that produced the ticket;
- keyboard-derived ticket receiving empty-focus amnesty only when mutation may destroy focus;
- stable in-place refresh refusing empty-focus amnesty;
- non-heartbeat direct overlay focus cancelling a captured-owner rebuild ticket;
- same heartbeat keyboard owner remaining valid even when direct focus exists;
- newer heartbeat keyboard focus superseding a selection-anchored captured-owner ticket;
- capture-time keyboard baseline remaining evidence when the secondary id disappears from the accepted current model;
- touch-selected ticket with no keyboard owner remaining valid only when explicit overlay scope proves no competing direct focus;
- geometry truth never resurrecting semantic ids missing from the accepted model;
- bounded anchor math at leading/trailing edges and width-growth cases;
- generation treated as ordering only, not timestamp/evidence truth.

`HeartbeatViewportRestorePolicyTest` and `HeartbeatViewportInteractionOwnershipRegressionTest` are regression source only until an authorized runner executes them.

## P0 / phone firewall

This skill is non-phone UI source work. It must not consume Phone Hands, primary-phone execution, queue/device probes, Home Center recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or the P0 physical acceptance chain.
