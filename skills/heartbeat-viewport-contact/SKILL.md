# Heartbeat Viewport Contact

## Purpose

Preserve *visible contact* for the existing Operator Overlay heartbeat controls when semantic heartbeat content changes width or the ordered child structure changes while a surviving semantic control remains relevant.

Stable object identity is not sufficient: a surviving Button can slide horizontally out of the user's viewport when preceding content changes width. Rebuilds add a second hazard: the old native object may disappear even though the same semantic light still exists in the accepted next model. Delayed after-layout work adds a third: an older restore callback must not move the viewport after a later mutation, explicit selection, or direct keyboard-focus move has superseded it. A fourth hazard is now explicit: **semantic selection is not proof of visible contact**. A durable selected light may be completely offscreen after the user scrolls elsewhere.

## Ownership

- `OperatorOverlayService` remains the only Android UI owner.
- `HeartbeatOverlayRefreshPlan` owns accepted semantic-anchor selection and bounded scroll math.
- `HeartbeatViewportRestorePolicy` owns pure restore-ticket identity, stale-work rejection, and source-only visible-contact geometry/selection policy; it owns no Android views, callbacks, renderer, controller, service, state store, transport, phone path, or P0 owner.
- The existing owner consumes the restore-ticket policy for stable in-place refreshes, structural rebuilds, and drift-triggered fallback rebuilds. This is **source wiring only**, not Android execution or runtime viewport proof.
- The new geometry-aware visible-contact gate is **policy/regression source only**. The existing owner does not yet consume it.

## Source contract

1. Consider viewport preservation only when the existing owner is about to perform a material heartbeat content mutation or structural rebuild.
2. Semantic candidacy remains selected-first / keyboard-focus-fallback against the **accepted next model**, but a candidate must also have real horizontal viewport intersection before it may be called visible contact.
3. `HeartbeatViewportRestorePolicy.hasVisibleViewportContact(...)` defines that geometry boundary: partial intersection is enough; fully offscreen, zero-width control, and zero-width viewport fail closed; long arithmetic prevents overflow from manufacturing contact.
4. `HeartbeatViewportRestorePolicy.visibleViewportAnchorId(...)` composes the existing semantic policy with geometry truth: a visible accepted selection wins; an offscreen selection cannot suppress a visible accepted keyboard-focused fallback; stale ids cannot be resurrected by a true geometry flag.
5. Do **not** inspect or claim TalkBack accessibility focus. Native accessibility-focus preservation requires runtime evidence and remains a separate capability state.
6. Before mutation, capture the chosen anchor's semantic id and horizontal viewport offset from the existing `HorizontalScrollView`, but only if that semantic id also exists in the current live child set.
7. Advance a restore-generation token whenever a later content/structure mutation, presentation-state mutation, hide, or explicit semantic selection supersedes older pending after-layout work.
8. After layout, restore only when the pending ticket's generation still equals the current generation, the semantic anchor still exists in the accepted current model/live children, **and the same semantic id still owns viewport contact under current accepted selection/focus semantics**.
9. A same-generation direct keyboard-focus move can invalidate an older keyboard-derived ticket without pretending focus motion is a new heartbeat generation.
10. Use `HeartbeatViewportRestorePolicy.targetScrollX(...)` / `HeartbeatOverlayRefreshPlan.anchoredScrollX(...)` for the bounded target. Do not manufacture negative/out-of-range scroll motion.
11. If the anchor disappeared, geometry is unavailable, the pending ticket is stale, current accepted interaction semantics no longer own that id, or the candidate is fully offscreen under the visibility policy, do not claim visible contact.
12. Viewport anchoring must not alter semantic selection, evidence identity, announcement identity, or Christmas-motion eligibility.
13. Direct keyboard focus is read only from the existing heartbeat `Button` objects; accessibility focus is deliberately neither queried nor synthesized.

## Accessibility rules

- Native heartbeat Buttons remain the semantic/touch destinations; the horizontal container is not an accessibility destination.
- Touch targets remain at least the model's 48dp contract on both axes.
- Selection, keyboard focus, visible viewport contact, and TalkBack accessibility focus are four separate states. Never report one as another.
- A selected control that is completely outside the current horizontal viewport does **not** possess visible contact merely because its semantic id is durable.
- A visible keyboard-focused control may be the source-policy fallback when a durable selection is offscreen; this is still not TalkBack accessibility-focus evidence.
- A structural rebuild may preserve the *semantic viewport target* when the id survives, but source wiring does not prove keyboard focus or accessibility focus survived object replacement.
- Do not announce scroll restoration, restore-generation churn, or geometry-only visibility decisions as semantic heartbeat transitions.
- Stable Button identity plus viewport restoration is an accessibility opportunity, not proof that TalkBack retained accessibility focus.

## Idempotence / delayed-callback law

`HeartbeatViewportRestorePolicy` defines one bounded ticket: `(generation, semanticId, viewportOffsetPx)`.

- Generation is an ordering token, not wall-clock evidence.
- A later mutation/selection advances generation and invalidates earlier pending tickets.
- Same generation is still insufficient when current selected/focused ownership moved to a different surviving semantic id.
- A current generation is still insufficient if the semantic id disappeared from the accepted model.
- Geometry visibility is a capture-time source boundary; it is not encoded into the ticket as evidence and therefore must not be retroactively claimed at runtime without owner consumption and observation.
- Exact generation equality plus surviving semantic ownership permits geometry calculation; it does not prove Android executed the callback.
- Generation wrap is deterministic source behavior, not an invitation to treat counters as durable evidence identities.

## Existing-owner source wiring

`OperatorOverlayService` currently:

1. advances restore generation before each material heartbeat view mutation;
2. captures selected-first / keyboard-focus-fallback semantic contact before mutation when the surviving anchor exists in current live children;
3. applies the same ticket path to stable in-place refresh, structural rebuild, and structure-drift fallback rebuild;
4. schedules one-shot pre-draw restoration on the existing `heartbeatLights` owner;
5. revalidates generation, current accepted model membership, and current selected/focused semantic ownership before scroll;
6. invalidates pending restore work on presentation-state changes, hide, and explicit heartbeat selection.

The existing owner **does not yet** use `hasVisibleViewportContact(...)` / `visibleViewportAnchorId(...)` before capture. Therefore an offscreen durable selection remains a known source-wiring wound, not a repaired runtime behavior.

This does **not** prove Android performed the restore, preserved keyboard focus through rebuild, retained TalkBack accessibility focus, or produced a delivered phone interface.

## Evidence membrane

Track these independently:

`requested → semantic viewport policy source → visible-contact geometry policy source → regression source → existing-owner stable-refresh wiring → existing-owner rebuild/generation wiring → existing-owner visibility-gate wiring → tested → runtime viewport observed → runtime keyboard focus observed → runtime TalkBack observed → deployed → callable → executed → delivered → accepted`

Current source truth:

- semantic viewport policy source: **YES**
- visible-contact geometry + geometry-aware anchor chooser source: **YES**
- regression source: **YES**
- existing-owner stable-refresh viewport wiring: **YES**
- existing-owner structural-rebuild viewport wiring: **YES**
- existing-owner restore-generation/idempotence wiring: **YES**
- current interaction-owner revalidation source: **YES**
- existing-owner visible-contact gate consumption: **NO**
- tested/runtime viewport/runtime keyboard focus/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO** until their own authorized evidence exists.

A source helper, service mutation, or test fixture never proves Android layout timing or accessibility-focus retention.

## Regression source

At minimum cover:

- selected semantic id surviving a changed ordered structure;
- keyboard-focused fallback when selection does not survive;
- stale/missing ids producing no anchor;
- a later mutation invalidating an older pending restore ticket;
- a removed semantic id refusing restore even when generation is current;
- a same-generation keyboard-focus move invalidating an older keyboard-derived ticket;
- explicit selection superseding an older keyboard-derived ticket;
- durable semantic selection remaining owner while keyboard focus moves elsewhere;
- whole and partial horizontal viewport intersection;
- fully offscreen and exact-edge non-intersection;
- zero-width control/viewport failure;
- overflow-adjacent geometry using long arithmetic;
- offscreen durable selection yielding to a visible keyboard-focused fallback;
- geometry truth never resurrecting semantic ids missing from the accepted model;
- bounded anchor math at leading/trailing edges and width-growth cases;
- generation treated as ordering only, not timestamp/evidence truth.

`HeartbeatViewportRestorePolicyTest` is regression source only until an authorized runner executes it.

## P0 / phone firewall

This skill is non-phone UI source work. It must not consume Phone Hands, primary-phone execution, queue/device probes, Home Center recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or the P0 physical acceptance chain.
