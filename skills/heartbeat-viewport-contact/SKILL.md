# Heartbeat Viewport Contact

## Purpose

Preserve *visible contact* for the existing Operator Overlay heartbeat controls when semantic heartbeat content changes width or the ordered child structure changes while a surviving semantic control remains relevant.

Stable object identity is not sufficient: a surviving Button can slide horizontally out of the user's viewport when preceding content changes width. Rebuilds add a second hazard: the old native object may disappear even though the same semantic light still exists in the accepted next model. Delayed after-layout work adds a third: an older restore callback must not move the viewport after a later mutation or explicit selection has superseded it.

## Ownership

- `OperatorOverlayService` remains the only Android UI owner.
- `HeartbeatOverlayRefreshPlan` owns accepted semantic-anchor selection and bounded scroll math.
- `HeartbeatViewportRestorePolicy` owns pure source-only restore tickets and generation gating; it owns no Android views, callbacks, renderer, controller, service, state store, transport, phone path, or P0 owner.
- The existing owner currently consumes viewport anchoring only for stable-structure in-place refreshes. The broader restore-lifecycle policy is implemented source but is **not yet consumed by `OperatorOverlayService`**.

## Source contract

1. Consider viewport preservation only when the existing owner is about to perform a material heartbeat content mutation or structural rebuild.
2. Choose at most one semantic anchor against the **accepted next model**:
   - first: the accepted selected heartbeat control id;
   - otherwise: a directly keyboard-focused heartbeat Button id;
   - stale/missing ids: no anchor.
3. Do **not** inspect or claim TalkBack accessibility focus. Native accessibility-focus preservation requires runtime evidence and remains a separate capability state.
4. Before mutation, capture the chosen anchor's semantic id and horizontal viewport offset from the existing `HorizontalScrollView`, but only if that semantic id also exists in the current live child set.
5. Advance a restore-generation token whenever a later content/structure mutation or explicit semantic selection supersedes older pending after-layout work.
6. After layout, restore only when the pending ticket's generation still equals the current generation **and** the semantic anchor still exists in the accepted current model/live children.
7. Use `HeartbeatOverlayRefreshPlan.anchoredScrollX(...)` for the bounded target. Do not manufacture negative/out-of-range scroll motion.
8. If the anchor disappeared, geometry is unavailable, the pending ticket is stale, or current accepted semantics no longer contain the id, do not restore.
9. Viewport anchoring must not alter semantic selection, evidence identity, announcement identity, or Christmas-motion eligibility.
10. Direct keyboard focus is read only from the existing heartbeat `Button` objects; accessibility focus is deliberately neither queried nor synthesized.

## Accessibility rules

- Native heartbeat Buttons remain the semantic/touch destinations; the horizontal container is not an accessibility destination.
- Touch targets remain at least the model's 48dp contract on both axes.
- Selection, keyboard focus, visible viewport contact, and TalkBack accessibility focus are four separate states. Never report one as another.
- A structural rebuild may preserve the *semantic viewport target* when the id survives, but source policy does not prove keyboard focus or accessibility focus survived object replacement.
- Do not announce scroll restoration or restore-generation churn as semantic heartbeat transitions.
- Stable Button identity plus viewport restoration is an accessibility opportunity, not proof that TalkBack retained accessibility focus.

## Idempotence / delayed-callback law

`HeartbeatViewportRestorePolicy` defines one bounded ticket: `(generation, semanticId, viewportOffsetPx)`.

- Generation is an ordering token, not wall-clock evidence.
- A later mutation/selection advances generation and invalidates earlier pending tickets.
- A current generation is still insufficient if the semantic id disappeared from the accepted model.
- Exact generation equality plus surviving semantic identity permits geometry calculation; it does not prove Android executed the callback.
- Generation wrap is deterministic source behavior, not an invitation to treat counters as durable evidence identities.

## Evidence membrane

Track these independently:

`requested → policy source → regression source → existing-owner stable-refresh wiring → existing-owner rebuild/generation wiring → tested → runtime viewport observed → runtime keyboard focus observed → runtime TalkBack observed → deployed → callable → executed → delivered → accepted`

Current source truth:

- policy source: **YES**
- regression source: **YES**
- existing-owner stable-refresh viewport wiring: **YES**
- existing-owner structural-rebuild viewport wiring: **NO**
- existing-owner restore-generation/idempotence wiring: **NO**
- tested/runtime viewport/runtime keyboard focus/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO** until their own authorized evidence exists.

A source helper or test fixture never proves Android layout timing or accessibility-focus retention.

## Regression source

At minimum cover:

- selected semantic id surviving a changed ordered structure;
- keyboard-focused fallback when selection does not survive;
- stale/missing ids producing no anchor;
- a later mutation invalidating an older pending restore ticket;
- a removed semantic id refusing restore even when generation is current;
- bounded anchor math at leading/trailing edges and width-growth cases;
- generation treated as ordering only, not timestamp/evidence truth.

`HeartbeatViewportRestorePolicyTest` is regression source only until an authorized runner executes it.

## P0 / phone firewall

This skill is non-phone UI source work. It must not consume Phone Hands, primary-phone execution, queue/device probes, Home Center recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or the P0 physical acceptance chain.
