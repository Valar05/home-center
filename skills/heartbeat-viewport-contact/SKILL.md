# Heartbeat Viewport Contact

## Purpose

Preserve *visible contact* for the existing Operator Overlay heartbeat controls when stable semantic Button objects are updated in place and label/neighbor widths change.

Stable object identity is not sufficient: a surviving Button can still slide horizontally out of the user's viewport when preceding content changes width.

## Ownership

- `OperatorOverlayService` remains the only Android UI owner.
- `HeartbeatOverlayRefreshPlan` owns pure semantic-anchor selection and bounded scroll math.
- The existing owner now consumes that policy in source; this is still not Android runtime proof.
- This skill does **not** create a renderer, controller, service, state store, phone path, or P0 owner.

## Source contract

1. Apply only when `structureIdentity` is stable and the existing owner is doing an in-place content refresh.
2. Choose at most one semantic anchor:
   - first: the accepted selected heartbeat control id;
   - otherwise: a directly keyboard-focused heartbeat Button id;
   - stale/missing ids: no anchor.
3. Do **not** inspect or claim TalkBack accessibility focus. Native accessibility-focus preservation requires runtime evidence and remains a separate capability state.
4. Before mutation, capture the anchor's semantic id and its horizontal viewport offset from the existing `HorizontalScrollView`.
5. After the existing child layout is requested, re-find that same semantic id and restore a bounded scroll target with `HeartbeatOverlayRefreshPlan.anchoredScrollX(...)`.
6. If the anchor disappeared, geometry is unavailable, structure changed, or the in-place refresh falls back to rebuild, do not manufacture anchor ownership or scroll movement.
7. Viewport anchoring must not alter semantic selection, evidence identity, announcement identity, or Christmas-motion eligibility.
8. Direct keyboard focus is read only from the existing heartbeat `Button` objects; accessibility focus is deliberately neither queried nor synthesized.

## Accessibility rules

- Native heartbeat Buttons remain the semantic/touch destinations; the horizontal container is not an accessibility destination.
- Touch targets remain at least the model's 48dp contract on both axes.
- Selection and keyboard-focus opportunity are not equivalent to TalkBack accessibility focus.
- Do not announce scroll restoration as a semantic heartbeat transition.
- Stable Button identity plus viewport restoration is an accessibility opportunity, not proof that TalkBack retained accessibility focus.

## Evidence membrane

Track these independently:

`requested → policy source → regression source → existing-owner source wiring → tested → runtime viewport observed → runtime TalkBack observed → deployed → callable → executed → delivered → accepted`

Current source truth: `existing-owner source wiring = YES`; `tested/runtime viewport/runtime TalkBack/deployed/callable/executed/delivered/accepted = NO` until their own authorized evidence exists.

A source helper or test fixture never proves Android layout timing or accessibility-focus retention.

## P0 / phone firewall

This skill is non-phone UI source work. It must not consume Phone Hands, primary-phone execution, queue/device probes, Home Center recovery orchestration, Nightcore, Pocket TTS, Chromium, Context Organs, or the P0 physical acceptance chain.
